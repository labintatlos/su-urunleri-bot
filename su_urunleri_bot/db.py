import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

import os
DB_PATH = Path('/share/su_urunleri_bot/su_urunleri_kolluk.db') if os.path.exists('/share') else Path('./su_urunleri_kolluk.db')
ASSET = Path('/app/data') if os.path.exists('/app/data') else Path(__file__).parent / 'data'
DATASET = 'v4'


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
    CREATE TABLE IF NOT EXISTS commercial_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min_cm REAL, min_kg REAL, time_bans TEXT, article_time INTEGER, search_text TEXT);
    CREATE TABLE IF NOT EXISTS amateur_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min_cm REAL, min_kg REAL, limit_text TEXT, time_bans TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS prohibited_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS penalty_cards(id INTEGER PRIMARY KEY, source_row INTEGER, violation TEXT, option_text TEXT, law TEXT, regulation TEXT, teblig TEXT, art36 TEXT, base_ipc REAL, amounts TEXT, product_seizure TEXT, means_seizure TEXT, repeat_text TEXT, license_action TEXT, notes TEXT, scope TEXT, layout TEXT, teblig_source TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS raw_excel_rows(source_row INTEGER PRIMARY KEY, raw_text TEXT, search_text TEXT);
    CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_seen TEXT);
    CREATE TABLE IF NOT EXISTS query_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, query TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER, item_type TEXT, item_id TEXT, created_at TEXT, PRIMARY KEY(user_id,item_type,item_id));
    ''')
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
            q.execute('INSERT INTO commercial_species(name,min_cm,min_kg,time_bans,article_time,search_text) VALUES(?,?,?,?,?,?)',
                      (sp['name'],sp['min_cm'],sp['min_kg'],json.dumps(sp['time_bans']),sp.get('article_time'),norm(sp['name'])))
        for sp in json.loads((ASSET/'amateur_species.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO amateur_species(name,min_cm,min_kg,limit_text,time_bans,search_text) VALUES(?,?,?,?,?,?)',
                      (sp['name'],sp['min_cm'],sp['min_kg'],sp['limit'],json.dumps(sp['time_bans']),norm(sp['name'])))
        for sp in json.loads((ASSET/'prohibited_species.json').read_text(encoding='utf-8')):
            q.execute('INSERT INTO prohibited_species(name,search_text) VALUES(?,?)',(sp['name'],norm(sp['name'])))
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


def search_articles(query,limit=8,source=None,include_inland=False):
    c=con(); cond=[]; args=[]
    if source: cond.append('source=?'); args.append(source)
    if not include_inland: cond.append("scope!='inland'")
    sql='SELECT * FROM articles'+((' WHERE '+' AND '.join(cond)) if cond else '')
    rows=c.execute(sql,args).fetchall(); c.close()
    return _rank_rows(rows,query,limit,('title',))


def get_article(source,article):
    c=con(); r=c.execute('SELECT * FROM articles WHERE source=? AND article=?',(source,int(article))).fetchone(); c.close(); return r


def list_articles(source,include_inland=False):
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


def search_species(query,kind='commercial',limit=10):
    table='commercial_species' if kind=='commercial' else 'amateur_species'
    c=con(); rows=c.execute('SELECT * FROM '+table+' ORDER BY name').fetchall(); c.close()
    return _rank_rows(rows,query,limit,('name',))


def get_species(kind,sid):
    table='commercial_species' if kind=='commercial' else 'amateur_species'; c=con(); r=c.execute(f'SELECT * FROM {table} WHERE id=?',(int(sid),)).fetchone(); c.close(); return r


def search_prohibited(query,limit=10):
    c=con(); rows=c.execute('SELECT * FROM prohibited_species ORDER BY name').fetchall(); c.close()
    return _rank_rows(rows,query,limit,('name',))


def search_penalties(query,limit=8):
    c=con(); rows=c.execute("SELECT * FROM penalty_cards WHERE scope!='inland'").fetchall(); c.close()
    ranked = _rank_rows(rows,query,limit*2,('violation','option_text'))
    # BAGIS cards are often operationally urgent; otherwise preserve relevance / Excel order.
    ranked.sort(key=lambda r: (0 if r['layout']=='bagis' and 'bagis' in _tokens(query) else 1,))
    return ranked[:limit]


def get_penalty(pid):
    c=con(); r=c.execute('SELECT * FROM penalty_cards WHERE id=?',(int(pid),)).fetchone(); c.close(); return r


def raw_row(n):
    c=con(); r=c.execute('SELECT * FROM raw_excel_rows WHERE source_row=?',(int(n),)).fetchone(); c.close(); return r


def _raw_is_inland(text):
    n=' '+norm(text)+' '
    if any(x in n for x in [' ic su ',' icsu ',' ic sular ',' baraj ',' golet ']):
        return ' deniz ' not in n and ' marmara ' not in n and ' bogaz ' not in n
    if any(x in n for x in [' akarsu ',' gol ',' hes ']):
        return ' deniz ' not in n and ' mansap ' not in n
    return False


def search_raw(query,limit=8):
    c=con(); rows=c.execute('SELECT * FROM raw_excel_rows ORDER BY source_row').fetchall(); c.close()
    rows=[r for r in rows if not _raw_is_inland(r['raw_text'])]
    return _rank_rows(rows,query,limit,('raw_text',))


def add_fav(uid,typ,item):
    c=con(); c.execute('INSERT OR IGNORE INTO favorites VALUES(?,?,?,?)',(uid,typ,str(item),datetime.now().isoformat(timespec='seconds'))); c.commit(); c.close()


def favs(uid):
    c=con(); rows=c.execute('SELECT * FROM favorites WHERE user_id=? ORDER BY created_at DESC LIMIT 30',(uid,)).fetchall(); c.close(); return rows


def history(uid):
    c=con(); rows=c.execute('SELECT * FROM query_log WHERE user_id=? ORDER BY id DESC LIMIT 12',(uid,)).fetchall(); c.close(); return rows


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
        SELECT u.user_id, u.username, u.first_name, u.last_seen, COUNT(q.id) as query_count
        FROM users u
        LEFT JOIN query_log q ON q.user_id = u.user_id
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
        WHERE query != '' AND query IS NOT NULL
        GROUP BY query
        ORDER BY count DESC
        LIMIT 10
    ''').fetchall()
    c.close()
    return guides, searches
