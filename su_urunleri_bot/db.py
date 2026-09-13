import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import os
DB_PATH = Path('/share/su_urunleri_bot/su_urunleri_kolluk.db') if os.path.exists('/share') else Path('./su_urunleri_kolluk.db')
ASSET = Path('/app/data') if os.path.exists('/app/data') else Path(__file__).parent / 'data'
DATASET = 'v9'


def norm(value):
    """Turkish-friendly token normalization used only for search, never for source text."""
    s = str(value or '').lower()
    s = s.translate(str.maketrans({'ı':'i','ğ':'g','ü':'u','ş':'s','ö':'o','ç':'c'}))
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # Token boundaries matter: "ışık" must not match "değişiklik".
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _tokens(value):
    return [x for x in norm(value).split() if x]


def _rank_rows(rows, query, limit, title_fields=()):
    terms = _tokens(query)
    if not terms:
        return []
    qphrase = ' '.join(terms)
    ranked = []
    for row in rows:
        text = row['search_text'] or ''
        toks = set(text.split())
        hit=lambda t: (t in toks) or (len(t)>=4 and any(tok.startswith(t) for tok in toks))
        hits = sum(1 for t in terms if hit(t))
        if len(terms) == 1:
            if not hits:
                continue
        else:
            # Natural queries may contain filler words; require a strong partial match.
            need = len(terms) if len(terms) <= 2 else max(2, (len(terms) * 3 + 4) // 5)
            if hits < need:
                continue
        title = norm(' '.join(str(row[f] or '') for f in title_fields if f in row.keys()))
        title_toks = set(title.split())
        title_hit=lambda t: (t in title_toks) or (len(t)>=4 and any(tok.startswith(t) for tok in title_toks))
        title_hits = sum(1 for t in terms if title_hit(t))
        score = hits * 10 + title_hits * 8
        if qphrase and f' {qphrase} ' in f' {text} ':
            score += 30
        if qphrase and f' {qphrase} ' in f' {title} ':
            score += 40
        ranked.append((score, row))
    ranked.sort(key=lambda x: (-x[0], x[1]['source_row'] if 'source_row' in x[1].keys() else 0, x[1]['article'] if 'article' in x[1].keys() else 0))
    return [r for _, r in ranked[:limit]]


def con():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = con(); q = c.cursor()
    q.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS sources(key TEXT PRIMARY KEY, title TEXT, type TEXT, number TEXT, filename TEXT, sha256 TEXT);
    CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, article INTEGER, title TEXT, body TEXT, page_start INTEGER, page_end INTEGER, scope TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY, cat TEXT, title TEXT, summary TEXT, refs TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS commercial_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min_cm REAL, min_kg REAL, time_bans TEXT, article_size INTEGER, article_time INTEGER, scope TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS amateur_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min_cm REAL, min_kg REAL, limit_text TEXT, time_bans TEXT, article INTEGER, scope TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS prohibited_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, commercial INTEGER, amateur INTEGER, source TEXT, article INTEGER, search_text TEXT);
    CREATE TABLE IF NOT EXISTS penalty_cards(id INTEGER PRIMARY KEY, source_row INTEGER, violation TEXT, option_text TEXT, law TEXT, regulation TEXT, teblig TEXT, art36 TEXT, base_ipc REAL, amounts TEXT, product_seizure TEXT, means_seizure TEXT, repeat_text TEXT, license_action TEXT, notes TEXT, scope TEXT, layout TEXT, teblig_source TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS raw_excel_rows(source_row INTEGER PRIMARY KEY, raw_text TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_seen TEXT);
    CREATE TABLE IF NOT EXISTS query_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, query TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, detail TEXT, created_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(id DESC);
    CREATE TABLE IF NOT EXISTS issue_reports(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT, created_at TEXT, resolved_at TEXT, resolved_by INTEGER);
    CREATE INDEX IF NOT EXISTS idx_issue_reports_status ON issue_reports(status, id DESC);
    CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER, item_type TEXT, item_id TEXT, created_at TEXT, PRIMARY KEY(user_id,item_type,item_id));
    CREATE TABLE IF NOT EXISTS inspections(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, title TEXT, state TEXT, report TEXT, status TEXT, created_at TEXT, updated_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_inspections_user ON inspections(user_id, status, updated_at);
    ''')
    existing_columns = {
        table: {row[1] for row in q.execute(f'PRAGMA table_info({table})')}
        for table in ('commercial_species', 'amateur_species', 'prohibited_species')
    }
    additions = {
        'commercial_species': [('article_size', 'INTEGER'), ('scope', 'TEXT')],
        'amateur_species': [('article', 'INTEGER'), ('scope', 'TEXT')],
        'prohibited_species': [('commercial', 'INTEGER'), ('amateur', 'INTEGER'),
                               ('source', 'TEXT'), ('article', 'INTEGER')],
    }
    for table, columns in additions.items():
        for column, kind in columns:
            if column not in existing_columns[table]:
                q.execute(f'ALTER TABLE {table} ADD COLUMN {column} {kind}')
    # 6.0.30: işlem geçmişi kategori ve önem düzeyiyle tutulur; eski satırlar
    # eylem adına göre sınıflandırılır (düğme/metin satırları "eski" kalır).
    activity_columns = {row[1] for row in q.execute('PRAGMA table_info(activity_log)')}
    for column in ('category', 'level'):
        if column not in activity_columns:
            q.execute(f'ALTER TABLE activity_log ADD COLUMN {column} TEXT')
    q.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id, id DESC)')
    q.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_category ON activity_log(category, id DESC)')
    for action, (category, level, _label) in ACTIVITY_EVENTS.items():
        q.execute('UPDATE activity_log SET category=?, level=? WHERE action=? AND category IS NULL',
                  (category, level, action))
    old = q.execute("SELECT v FROM meta WHERE k='dataset'").fetchone()
    if not old or old[0] != DATASET:
        for table in ['sources','articles','rules','commercial_species','amateur_species','prohibited_species','penalty_cards','raw_excel_rows']:
            q.execute(f'DELETE FROM {table}')
        q.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('dataset',?)", (DATASET,))

        for src in json.loads((ASSET/'sources.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO sources VALUES(?,?,?,?,?,?)', (src['key'],src['title'],src['type'],src.get('number',''),src['filename'],src['sha256']))
        for a in json.loads((ASSET/'articles.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO articles(source,article,title,body,page_start,page_end,scope,search_text) VALUES(?,?,?,?,?,?,?,?)',
                      (a['source'],a['article'],a['title'],a['body'],a['page_start'],a['page_end'],a['scope'],norm(a['title']+' '+a['body'])))
        for r in json.loads((ASSET/'field_rules.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO rules VALUES(?,?,?,?,?,?)', (r['id'],r['cat'],r['title'],r['summary'],json.dumps(r['refs'],ensure_ascii=False),norm(r['cat']+' '+r['title']+' '+r['summary'])))
        for sp in json.loads((ASSET/'commercial_species.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO commercial_species(name,min_cm,min_kg,time_bans,article_size,article_time,scope,search_text) VALUES(?,?,?,?,?,?,?,?)',
                      (sp['name'],sp['min_cm'],sp['min_kg'],json.dumps(sp['time_bans']),sp.get('article_size',17),sp.get('article_time'),sp.get('scope','sea'),norm(sp['name'])))
        for sp in json.loads((ASSET/'amateur_species.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO amateur_species(name,min_cm,min_kg,limit_text,time_bans,article,scope,search_text) VALUES(?,?,?,?,?,?,?,?)',
                      (sp['name'],sp['min_cm'],sp['min_kg'],sp['limit'],json.dumps(sp['time_bans']),sp.get('article',15),sp.get('scope','sea'),norm(sp['name'])))
        for sp in json.loads((ASSET/'prohibited_species.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO prohibited_species(name,commercial,amateur,source,article,search_text) VALUES(?,?,?,?,?,?)',
                      (sp['name'],int(sp.get('commercial',True)),int(sp.get('amateur',True)),sp.get('source','61'),sp.get('article',16),norm(sp['name'])))
        for pc in json.loads((ASSET/'penalty_cards.json').read_text(encoding='utf-8')):
            search = norm(' '.join(str(pc.get(k) or '') for k in ['violation','option','law','regulation','teblig','art36','notes','aliases']))
            q.execute('''INSERT INTO penalty_cards(id,source_row,violation,option_text,law,regulation,teblig,art36,base_ipc,amounts,product_seizure,means_seizure,repeat_text,license_action,notes,scope,layout,teblig_source,search_text)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (pc['id'],pc['source_row'],pc['violation'],pc.get('option'),pc.get('law'),pc.get('regulation'),pc.get('teblig'),pc.get('art36'),pc.get('base_ipc'),json.dumps(pc.get('amounts') or {},ensure_ascii=False),pc.get('product_seizure'),pc.get('means_seizure'),pc.get('repeat'),pc.get('license_action'),pc.get('notes'),pc.get('scope','sea_or_general'),pc.get('layout'),pc.get('teblig_source'),search))
        for rr in json.loads((ASSET/'raw_excel_rows.json').read_text(encoding='utf-8')):
            raw = ' | '.join(str(x) if x is not None else '' for x in rr['cells']).strip(' |')
            q.execute('INSERT INTO raw_excel_rows VALUES(?,?,?)',(rr['source_row'],raw,norm(raw)))
    c.commit(); c.close()


def touch_user(u, custom_name=None):
    name = custom_name or u.first_name or ''
    c=con(); c.execute('''INSERT INTO users(user_id,username,first_name,last_seen) VALUES(?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name,last_seen=excluded.last_seen''',(u.id,u.username,name,datetime.now().isoformat(timespec='seconds'))); c.commit(); c.close()


def log(uid,action,query=''):
    c=con(); c.execute('INSERT INTO query_log(user_id,action,query,created_at) VALUES(?,?,?,?)',(uid,action,query,datetime.now().isoformat(timespec='seconds'))); c.commit(); c.close()


# ── İşlem geçmişi ─────────────────────────────────────────────────────────
# Yalnızca iz bırakması gereken olaylar kaydedilir: oturum ve güvenlik, hesap
# yönetimi, denetim adımları, aramalar, hukuki değerlendirme ve destek.
# Ekranlar arası gezinme (geri, ana menü, sayfa değiştirme, cevap düğmeleri)
# 6.0.30'dan beri kaydedilmez; önceki 'button'/'text' satırları "eski"
# kategorisinde durur ve yönetici panelinden temizlenebilir.
ACTIVITY_CATEGORIES = {
    'denetim': 'Denetim',
    'arama': 'Arama',
    'hukuki': 'Hukuki değerlendirme',
    'oturum': 'Oturum',
    'guvenlik': 'Güvenlik',
    'yonetim': 'Yönetim',
    'destek': 'Destek',
    'eski': 'Eski gezinme kaydı',
}
ACTIVITY_LEVELS = ('bilgi', 'uyari', 'kritik')
# eylem: (kategori, varsayılan önem düzeyi, yönetici panelindeki açıklama)
ACTIVITY_EVENTS = {
    'setup': ('yonetim', 'kritik', 'İlk yönetici hesabını oluşturdu'),
    'login': ('oturum', 'bilgi', 'Giriş yaptı'),
    'logout': ('oturum', 'bilgi', 'Çıkış yaptı'),
    'login_failed': ('guvenlik', 'uyari', 'Hatalı şifreyle giriş denendi'),
    'login_blocked': ('guvenlik', 'kritik', 'Giriş geçici olarak kilitlendi'),
    'password_change': ('guvenlik', 'uyari', 'Kendi şifresini değiştirdi'),
    'password_reset_request': ('guvenlik', 'uyari', 'Şifre yenileme talebi oluşturdu'),
    'registration': ('yonetim', 'uyari', 'Üyelik başvurusu yaptı'),
    'person_create': ('yonetim', 'kritik', 'Kişi oluşturdu'),
    'person_update': ('yonetim', 'kritik', 'Kişi bilgilerini değiştirdi'),
    'log_purge': ('yonetim', 'kritik', 'Eski gezinme kayıtlarını temizledi'),
    'issue_report': ('destek', 'uyari', 'Sorun bildirdi'),
    'issue_resolve': ('destek', 'bilgi', 'Sorun bildirimini kapattı'),
    'audit_start': ('denetim', 'bilgi', 'Yönlendirilmiş denetim başlattı'),
    'audit_result': ('denetim', 'bilgi', 'Denetimi sonuçlandırdı'),
    'guide_start': ('denetim', 'bilgi', 'Kontrol föyü başlattı'),
    'guide_finish': ('denetim', 'bilgi', 'Kontrol föyünü tamamladı'),
    'control_sheet': ('denetim', 'bilgi', 'Kontrol çizelgesi oluşturdu'),
    'amateur_classification': ('denetim', 'bilgi', 'Ticari nitelik kontrolü yaptı'),
    'draft_resume': ('denetim', 'bilgi', 'Yarım kalan denetime devam etti'),
    'draft_discard': ('denetim', 'uyari', 'Yarım kalan denetimi sildi'),
    'search': ('arama', 'bilgi', 'Arama yaptı'),
    'ai_assessment': ('hukuki', 'bilgi', 'Hukuki değerlendirme istedi'),
    'button': ('eski', 'bilgi', 'Düğmeye bastı'),
    'text': ('eski', 'bilgi', 'Metin gönderdi'),
}


def log_activity(uid, action, detail='', level=None):
    """Web kullanıcısının güvenli işlem kaydı; parola ve oturum verisi almaz."""
    action = str(action)[:40]
    category, default_level, _label = ACTIVITY_EVENTS.get(action, ('yonetim', 'bilgi', action))
    level = level if level in ACTIVITY_LEVELS else default_level
    detail = ' '.join(str(detail or '').split())[:240]
    c = con()
    c.execute('INSERT INTO activity_log(user_id,action,detail,created_at,category,level) VALUES(?,?,?,?,?,?)',
              (uid, action, detail, datetime.now().isoformat(timespec='seconds'), category, level))
    c.commit()
    c.close()


def web_account_uid(username):
    """Hatalı giriş kaydı için: kullanıcı adı var olan bir hesaba aitse o hesabın kimliği."""
    c = con()
    row = c.execute('SELECT id FROM web_accounts WHERE username=?', (str(username or '').strip().lower(),)).fetchone()
    c.close()
    return -int(row['id']) if row else None


def activity_count():
    c = con()
    count = c.execute("SELECT COUNT(*) FROM activity_log WHERE COALESCE(category,'eski') != 'eski'").fetchone()[0]
    c.close()
    return count


_ACTIVITY_SELECT = '''
    SELECT a.id, a.user_id, a.action, a.detail, a.created_at,
           COALESCE(a.category, 'eski') AS category, COALESCE(a.level, 'bilgi') AS level,
           COALESCE(w.display_name, u.first_name, u.username, CAST(a.user_id AS TEXT)) AS display_name,
           COALESCE(w.username, u.username, '') AS username
    FROM activity_log a
    LEFT JOIN users u ON u.user_id = a.user_id
    LEFT JOIN web_accounts w ON a.user_id = -w.id'''


def activity_page(category='all', user_id=None, limit=25, offset=0):
    """Süzülmüş işlem geçmişi sayfası ve toplam kayıt sayısı. 'all' eski gezinme kayıtlarını içermez."""
    where, args = [], []
    if category in (None, 'all'):
        where.append("COALESCE(a.category,'eski') != 'eski'")
    else:
        where.append("COALESCE(a.category,'eski') = ?")
        args.append(category)
    if user_id is not None:
        where.append('a.user_id = ?')
        args.append(int(user_id))
    clause = ' WHERE ' + ' AND '.join(where)
    c = con()
    total = c.execute('SELECT COUNT(*) FROM activity_log a' + clause, args).fetchone()[0]
    rows = c.execute(_ACTIVITY_SELECT + clause + ' ORDER BY a.id DESC LIMIT ? OFFSET ?',
                     args + [int(limit), int(offset)]).fetchall()
    c.close()
    return rows, total


def admin_activity(limit=30):
    """En yeni önemli web işlemleri (eski gezinme kayıtları hariç)."""
    return activity_page('all', limit=limit)[0]


def activity_summary(days=7):
    """Yönetici özeti: bugün ve son `days` gün için eylem sayıları, uyarı düzeyindeki
    kayıtlar, etkin kişi sayıları ve son 24 saatteki hatalı giriş denemeleri."""
    now = datetime.now()
    today = now.date().isoformat()
    since = (now.date() - timedelta(days=days - 1)).isoformat()
    day_ago = (now - timedelta(hours=24)).isoformat(timespec='seconds')
    c = con()

    def counts(start):
        return {row['action']: (row['n'], row['warn'] or 0) for row in c.execute(
            "SELECT action, COUNT(*) AS n, SUM(CASE WHEN level IN ('uyari','kritik') THEN 1 ELSE 0 END) AS warn "
            'FROM activity_log WHERE created_at >= ? GROUP BY action', (start,))}

    def active(start):
        return c.execute('SELECT COUNT(DISTINCT user_id) FROM activity_log WHERE created_at >= ? AND user_id < 0',
                         (start,)).fetchone()[0]

    summary = {
        'today': counts(today), 'week': counts(since),
        'active_today': active(today), 'active_week': active(since),
        'failed_24h': c.execute("SELECT COUNT(*) FROM activity_log WHERE action IN ('login_failed','login_blocked') "
                                'AND created_at >= ?', (day_ago,)).fetchone()[0],
        'legacy': c.execute("SELECT COUNT(*) FROM activity_log WHERE COALESCE(category,'eski')='eski'").fetchone()[0],
    }
    c.close()
    return summary


def staff_activity(days=7):
    """Her site hesabı için son `days` gündeki denetim, bulgu ve arama sayıları ile son önemli işlem zamanı."""
    since = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
    c = con()
    rows = c.execute('''
        SELECT w.id, w.username, w.display_name, w.is_admin, w.is_active, w.approval_status, w.last_login,
               SUM(CASE WHEN a.action IN ('audit_start','guide_start') AND a.created_at >= ? THEN 1 ELSE 0 END) AS inspections,
               SUM(CASE WHEN a.action IN ('audit_result','guide_finish') AND a.level IN ('uyari','kritik')
                        AND a.created_at >= ? THEN 1 ELSE 0 END) AS findings,
               SUM(CASE WHEN a.action = 'search' AND a.created_at >= ? THEN 1 ELSE 0 END) AS searches,
               MAX(CASE WHEN COALESCE(a.category,'eski') != 'eski' THEN a.created_at END) AS last_event
        FROM web_accounts w
        LEFT JOIN activity_log a ON a.user_id = -w.id
        GROUP BY w.id
        ORDER BY w.is_active DESC, last_event DESC, w.display_name COLLATE NOCASE
    ''', (since, since, since)).fetchall()
    c.close()
    return rows


def person_activity_counts(uid):
    """Bir kişinin tüm zamanlardaki eylem sayıları: {eylem: (adet, uyarı düzeyindeki adet)}."""
    c = con()
    rows = {row['action']: (row['n'], row['warn'] or 0) for row in c.execute(
        "SELECT action, COUNT(*) AS n, SUM(CASE WHEN level IN ('uyari','kritik') THEN 1 ELSE 0 END) AS warn "
        'FROM activity_log WHERE user_id = ? GROUP BY action', (int(uid),))}
    c.close()
    return rows


def purge_legacy_activity():
    """Eski düğme/metin gezinme kayıtlarını siler; önemli olay kayıtlarına dokunmaz."""
    c = con()
    removed = c.execute("DELETE FROM activity_log WHERE COALESCE(category,'eski') = 'eski'").rowcount
    c.commit()
    c.close()
    return removed


def create_issue_report(uid, message):
    c = con()
    cur = c.execute("INSERT INTO issue_reports(user_id,message,status,created_at) VALUES(?,?,'open',?)",
                    (uid, message, datetime.now().isoformat(timespec='seconds')))
    c.commit()
    report_id = cur.lastrowid
    c.close()
    return report_id


def open_issue_count():
    c = con()
    count = c.execute("SELECT COUNT(*) FROM issue_reports WHERE status='open'").fetchone()[0]
    c.close()
    return count


def admin_issue_reports(limit=20):
    c = con()
    rows = c.execute('''
        SELECT r.*, COALESCE(w.display_name, u.first_name, u.username, CAST(r.user_id AS TEXT)) AS display_name,
               COALESCE(w.username, u.username, '') AS username
        FROM issue_reports r
        LEFT JOIN users u ON u.user_id=r.user_id
        LEFT JOIN web_accounts w ON r.user_id=-w.id
        WHERE r.status='open'
        ORDER BY r.id DESC LIMIT ?
    ''', (int(limit),)).fetchall()
    c.close()
    return rows


def resolve_issue_report(report_id, admin_uid):
    c = con()
    cur = c.execute("UPDATE issue_reports SET status='resolved',resolved_at=?,resolved_by=? WHERE id=? AND status='open'",
                    (datetime.now().isoformat(timespec='seconds'), admin_uid, int(report_id)))
    c.commit()
    changed = cur.rowcount > 0
    c.close()
    return changed


def search_articles(query,limit=8,source=None,include_inland=True):
    c=con(); cond=[]; args=[]
    if source: cond.append('source=?'); args.append(source)
    if not include_inland: cond.append("scope!='inland'")
    sql='SELECT * FROM articles'+((' WHERE '+' AND '.join(cond)) if cond else '')
    rows=c.execute(sql,args).fetchall(); c.close()
    return _rank_rows(rows,query,limit,('title',))


def get_article(source,article):
    c=con(); r=c.execute('SELECT * FROM articles WHERE source=? AND article=?',(source,int(article))).fetchone(); c.close(); return r


def list_articles(source,include_inland=True):
    c=con();
    if include_inland:
        rows=c.execute('SELECT * FROM articles WHERE source=? ORDER BY article',(source,)).fetchall()
    else:
        rows=c.execute("SELECT * FROM articles WHERE source=? AND scope!='inland' ORDER BY article",(source,)).fetchall()
    c.close(); return rows


def list_sources():
    c=con(); rows=c.execute('''SELECT * FROM sources ORDER BY CASE key WHEN 'law' THEN 1 WHEN 'reg' THEN 2 WHEN '61' THEN 3 WHEN '62' THEN 4 WHEN 'bagis' THEN 5 ELSE 6 END''').fetchall(); c.close(); return rows


def search_rules(query='',cat=None,limit=12):
    c=con();
    if cat:
        rows=c.execute('SELECT * FROM rules WHERE cat=? ORDER BY title',(cat,)).fetchall()
    else:
        rows=c.execute('SELECT * FROM rules ORDER BY cat,title').fetchall()
    c.close()
    if not query:
        return rows[:limit]
    return _rank_rows(rows,query,limit,('title','cat'))


def get_rule(rid):
    c=con(); r=c.execute('SELECT * FROM rules WHERE id=?',(rid,)).fetchone(); c.close(); return r


def search_species(query,kind='commercial',limit=10,scope=None):
    table='commercial_species' if kind=='commercial' else 'amateur_species'
    c=con()
    if scope:
        rows=c.execute('SELECT * FROM '+table+' WHERE scope=? ORDER BY name',(scope,)).fetchall()
    else:
        rows=c.execute('SELECT * FROM '+table+' ORDER BY scope,name').fetchall()
    c.close()
    return _rank_rows(rows,query,limit,('name',))


def get_species(kind,sid):
    table='commercial_species' if kind=='commercial' else 'amateur_species'; c=con(); r=c.execute(f'SELECT * FROM {table} WHERE id=?',(int(sid),)).fetchone(); c.close(); return r


def search_prohibited(query,limit=10,activity=None):
    c=con()
    if activity in {'commercial','amateur'}:
        rows=c.execute(f'SELECT * FROM prohibited_species WHERE {activity}=1 ORDER BY name').fetchall()
    else:
        rows=c.execute('SELECT * FROM prohibited_species ORDER BY name').fetchall()
    c.close()
    return _rank_rows(rows,query,limit,('name',))


def search_penalties(query,limit=8):
    c=con(); rows=c.execute('SELECT * FROM penalty_cards').fetchall(); c.close()
    ranked = _rank_rows(rows,query,limit*2,('violation','option_text'))
    # BAGIS cards are often operationally urgent; otherwise preserve relevance / Excel order.
    ranked.sort(key=lambda r: (0 if r['layout']=='bagis' and 'bagis' in _tokens(query) else 1,))
    return ranked[:limit]


def get_penalty(pid):
    c=con(); r=c.execute('SELECT * FROM penalty_cards WHERE id=?',(int(pid),)).fetchone(); c.close(); return r


def raw_row(n):
    c=con(); r=c.execute('SELECT * FROM raw_excel_rows WHERE source_row=?',(int(n),)).fetchone(); c.close(); return r


def search_raw(query,limit=8):
    c=con(); rows=c.execute('SELECT * FROM raw_excel_rows ORDER BY source_row').fetchall(); c.close()
    return _rank_rows(rows,query,limit,('raw_text',))


def admin_stats():
    c=con()
    users=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_queries=c.execute('SELECT COUNT(*) FROM query_log').fetchone()[0]
    recent_logs=c.execute('''SELECT q.user_id,u.username,u.first_name,q.action,q.query,q.created_at FROM query_log q LEFT JOIN users u ON u.user_id=q.user_id ORDER BY q.id DESC LIMIT 30''').fetchall()
    c.close()
    return users, total_queries, recent_logs


def admin_user_activity():
    c=con()
    rows=c.execute('''
        SELECT u.user_id, u.username, u.first_name, u.last_seen, COUNT(a.id) as query_count
        FROM users u
        LEFT JOIN activity_log a ON a.user_id = u.user_id
        GROUP BY u.user_id
        ORDER BY query_count DESC
    ''').fetchall()
    c.close()
    return rows


def admin_audit_activity():
    c=con()
    # Audit & guide distribution
    guides=c.execute('''
        SELECT query, COUNT(*) as count 
        FROM query_log 
        WHERE action LIKE 'guide:%' OR action LIKE 'audit:%' OR action = 'guide_start'
        GROUP BY query
        ORDER BY count DESC
        LIMIT 15
    ''').fetchall()
    # Most searched keywords
    searches=c.execute('''
        SELECT query, COUNT(*) as count
        FROM query_log
        WHERE action LIKE '%search' AND query != '' AND query IS NOT NULL
        GROUP BY query
        ORDER BY count DESC
        LIMIT 10
    ''').fetchall()
    c.close()
    return guides, searches


def admin_daily_trend(days=7):
    """Son `days` günün denetim/kılavuz başlatma ve arama sayıları, en eskiden
    en yeniye sıralı. Hiç kaydı olmayan günler de 0 olarak döner ki yönetici
    panelindeki basit çubuk grafiğin günleri boşluksuz ve karşılaştırılabilir
    olsun. created_at sunucunun yerel saatiyle (datetime.now()) yazıldığı için
    burada da SQLite'ın UTC date() işlevi yerine Python tarihi kullanılır."""
    start = datetime.now().date() - timedelta(days=days - 1)
    c = con()
    rows = c.execute('''
        SELECT substr(created_at,1,10) AS day,
               SUM(CASE WHEN action LIKE 'guide:%' OR action LIKE 'audit:%' OR action='guide_start' THEN 1 ELSE 0 END) AS denetim,
               SUM(CASE WHEN query != '' AND query IS NOT NULL THEN 1 ELSE 0 END) AS arama
        FROM query_log
        WHERE substr(created_at,1,10) >= ?
        GROUP BY day
    ''', (start.isoformat(),)).fetchall()
    c.close()
    by_day = {r['day']: (r['denetim'] or 0, r['arama'] or 0) for r in rows}
    return [((start + timedelta(days=i)).isoformat(), *by_day.get((start + timedelta(days=i)).isoformat(), (0, 0)))
            for i in range(days)]


# ── Inspections ───────────────────────────────────────────────────────────
# A guided audit or a checklist run is kept as a row so the work survives a
# restart: one 'open' draft per user, promoted to 'done' with its report text
# when the inspector finishes.

def _now():
    return datetime.now().isoformat(timespec='seconds')


def save_draft(uid, kind, title, state):
    """Create or refresh this user's open draft; returns its id."""
    blob = json.dumps(state, ensure_ascii=False, default=str)
    c = con()
    row = c.execute("SELECT id FROM inspections WHERE user_id=? AND status='open'", (uid,)).fetchone()
    if row:
        iid = row['id']
        c.execute('UPDATE inspections SET kind=?,title=?,state=?,updated_at=? WHERE id=?',
                  (kind, title, blob, _now(), iid))
    else:
        cur = c.execute('INSERT INTO inspections(user_id,kind,title,state,report,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                        (uid, kind, title, blob, '', 'open', _now(), _now()))
        iid = cur.lastrowid
    c.commit()
    c.close()
    return iid


def open_draft(uid):
    c = con()
    r = c.execute("SELECT * FROM inspections WHERE user_id=? AND status='open' ORDER BY updated_at DESC LIMIT 1", (uid,)).fetchone()
    c.close()
    return r


def drop_draft(uid):
    c = con()
    c.execute("DELETE FROM inspections WHERE user_id=? AND status='open'", (uid,))
    c.commit()
    c.close()


def finish_inspection(uid, kind, title, state, report):
    """Close this user's draft as a completed record; returns its id."""
    blob = json.dumps(state, ensure_ascii=False, default=str)
    c = con()
    row = c.execute("SELECT id FROM inspections WHERE user_id=? AND status='open'", (uid,)).fetchone()
    if row:
        iid = row['id']
        c.execute("UPDATE inspections SET kind=?,title=?,state=?,report=?,status='done',updated_at=? WHERE id=?",
                  (kind, title, blob, report, _now(), iid))
    else:
        cur = c.execute("INSERT INTO inspections(user_id,kind,title,state,report,status,created_at,updated_at) VALUES(?,?,?,?,?,'done',?,?)",
                        (uid, kind, title, blob, report, _now(), _now()))
        iid = cur.lastrowid
    c.commit()
    c.close()
    return iid


def list_inspections(uid, limit=10):
    c = con()
    rows = c.execute("SELECT * FROM inspections WHERE user_id=? AND status='done' ORDER BY updated_at DESC LIMIT ?", (uid, int(limit))).fetchall()
    c.close()
    return rows


def get_inspection(iid):
    c = con()
    r = c.execute('SELECT * FROM inspections WHERE id=?', (int(iid),)).fetchone()
    c.close()
    return r


def load_state(row):
    """Decode a stored state blob, tolerating a corrupt or empty column."""
    try:
        data = json.loads(row['state'] or '{}')
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}
