"""Uçtan uca duman testi: web.py'yi gerçekten başlatır ve ulaşılabilen her düğmeye basar.

    python tools/smoke_test.py

Geçici bir klasörde boş veritabanıyla çalışır (canlı veriye dokunmaz), kurulum
koduyla ilk yöneticiyi oluşturur, giriş yapar, ana menüden başlayarak her
düğmeyi dener ve metin bekleyen ekranlara örnek metin yazar. Hata ekranı veya
HTTP hatası görülürse listeler ve 1 ile çıkar.
"""
import http.cookiejar
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADDON = REPO / 'su_urunleri_bot'
CANONICAL_SOURCES = REPO / 'SU ÜRÜNLERİ KAYNAKLAR (MARKDOWN)'
PACKAGED_MARKDOWN = ADDON / 'data' / 'markdown'
WEB_PORT, INGRESS_PORT = 18101, 18099
BASE = f'http://127.0.0.1:{WEB_PORT}'
MAX_DEPTH, MAX_PRESSES = 5, 4000
ERROR_MARKERS = ('Bir hata oluştu', 'Sunucuda beklenmeyen')
SAMPLE_TEXTS = ('levrek', '12')

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def source_digest(path):
    content = path.read_bytes()
    if path.suffix.casefold() == '.md':
        content = content.replace(b'\r\n', b'\n')
    return hashlib.sha256(content).hexdigest()


def check_source_integrity():
    """Ana kaynak klasörü, paket kopyası ve kaynak manifesti birebir uyuşmalı."""
    canonical = {p.name: p.read_bytes() for p in CANONICAL_SOURCES.glob('*.md')}
    packaged = {p.name: p.read_bytes() for p in PACKAGED_MARKDOWN.glob('*.md')}
    if not canonical:
        raise AssertionError('Ana Markdown kaynak klasörü boş')
    if canonical != packaged:
        missing = sorted(canonical.keys() - packaged.keys())
        extra = sorted(packaged.keys() - canonical.keys())
        changed = sorted(name for name in canonical.keys() & packaged.keys()
                         if canonical[name] != packaged[name])
        raise AssertionError(f'Paket Markdown kopyası eşleşmiyor: eksik={missing}, fazla={extra}, farklı={changed}')

    manifest = json.loads((ADDON / 'data' / 'sources.json').read_text(encoding='utf-8'))
    for source in manifest:
        path = REPO / source['filename']
        if not path.is_file():
            raise AssertionError(f'Manifest kaynağı bulunamadı: {source["filename"]}')
        digest = source_digest(path)
        if digest != source['sha256']:
            raise AssertionError(f'Manifest özeti uyuşmuyor: {source["filename"]}')
    print(f'sources {len(canonical)} Markdown + {len(manifest) - len(canonical)} diğer: verified')


def check_structured_data():
    import rebuild_structured_data
    stale = []
    for name, value in rebuild_structured_data.build_outputs().items():
        if (ADDON / 'data' / name).read_bytes() != rebuild_structured_data.dump(value):
            stale.append(name)
    if stale:
        raise AssertionError('Yeni kaynaklara göre güncel olmayan JSON verileri: ' + ', '.join(stale))
    species_guide = json.loads((ADDON / 'data' / 'tur_cizelgesi.json').read_text(encoding='utf-8'))
    sections = {sub['id']: sub for group in species_guide for sub in group.get('sub', [])}
    expected_columns = {
        '1.1': {'Türkçe Adı', 'Kapsam'},
        '1.2': {'Türkçe Adı', 'Asgari Boy', 'Asgari Ağırlık', 'Zaman Yasağı'},
        '2.1': {'Türkçe Adı', 'Kapsam'},
        '2.2': {'Türkçe Adı', 'Asgari Boy', 'Asgari Ağırlık', 'Alıkonulabilir Miktar', 'Zaman Yasağı'},
        '3.1': {'Türkçe Adı', 'Asgari Boy', 'Asgari Ağırlık', 'Zaman Yasağı'},
        '3.2': {'Türkçe Adı', 'Asgari Boy', 'Asgari Ağırlık', 'Alıkonulabilir Miktar', 'Zaman Yasağı'},
    }
    for section_id, columns in expected_columns.items():
        items = sections[section_id]['items']
        if not items or any(set(row['details']) != columns for row in items):
            raise AssertionError(f'Tür çizelgesi {section_id} sütunları eksik veya tutarsız')
    if any('Kaynak' in row['details'] for section in sections.values() for row in section['items']):
        raise AssertionError('Pratik Tür Çizelgesinde Kaynak sütunu kalmış')
    if not all(any(row['title'] == 'Diğer türler' for row in sections[sid]['items']) for sid in ('2.2', '3.2')):
        raise AssertionError('Pratik Tür Çizelgesinde Diğer türler satırı eksik')
    if any(re.search(r'\b\d{2}-\d{2}\b', str(row['details']))
           for section in sections.values() for row in section['items']):
        raise AssertionError('Pratik Tür Çizelgesinde teknik tarih biçimi kalmış')
    ahtapot = next(row for row in sections['1.2']['items'] if row['title'] == 'Ahtapot')['details']
    kurbaga = next(row for row in sections['3.1']['items'] if row['title'] == 'Kurbağa')['details']
    yayin = next(row for row in sections['3.1']['items'] if row['title'] == 'Yayın')['details']
    if (ahtapot['Asgari Boy'], ahtapot['Asgari Ağırlık'], ahtapot['Zaman Yasağı']) != (
            '—', '0,75 kg', '15 Nisan – 31 Ekim'):
        raise AssertionError('Ahtapot satırındaki boy/ağırlık/zaman değerleri hatalı')
    if kurbaga['Asgari Ağırlık'] != '30 gr' or 'Antalya ve Muğla' not in kurbaga['Zaman Yasağı']:
        raise AssertionError('Kurbağa satırındaki ağırlık veya bölgesel yasak hatalı')
    if 'Uluabat Gölü’nde dönem boyunca yasak' not in yayin['Zaman Yasağı']:
        raise AssertionError('Yayın türünün özel zaman yasağı eksik')
    sudak = next(row for row in sections['3.1']['items'] if row['title'] == 'Sudak')['details']
    if 'Eğirdir' not in sudak['Zaman Yasağı']:
        raise AssertionError('Sudak türünün Eğirdir Gölü yasağı eksik')
    if any(marker in str(row['details']) for row in sections['3.4']['items']
           for marker in ('\\', '(aynı türler)', '…', 'Dosya 04')):
        raise AssertionError('Amatör içsu bölgesel yasak tablosunda kısaltılmış veya bozuk satır kalmış')
    if any('*' in row['title'] or row['title'] == 'Istakoz'
           for section in sections.values() for row in section['items']):
        raise AssertionError('Pratik Tür Çizelgesinde düzeltilmemiş tür adı kalmış')
    print('structured data: canonical source build verified')


def check_items_table():
    """Ceza/tür tabloları yalnızca bazı satırlarda olan sütunları da göstermeli."""
    sys.path.insert(0, str(ADDON))
    import screens
    groups = screens.CEZA_REHBERI + [sub for group in screens.TUR_CIZELGESI for sub in group.get('sub', [])]
    for group in groups:
        if not group.get('items'):
            continue
        headers = re.findall(r'<th>(.*?)</th>', screens.items_table(group['items']))
        keys = {screens.esc(key) for row in group['items'] for key in row['details']}
        if len(headers) != len(keys) or set(headers) != keys:
            raise AssertionError(f"{group['title']} tablosunda gizli sütun var: {sorted(keys - set(headers))}")
    print('items table: all columns visible')


def check_dataset_migration(work):
    """6.0.14 ve öncesindeki tür tabloları yerinde yükseltilebilmeli."""
    sys.path.insert(0, str(ADDON))
    import db
    migration_db = work / 'migration.db'
    with sqlite3.connect(migration_db) as con:
        con.executescript('''
            CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
            INSERT INTO meta VALUES('dataset', 'v6');
            CREATE TABLE commercial_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min_cm REAL, min_kg REAL, time_bans TEXT, article_time INTEGER, search_text TEXT);
            CREATE TABLE amateur_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min_cm REAL, min_kg REAL, limit_text TEXT, time_bans TEXT, search_text TEXT);
            CREATE TABLE prohibited_species(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, search_text TEXT);
        ''')
    db.DB_PATH = migration_db
    db.init_db()
    with sqlite3.connect(migration_db) as con:
        counts = [con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in
                  ('commercial_species', 'amateur_species', 'prohibited_species')]
        dataset = con.execute("SELECT v FROM meta WHERE k='dataset'").fetchone()[0]
    if dataset != db.DATASET or counts != [65, 54, 53]:
        raise AssertionError(f'Veri kümesi geçişi başarısız: dataset={dataset}, counts={counts}')
    print(f'dataset migration {dataset}: verified ({counts})')


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'X-Requested-With': 'SuUrunleri', 'Content-Type': 'application/json'})
    try:
        with opener.open(req, timeout=60) as r:
            raw = r.read()
            return r.status, json.loads(raw or b'{}') if 'json' in r.headers.get('Content-Type', '') else raw
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


def text_of(view):
    return '\n'.join(view.get('blocks', []))


def main():
    check_source_integrity()
    check_structured_data()
    check_items_table()
    work = Path(tempfile.mkdtemp(prefix='suurunleri_smoke_'))
    check_dataset_migration(work)
    env = dict(os.environ, WEB_PORT=str(WEB_PORT), INGRESS_PORT=str(INGRESS_PORT), GEMINI_API_KEY='',
               PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    log_path = work / 'server.log'
    proc = subprocess.Popen([sys.executable, '-u', str(ADDON / 'web.py')], cwd=work, env=env,
                            stdout=open(log_path, 'w', encoding='utf-8'), stderr=subprocess.STDOUT)
    errors, presses = [], 0
    try:
        for _ in range(100):
            try:
                if call('/health')[0] == 200:
                    break
            except OSError:
                time.sleep(0.2)
        print('health', call('/health'))
        print('index', call('/')[0], 'app.js', call('/static/app.js')[0])
        print('screen before login (expect 401)', call('/api/screen')[0])
        code = (work / 'setup_code').read_text()
        print('setup', call('/api/setup', {'code': code, 'username': 'deneme', 'display_name': 'Deneme',
                                           'password': 'DenemeSifre123!'}))

        # Üyelik başvurusu onaylanmadan giriş yapamamalı; onaydan sonra
        # açılmalı. Şifre talebi yönetici listesine düşmeli ve yeni şifre
        # verilince kapanmalı.
        registration_password = 'BasvuruKaydaGirmemeli123!'
        s, registered = call('/api/register', {
            'first_name': 'Aday', 'last_name': 'Kişi', 'email': 'aday@example.com',
            'phone': '0532 123 45 67', 'position': 'uzman', 'username': 'aday',
            'password': registration_password,
        })
        if s != 200:
            errors.append((('REGISTRATION', 'create'), s, registered))
        s, people = call('/api/people')
        candidate = next((p for p in people.get('people', []) if p['username'] == 'aday'), None)
        if s != 200 or not candidate or candidate['approval_status'] != 'pending' or candidate['is_active']:
            errors.append((('REGISTRATION', 'pending'), s, candidate or people))
        if call('/api/login', {'username': 'aday', 'password': registration_password})[0] != 401:
            errors.append((('REGISTRATION', 'blocked_login'), 0, 'onaysız hesap giriş yapabildi'))
        if candidate:
            s, approved = call(f'/api/people/{candidate["id"]}', {'approval_status': 'approved'})
            if s != 200 or not approved['person']['is_active']:
                errors.append((('REGISTRATION', 'approve'), s, approved))
        if call('/api/login', {'username': 'aday', 'password': registration_password})[0] != 200:
            errors.append((('REGISTRATION', 'approved_login'), 0, 'onaylı hesap giriş yapamadı'))
        call('/api/logout', {})
        call('/api/login', {'username': 'deneme', 'password': 'DenemeSifre123!', 'remember': False})
        if call('/api/password-reset', {'identifier': 'aday@example.com'})[0] != 200:
            errors.append((('PASSWORD_RESET', 'request'), 0, 'talep oluşturulamadı'))
        if call('/api/password-reset', {'identifier': 'olmayan@example.com'})[0] != 200:
            errors.append((('PASSWORD_RESET', 'generic'), 0, 'bilinmeyen hesap farklı yanıt verdi'))
        _, people = call('/api/people')
        candidate = next((p for p in people.get('people', []) if p['username'] == 'aday'), None)
        if not candidate or not candidate['reset_pending']:
            errors.append((('PASSWORD_RESET', 'visible'), 0, candidate or people))
        elif call(f'/api/people/{candidate["id"]}', {'password': 'AdayYeniSifre123!'})[0] != 200:
            errors.append((('PASSWORD_RESET', 'resolve'), 0, 'yeni şifre verilemedi'))
        _, people = call('/api/people')
        candidate = next((p for p in people.get('people', []) if p['username'] == 'aday'), None)
        if not candidate or candidate['reset_pending']:
            errors.append((('PASSWORD_RESET', 'closed'), 0, candidate or people))

        def replay(path):
            nonlocal presses
            status, view = 200, call('/api/action', {'data': 'menu'})[1]
            for data in path:
                status, view = call('/api/action', {'data': data})
                presses += 1
                if status != 200:
                    break
            return status, view

        def action(data):
            nonlocal presses
            presses += 1
            return call('/api/action', {'data': data})

        def answer_current_audit(view):
            """Aktif hızlı kontrolü tüm maddelere Evet diyerek sonuç ekranına taşır."""
            for _ in range(40):
                next_data = next((button.get('data') for row in view.get('buttons', []) for button in row
                                  if button.get('data', '').startswith('audit:quick:ans:')
                                  and button.get('data', '').endswith(':yes')), None)
                if not next_data:
                    return view
                status, view = action(next_data)
                if status != 200:
                    errors.append((('TARGETED_AUDIT', next_data), status, view))
                    return view
            errors.append((('TARGETED_AUDIT', 'loop'), 0, 'hızlı kontrol 40 soruda bitmedi'))
            return view

        # Yeni kaynak kapsamının yalnızca erişilebilir olması değil, doğru dala
        # yönelmesi de doğrulanır: içsu, tesis ve faaliyet-bazlı yasak türler.
        action('audit:start')
        action('audit:region:inland')
        s, view = call('/api/text', {'text': 'Ankara — Mogan Gölü'})
        for data in ('audit:activity:commercial', 'audit:length:none', 'audit:date:today',
                     'audit:subject:fishing', 'audit:gear:gırgır', 'audit:guided:check'):
            s, view = action(data)
        if s != 200:
            errors.append((('TARGETED_AUDIT', 'inland_questions'), s, view))
        inland_result = answer_current_audit(view)
        if ('İçsularda trol ve gırgır ağı kullanımı tamamen yasaktır' not in text_of(inland_result)
                or 'Mogan Gölü' not in text_of(inland_result)):
            errors.append((('TARGETED_AUDIT', 'inland_result'), 0, inland_result))

        action('audit:start')
        for data in ('audit:region:facility', 'audit:activity:processing', 'audit:date:today',
                     'audit:subject:facility'):
            s, view = action(data)
        if s != 200 or 'çalışma izni' not in text_of(view):
            errors.append((('TARGETED_AUDIT', 'facility_questions'), s, view))
        facility_result = answer_current_audit(view)
        facility_text = text_of(facility_result)
        if 'İşleme / değerlendirme tesisi' not in facility_text or 'Gemi/Tekne' in facility_text:
            errors.append((('TARGETED_AUDIT', 'facility_result'), 0, facility_result))

        action('menu')
        action('species:menu')
        action('species:kind:commercial:inland')
        s, view = call('/api/text', {'text': 'yayın'})
        species_data = next((button.get('data') for row in view.get('buttons', []) for button in row
                             if button.get('data', '').startswith('sp:commercial:')), None)
        if s != 200 or not species_data:
            errors.append((('TARGETED_SPECIES', 'inland_search'), s, view))
        else:
            s, species_view = action(species_data)
            if s != 200 or 'İçsu' not in text_of(species_view) or '90 cm' not in text_of(species_view):
                errors.append((('TARGETED_SPECIES', 'inland_card'), s, species_view))

        action('species:menu')
        action('species:kind:prohibited:commercial')
        _, commercial_forbidden = call('/api/text', {'text': 'yılan balığı'})
        action('species:menu')
        action('species:kind:prohibited:amateur')
        _, amateur_forbidden = call('/api/text', {'text': 'yılan balığı'})
        commercial_hits = [b for row in commercial_forbidden.get('buttons', []) for b in row
                           if b.get('data', '').startswith('art:')]
        amateur_hits = [b for row in amateur_forbidden.get('buttons', []) for b in row
                        if b.get('data', '').startswith('art:')]
        if commercial_hits or not amateur_hits:
            errors.append((('TARGETED_SPECIES', 'activity_prohibition'), 0,
                           {'commercial': commercial_forbidden, 'amateur': amateur_forbidden}))
        print('targeted source-scope flows: verified')

        seen, stack = set(), [()]
        while stack and presses < MAX_PRESSES:
            path = stack.pop()
            status, view = replay(path)
            if status != 200 or any(m in text_of(view) for m in ERROR_MARKERS):
                errors.append((path, status, view if status != 200 else text_of(view)[:200]))
                continue
            if view.get('mode'):
                for sample in SAMPLE_TEXTS:
                    s2, v2 = call('/api/text', {'text': sample})
                    if s2 != 200 or any(m in text_of(v2) for m in ERROR_MARKERS):
                        errors.append((path + (f'TEXT:{sample}',), s2, v2 if s2 != 200 else text_of(v2)[:200]))
                    replay(path)
            if len(path) >= MAX_DEPTH:
                continue
            for row in view.get('buttons', []):
                for button in row:
                    data = button.get('data')
                    if data and data not in seen:
                        seen.add(data)
                        stack.append(path + (data,))
        print(f'distinct buttons visited: {len(seen)}, presses: {presses}')

        # Hesap işlemlerinin denetim kaydı oluşmalı; parola değerleri kayda
        # kesinlikle girmemeli.
        secret_a, secret_b = 'KaydaGirmemeli123!', 'YeniKaydaGirmemeli123!'
        s, created = call('/api/people', {'username': 'ikinci', 'display_name': 'İkinci Kişi',
                                          'password': secret_a, 'is_admin': False})
        if s != 200:
            errors.append((('ACTIVITY_ACCOUNT', 'create'), s, created))
        else:
            s, changed = call(f'/api/people/{created["person"]["id"]}', {'password': secret_b})
            if s != 200:
                errors.append((('ACTIVITY_ACCOUNT', 'update'), s, changed))
        s, changed = call('/api/password', {'current': 'DenemeSifre123!',
                                             'new': 'DenemeYeniSifre123!'})
        if s != 200:
            errors.append((('ACTIVITY_ACCOUNT', 'password'), s, changed))
        call('/api/logout', {})
        s, logged_in = call('/api/login', {'username': 'deneme', 'password': 'DenemeYeniSifre123!',
                                            'remember': False})
        if s != 200:
            errors.append((('ACTIVITY_ACCOUNT', 'login'), s, logged_in))

        issue_message = 'Duman testi sorun bildirimi'
        s, reported = call('/api/issues', {'message': issue_message})
        if s != 200:
            errors.append((('ISSUE_REPORT', 'create'), s, reported))
        s, issue_view = call('/api/action', {'data': 'admin:issues'})
        if s != 200 or issue_message not in text_of(issue_view):
            errors.append((('ISSUE_REPORT', 'admin_view'), s, issue_view))
        resolve_data = next((button['data'] for row in issue_view.get('buttons', []) for button in row
                             if button.get('data', '').startswith('admin:issue:resolve:')), None)
        if not resolve_data:
            errors.append((('ISSUE_REPORT', 'resolve_button'), 0, issue_view))
        else:
            s, resolved = call('/api/action', {'data': resolve_data})
            if s != 200 or issue_message in text_of(resolved):
                errors.append((('ISSUE_REPORT', 'resolve'), s, resolved))

        with sqlite3.connect(work / 'su_urunleri_kolluk.db') as audit_db:
            activity = dict(audit_db.execute(
                'SELECT action, COUNT(*) FROM activity_log GROUP BY action').fetchall())
            activity_text = '\n'.join(row[0] or '' for row in audit_db.execute(
                'SELECT detail FROM activity_log').fetchall())
            issue_statuses = dict(audit_db.execute(
                'SELECT status, COUNT(*) FROM issue_reports GROUP BY status').fetchall())
        print('activity log:', activity)
        for required in ('setup', 'login', 'logout', 'button', 'text', 'password_change',
                         'person_create', 'person_update', 'registration', 'password_reset_request',
                         'issue_report', 'issue_resolve'):
            if not activity.get(required):
                errors.append((('ACTIVITY_LOG', required), 0, 'beklenen işlem kaydı yok'))
        if any(secret in activity_text for secret in (secret_a, secret_b, registration_password,
                                                       'AdayYeniSifre123!')):
            errors.append((('ACTIVITY_LOG', 'password'), 0, 'parola işlem kaydına yazılmış'))
        if not issue_statuses.get('resolved'):
            errors.append((('ISSUE_REPORT', 'database'), 0, issue_statuses))
        print('errors:', len(errors))
        for e in errors[:40]:
            print('  ', e)
    finally:
        proc.terminate()
        proc.wait()
        print('---- server log (tail) ----')
        print(log_path.read_text(encoding='utf-8')[-3000:])
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
