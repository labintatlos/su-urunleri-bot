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


# Depo herkese açıktır: paketlenen Markdown kopyasına kurum içi sınıflandırmalı
# bir yayın girmemelidir.
RESTRICTED_MARKERS = ('HİZMETE ÖZEL', 'Hizmete Özel', 'hizmete özel', 'KİŞİYE ÖZEL', 'SGYY 164', 'SGD 205')


def check_source_integrity():
    """Paket kopyası manifestle birebir uyuşmalı.

    Ana kaynak klasörü depoda değil, yalnızca geliştirme bilgisayarında durur ve
    manifestte olmayan yerel belgeler (kurum içi yayınlar) içerebilir. Klasör
    varsa manifestteki her kaynak orada da doğrulanır; yoksa (GitHub Actions)
    yalnızca paket kopyası doğrulanır ve paketlenmeyen Excel atlanır."""
    manifest = json.loads((ADDON / 'data' / 'sources.json').read_text(encoding='utf-8'))
    packaged = {p.name: p for p in PACKAGED_MARKDOWN.glob('*.md')}
    listed = {Path(source['filename']).name for source in manifest}
    stray = sorted(set(packaged) - listed)
    if stray:
        raise AssertionError(f'Manifestte olmayan paket Markdown dosyası: {stray}')
    for name, path in packaged.items():
        text = path.read_text(encoding='utf-8')
        found = [marker for marker in RESTRICTED_MARKERS if marker in text]
        if found:
            raise AssertionError(f'Paket Markdown dosyasında kısıtlı yayın işareti var: {name} {found}')

    canonical_present = CANONICAL_SOURCES.is_dir()
    checked = 0
    for source in manifest:
        name = Path(source['filename']).name
        paths = [REPO / source['filename']] if canonical_present else []
        if name.endswith('.md'):
            if name not in packaged:
                raise AssertionError(f'Manifest Markdown kaynağı paket kopyasında yok: {name}')
            paths.append(packaged[name])
        for path in paths:
            if not path.is_file():
                raise AssertionError(f'Manifest kaynağı bulunamadı: {source["filename"]}')
            if source_digest(path) != source['sha256']:
                raise AssertionError(f'Manifest özeti uyuşmuyor: {path}')
            checked += 1
    where = 'ana klasör + paket kopyası' if canonical_present else 'paket kopyası (ana klasör depoda yok)'
    print(f'sources {len(packaged)} Markdown, {checked} dosya özeti ({where}): verified')


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
    penalty_guide = json.loads((ADDON / 'data' / 'ceza_rehberi_v2.json').read_text(encoding='utf-8'))
    penalty_rows = [row for group in penalty_guide
                    for row in group['items'] + [r for sub in group.get('sub', []) for r in sub['items']]]
    if not penalty_rows or any('Kaynak' in row['details'] for row in penalty_rows):
        raise AssertionError('Pratik Ceza Rehberinde Kaynak sütunu kalmış')
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
    import build_penalty_links
    links, link_errors = build_penalty_links.build(write_report=False)
    if link_errors:
        raise AssertionError('Yaptırım eşleştirmesi sağlaması başarısız: ' + '; '.join(link_errors[:5]))
    if (ADDON / 'data' / 'penalty_links.json').read_bytes() != build_penalty_links.dump(links):
        raise AssertionError('penalty_links.json güncel değil: python tools/build_penalty_links.py')
    print(f'penalty links: {len(links["guides"])} föy maddesi, {len(links["questions"])} soru, '
          f'{len(links["flags"])} uyarı eşleştirmesi verified')
    import verify_penalties
    cards = json.loads((ADDON / 'data' / 'penalty_cards.json').read_text(encoding='utf-8'))
    fresh = verify_penalties.apply(json.loads(json.dumps(cards)))
    law_errors = verify_penalties.verify(fresh)
    if law_errors:
        raise AssertionError('Ceza dosyası Kanun sağlaması başarısız: ' + '; '.join(law_errors[:5]))
    if fresh != cards:
        raise AssertionError('penalty_cards.json Kanun sağlamasıyla güncel değil: python tools/rebuild_structured_data.py')
    by_id = {card['id']: card for card in cards}
    expected = [(69, 'Gırgır', 71076), (70, 'Gırgır', 71076), (96, '≥22 m', 28419), (98, '12–<22 m', 94794),
                (100, '≥22 m', 48318), (45, '≥22 m', 21315)]
    if (any(by_id[cid]['amounts'].get(key) != value for cid, key, value in expected)
            or by_id[74]['base_ipc'] != 66357 or by_id[109]['base_ipc'] != 568890 or by_id[140]['art36'] != 'e'
            or not {154, 155, 156, 157} <= set(by_id) or by_id[78]['teblig'] != '49/9'
            or 'hapis' not in by_id[73]['repeat'] or any('law_check' not in card for card in cards)):
        raise AssertionError('Ceza dosyası Kanun düzeltmeleri veya eklenen hükümler eksik')
    saglama = next((group for group in penalty_guide if group['id'] == 'saglama'), None)
    if not saglama or len(saglama['items']) != len(verify_penalties.LAW36):
        raise AssertionError('Ceza Rehberinde Kanun 36 Sağlaması başlığı eksik')
    print(f'penalty law check: {len(cards)} kart, {len(verify_penalties.LAW36)} Kanun 36 hükmü verified')


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


def check_sanction_coverage():
    """Her yaptırım profili her boy/gırgır durumunda satır üretmeli; her föy maddesi,
    denetim sorusu ve otomatik uyarı yaptırım özetinde ve çizelgede hatasız işlenmeli."""
    sys.path.insert(0, str(ADDON))
    from types import SimpleNamespace
    import screens
    links = screens.PENALTY_LINKS
    problems = []
    ranges = [None, (0.0, 12.0), (12.0, 22.0), (22.0, None)]
    for name, profile in links['profiles'].items():
        if profile['kind'] == 'none':
            continue
        for rng in ranges:
            for purse_seine in (False, True):
                rows = screens.sanction_profile_rows(name, rng, purse_seine)
                if not rows or any('None' in str(row) or row['İdari para cezası'] in ('', '—') for row in rows):
                    problems.append(f'{name} {rng} gırgır={purse_seine}')
    for guide in screens.GUIDE_LIST:
        missing = [row['no'] for row in guide['rows'] if f'{guide["key"]}:{row["no"]}' not in links['guides']]
        if missing:
            problems.append(f'{guide["key"]} eşleşmeyen: {missing}')
        for band in (None, 'lt12', '12to22', 'ge22'):
            data = {'guide_key': guide['key'], 'guide_answers': ['bad'] * len(guide['rows'])}
            if band:
                data['audit_length_band'] = band
            context = SimpleNamespace(user_data=data)
            findings, _ = screens.sanction_findings(context, 'guide')
            text, _ = screens.render_sanction_summary(context, 'guide')
            if len(findings) != len(guide['rows']) or 'YAPTIRIM ÖZETİ' not in text \
                    or not screens.sanction_sheet_block(context, 'guide'):
                problems.append(f'{guide["key"]} {band}')
    questions = [{'q': tag, 'expected': 'yes', 'ref': ('61', 50), 'tag': tag} for tag in links['questions']]
    flags = [{'tag': key, 'ref': ('61', 50), 'key': key} for key in links['flags']]
    context = SimpleNamespace(user_data={'quick_questions': questions, 'quick_answers': ['no'] * len(questions),
                                         'context_flags': flags, 'audit_region': 'marmara',
                                         'audit_gear': 'gırgır', 'audit_length_band': '12to22'})
    findings, _ = screens.sanction_findings(context, 'audit')
    if len(findings) != len(questions) + len(flags) or not screens.sanction_sheet_block(context, 'audit'):
        problems.append('denetim soruları/uyarıları')
    screens.render_sanction_summary(context, 'audit')
    if problems:
        raise AssertionError('Yaptırım özeti kapsam hatası: ' + '; '.join(problems[:10]))
    print(f'sanction coverage: {len(links["profiles"])} profil × {len(ranges)} boy × gırgır, '
          f'{len(links["guides"])} föy maddesi, {len(questions)} soru, {len(flags)} uyarı verified')


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
    check_sanction_coverage()
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

        # Boğazlar ayrı bölge değildir: tek "Marmara Denizi" düğmesi vardır ve
        # eski boğaz değeri (kayıtlı düğme) Marmara kurallarıyla sonuçlanır.
        s, view = action('audit:start')
        region_buttons = [button.get('data') for row in view.get('buttons', []) for button in row]
        if ('audit:region:marmara' not in region_buttons
                or any('istanbul' in b or 'canakkale' in b for b in region_buttons)
                or 'Marmara Denizi' not in json.dumps(view.get('buttons'), ensure_ascii=False)):
            errors.append((('TARGETED_AUDIT', 'marmara_region_buttons'), s, view))
        for data in ('audit:region:istanbul', 'audit:activity:commercial', 'audit:length:none',
                     'audit:date:today', 'audit:subject:fishing', 'audit:gear:dip trolü', 'audit:guided:check'):
            s, view = action(data)
        marmara_result = answer_current_audit(view)
        if ('Seçilen bölgede trol yasağı' not in text_of(marmara_result)
                or 'Marmara Denizi' not in text_of(marmara_result)):
            errors.append((('TARGETED_AUDIT', 'marmara_result'), 0, marmara_result))

        # 6.0.27: uluslararası sularda duruma özel sorular ve ilgili föy
        # önerileri çıkmalı; iki sonuç ekranından da kontrol çizelgesi
        # açılabilmeli.
        action('audit:start')
        for data in ('audit:region:international', 'audit:activity:commercial', 'audit:length:12to22',
                     'audit:date:today', 'audit:subject:fishing', 'audit:gear:gırgır', 'audit:guided:check'):
            s, view = action(data)
        intl_result = answer_current_audit(view)
        intl_buttons = [button.get('data') for row in intl_result.get('buttons', []) for button in row]
        if ('guide:open:24_Uluslararasi_Sular' not in intl_buttons or 'audit:sheet' not in intl_buttons
                or 'guide:open:25_Orkinos_Kilic' not in intl_buttons):
            errors.append((('TARGETED_AUDIT', 'international_result'), 0, intl_buttons))
        s, sheet = action('audit:sheet')
        sheet_text = text_of(sheet)
        if (s != 200 or 'KONTROL ÇİZELGESİ' not in sheet_text or '<table>' not in sheet_text
                or 'münhasır ekonomik bölgesinde' not in sheet_text or 'Tutanak no' not in sheet_text):
            errors.append((('CONTROL_SHEET', 'audit'), s, sheet_text[:300]))

        s, view = action('guide:start:25_Orkinos_Kilic')
        for _ in range(30):
            answer = next((button['data'] for row in view.get('buttons', []) for button in row
                           if button.get('data', '').startswith('guide:ans:')
                           and button['data'].endswith(':ok')), None)
            if not answer:
                break
            s, view = action(answer)
        if 'guide:sheet' not in [b.get('data') for row in view.get('buttons', []) for b in row]:
            errors.append((('CONTROL_SHEET', 'guide_result_button'), s, view))
        s, sheet = action('guide:sheet')
        sheet_text = text_of(sheet)
        if (s != 200 or 'KONTROL ÇİZELGESİ' not in sheet_text or 'eBCD' not in sheet_text
                or '✅ Uygun' not in sheet_text or 'ÖLÇÜM / KAYIT' not in sheet_text):
            errors.append((('CONTROL_SHEET', 'guide'), s, sheet_text[:300]))
        guide_keys = {guide['key'] for guide in json.loads(
            (ADDON / 'data' / 'vessel_guides.json').read_text(encoding='utf-8'))}
        missing_guides = {'23_Yabanci_Uyruk', '24_Uluslararasi_Sular', '25_Orkinos_Kilic',
                          '26_Balik_Ciftligi'} - guide_keys
        if missing_guides:
            errors.append((('GUIDES', 'new_guides'), 0, sorted(missing_guides)))
        s, view = action('field:Kolluk İşlemi')
        if s != 200 or not any(b.get('data') == 'rule:evidence_checklist' for row in view.get('buttons', []) for b in row):
            errors.append((('FIELD_RULES', 'evidence_checklist'), s, view))

        # 6.0.32 yaptırım özeti: Marmara trol uyarısı Kanun 36/l kartına, gırgır
        # föyündeki ruhsat ve av dönemi uygunsuzlukları ilgili kartlara ve boya göre
        # doğru kademeye bağlanmalı; çizelgede ön bilgi bölümü çıkmalı.
        action('audit:start')
        for data in ('audit:region:marmara', 'audit:activity:commercial', 'audit:length:none',
                     'audit:date:today', 'audit:subject:fishing', 'audit:gear:dip trolü', 'audit:guided:check'):
            s, view = action(data)
        answer_current_audit(view)
        s, sanction = action('sanction:audit')
        sanction_text = text_of(sanction)
        if (s != 200 or 'YAPTIRIM ÖZETİ' not in sanction_text or 'İçsular, Marmara ve boğazlarda trol' not in sanction_text
                or '189.630 TL' not in sanction_text):
            errors.append((('SANCTION', 'audit_marmara'), s, sanction_text[:400]))
        action('menu')  # önceki denetimin boy bilgisi föye taşınmasın
        action('guide:start:01_Girgir')
        action('guide:ans:0:bad')
        for idx in range(1, 9):
            action(f'guide:ans:{idx}:ok')
        action('guide:ans:9:bad')
        action('guide:finish')
        s, sanction = action('sanction:guide')
        sanction_text = text_of(sanction)
        if (s != 200 or 'Ruhsat tezkeresi olmadan avcılık — gemi' not in sanction_text
                or '474.079 TL' not in sanction_text or 'Gırgır gemisi: 71.076 TL' not in sanction_text
                or 'Yasak zamanda gırgır' not in sanction_text):
            errors.append((('SANCTION', 'guide_unknown_length'), s, sanction_text[:400]))
        s, sanction = action('sanction:band:guide:12to22')
        sanction_text = text_of(sanction)
        buttons = json.dumps(sanction.get('buttons', []), ensure_ascii=False)
        if ('Boyunu Gir' in buttons or not all(label in buttons for label in ('12 metre altı', '12–22 metre arası', '22 metre ve üstü'))):
            errors.append((('SANCTION', 'length_buttons'), s, buttons[:300]))
        if (s != 200 or '237.034 TL' not in sanction_text or '474.079 TL' in sanction_text
                or '47.384 TL (12–&lt;22 m)' not in sanction_text):
            errors.append((('SANCTION', 'guide_length_17'), s, sanction_text[:400]))
        s, sheet = action('guide:sheet')
        if s != 200 or 'YAPTIRIM ÖN BİLGİSİ' not in text_of(sheet):
            errors.append((('SANCTION', 'sheet_block'), s, text_of(sheet)[:300]))

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

        # 6.0.30 yönetici paneli: özet, süzgeçli işlem geçmişi, personel,
        # kişi özeti ve eski kayıt temizleme ekranları hatasız açılmalı.
        admin_screens = {
            'admin:panel': 'DİKKAT GEREKTİRENLER',
            'admin:log:all:all:0': 'İŞLEM GEÇMİŞİ',
            'admin:log:denetim:all:0': 'Denetim',
            'admin:log:arama:all:0': 'Arama yaptı',
            'admin:log:guvenlik:all:0': 'Hatalı şifreyle giriş denendi',
            'admin:users': 'PERSONEL',
            'admin:purge:ask': 'ESKİ KAYITLARI TEMİZLE',
        }
        for data, expected in admin_screens.items():
            s, admin_view = action(data)
            admin_text = text_of(admin_view)
            if s != 200 or expected not in admin_text or any(m in admin_text for m in ERROR_MARKERS):
                errors.append((('ADMIN_PANEL', data), s, admin_text[:300]))
        _, people = call('/api/people')
        candidate = next((p for p in people.get('people', []) if p['username'] == 'aday'), None)
        if candidate:
            s, person_view = action(f'admin:person:{candidate["id"]}')
            if s != 200 or 'Hatalı giriş' not in text_of(person_view):
                errors.append((('ADMIN_PANEL', 'person'), s, text_of(person_view)[:300]))

        with sqlite3.connect(work / 'su_urunleri_kolluk.db') as audit_db:
            activity = dict(audit_db.execute(
                'SELECT action, COUNT(*) FROM activity_log GROUP BY action').fetchall())
            activity_text = '\n'.join(row[0] or '' for row in audit_db.execute(
                'SELECT detail FROM activity_log').fetchall())
            issue_statuses = dict(audit_db.execute(
                'SELECT status, COUNT(*) FROM issue_reports GROUP BY status').fetchall())
        print('activity log:', activity)
        for required in ('setup', 'login', 'logout', 'password_change', 'login_failed',
                         'person_create', 'person_update', 'registration', 'password_reset_request',
                         'issue_report', 'issue_resolve', 'audit_start', 'audit_result', 'guide_start',
                         'guide_finish', 'control_sheet', 'search'):
            if not activity.get(required):
                errors.append((('ACTIVITY_LOG', required), 0, 'beklenen işlem kaydı yok'))
        # Gezinme (düğme basışı, yazılan her metin) artık kaydedilmez.
        for noise in ('button', 'text'):
            if activity.get(noise):
                errors.append((('ACTIVITY_LOG', f'no_{noise}'), 0, f'{activity[noise]} gezinme kaydı yazılmış'))
        with sqlite3.connect(work / 'su_urunleri_kolluk.db') as audit_db:
            uncategorized = audit_db.execute(
                'SELECT COUNT(*) FROM activity_log WHERE category IS NULL OR level IS NULL').fetchone()[0]
        if uncategorized:
            errors.append((('ACTIVITY_LOG', 'category'), 0, f'{uncategorized} kategorisiz kayıt'))
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
