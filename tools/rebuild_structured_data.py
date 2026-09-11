"""Yeni 03, 04 ve 08 rehberlerinden yapılandırılmış uygulama verilerini üretir.

    python tools/rebuild_structured_data.py
    python tools/rebuild_structured_data.py --check

Kanun/Tebliğ madde dökümü ile Excel ham satırları, yeni klasördeki aynı tam
metin ve aynı Excel dosyasından daha önce üretilmiştir. Bu betik değişen rehber
katmanını (türler, pratik ceza grupları, saha kartları) tekrar üretir.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'SU ÜRÜNLERİ KAYNAKLAR (MARKDOWN)'
DATA = ROOT / 'su_urunleri_bot' / 'data'
GUIDE_03 = SOURCE / '03 TÜRLERE GÖRE AV YASAKLARI, BOY-AĞIRLIK VE KOTALAR.md'
GUIDE_04 = SOURCE / '04 İÇSULAR, DALYAN VE LAGÜNLER.md'


def read_json(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def clean_cell(value):
    value = value.strip().replace('**', '').replace('`', '')
    return re.sub(r'\s+', ' ', value)


def tables(path):
    result, current = [], []
    for line in path.read_text(encoding='utf-8').splitlines() + ['']:
        if line.startswith('|') and line.endswith('|'):
            current.append([clean_cell(cell) for cell in line.strip('|').split('|')])
        elif current:
            if len(current) >= 3:
                result.append([current[0]] + current[2:])
            current = []
    return result


def number(value):
    if value in {'-', 'Yok', ''}:
        return None
    match = re.search(r'\d+(?:[.,]\d+)?', value)
    return float(match.group().replace(',', '.')) if match else None


COMMERCIAL_TIME = {
    'Ahtapot': (['04-15/10-31'], 31),
    'Akivades': (['04-15/08-31'], 28),
    'Akya': (['04-15/05-15'], 24),
    'Deniz böceği': (['09-02/04-14'], 30),
    'Dil': (['01-01/02-15'], 21),
    'İstakoz': (['09-02/04-14'], 30),
    'İstiridye': (['04-15/08-31'], 28),
    'Kalkan': (['04-15/06-15'], 21),
    'Kılıç (çatal boy)': (['02-15/03-15', '10-01/11-30'], 25),
    'Kidonya': (['04-15/08-31'], 28),
    'Kum şırlanı (Tellina)': (['04-15/08-31'], 28),
    'Lagos': (['06-01/08-31'], 26),
    'Lambuka': (['01-01/08-14'], 24),
    'Mavi yengeç': (['05-01/09-30'], 30),
    'Midye (Beyaz kum midyesi)': (['04-15/08-31'], 28),
    'Palamut': (['04-01/08-14'], 20),
    'Pisi': (['01-01/02-15'], 21),
    'Sarıkuyruk': (['04-15/05-15'], 24),
}

AMATEUR_TIME = {
    'Ahtapot': ['04-15/10-31'], 'Akya': ['04-15/05-15'],
    'Dil': ['01-01/02-15'], 'Kalkan': ['04-15/06-15'],
    'Kılıç (çatal boy)': ['02-15/03-15', '10-01/11-30'],
    'Lagos': ['06-01/08-31'], 'Lambuka': ['01-01/08-14'],
    'Mavi yüzgeçli orkinos (çatal boy)': ['10-15/06-15'],
    'Palamut': ['04-01/08-14'], 'Sarıkuyruk': ['04-15/05-15'],
    'Uzun kanat orkinos (tulina)': ['02-15/03-15', '10-01/11-30'],
}

INLAND_ARTICLE = {
    'Alabalık (3 doğal tür)': 42, 'İnci kefali': 39, 'Karabalık (Clarias gariepinus)': 41,
    'Karabalık (Capoeta trutta)': 41, 'Kerevit': 43, 'Kurbağa': 44,
    'Sudak': 40, 'Tatlısu levreği': 40, 'Turna': 40, 'Yayın': 39,
    'Yılan balığı': 41,
}

INLAND_AMATEUR_TIME = {
    'Doğal alabalık (tüm türler)': ['10-01/02-28'],
    'Sudak': ['03-15/04-30'], 'Tatlısu levreği': ['03-15/04-30'],
    'Turna': ['12-15/03-31'],
}

SPECIAL_TIME_TEXT = {
    'Mavi yüzgeçli orkinos (çatal boy VEYA ağırlık)':
        'Bölgeye göre: Akdeniz/Ege 1 Temmuz – 14 Mayıs; diğer alanlar 1 Temmuz – 25 Mayıs',
}

INLAND_COMMERCIAL_TIME_TEXT = {
    'Alabalık (3 doğal tür)': '1 Ekim – 28 Şubat; bazı sularda dönem boyunca yasak',
    'Fırat turnası': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'İnci kefali': 'Van Gölü havzasında 15 Nisan – 15 Temmuz',
    'Kadife': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'Karabalık (*Clarias gariepinus*)': '1 Nisan – 30 Haziran',
    'Karabalık (*Capoeta trutta*)': '1 Nisan – 30 Haziran',
    'Kerevit': '15 Kasım – 15 Haziran',
    'Kurbağa': 'Bölgeye göre değişir; Antalya ve Muğla’da dönem boyunca yasak',
    'Maya': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'Sazan': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'Siraz': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'Sudak': '15 Mart – 30 Nisan ve bölgesel sazangiller yasağı; Eğirdir Gölü’nde dönem boyunca, '
             'Beyşehir Gölü’nde paraketeyle dönem boyunca yasak',
    'Şabut': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'Tatlısu kefali': 'Bölgesel sazangiller yasağı — bkz. 3.3',
    'Tatlısu levreği': '15 Mart – 30 Nisan ve bölgesel sazangiller yasağı; Eğirdir Gölü’nde dönem boyunca, '
                       'Beyşehir Gölü’nde paraketeyle dönem boyunca yasak',
    'Turna': '15 Aralık – 31 Mart; Işıklı ve Karamık göllerinde ayrıca sazan yasağı döneminde',
    'Yayın': 'Bölgesel sazangiller yasağı; Uluabat Gölü’nde dönem boyunca yasak',
    'Yılan balığı': '1 Nisan – 30 Eylül',
}

INLAND_AMATEUR_TIME_TEXT = {
    'Doğal alabalık (tüm türler)': '1 Ekim – 28 Şubat',
    'Gökkuşağı alabalığı': 'Yok (orman içi sular hariç)',
    'Kadife': 'Bölgesel — bkz. 3.4',
    'Sazan': 'Bölgesel — bkz. 3.4',
    'Siraz': 'Bölgesel — bkz. 3.4',
    'Sudak': '15 Mart – 30 Nisan',
    'Tatlısu kefali': 'Bölgesel; akarsularda (orman içi hariç) yok — bkz. 3.4',
    'Tatlısu levreği': '15 Mart – 30 Nisan',
    'Turna': '15 Aralık – 31 Mart',
    'Yayın': 'Bölgesel — bkz. 3.4',
    'Diğer türler': 'Bölgesel — bkz. 3.4',
}


def build_species():
    sea_tables = tables(GUIDE_03)
    inland_tables = tables(GUIDE_04)
    if len(sea_tables) < 2 or len(inland_tables) < 5:
        raise ValueError('03/04 rehberlerindeki tür tabloları bulunamadı')

    commercial = []
    for species, cm, kg in sea_tables[0][1:]:
        bans, article_time = COMMERCIAL_TIME.get(species, ([], None))
        commercial.append({
            'name': species, 'min_cm': number(cm), 'min_kg': number(kg),
            'time_bans': bans, 'source': '61', 'article_size': 17,
            'article_time': article_time, 'scope': 'sea', 'source_doc': GUIDE_03.name,
        })

    amateur = []
    for species, size, limit, _time_text in sea_tables[1][1:]:
        if species == 'Diğer türler':
            continue
        amount = number(size)
        is_weight = 'gr' in size.casefold()
        amateur.append({
            'name': species, 'min_cm': None if is_weight else amount,
            'min_kg': amount / 1000 if is_weight and amount is not None else None,
            'limit': limit, 'time_bans': AMATEUR_TIME.get(species, []),
            'source': '62', 'article': 15, 'scope': 'sea', 'source_doc': GUIDE_03.name,
        })

    for species, cm, grams in inland_tables[2][1:]:
        commercial.append({
            'name': species, 'min_cm': number(cm),
            'min_kg': number(grams) / 1000 if number(grams) is not None else None,
            'time_bans': [], 'source': '61', 'article_size': 38,
            'article_time': INLAND_ARTICLE.get(species), 'scope': 'inland',
            'source_doc': GUIDE_04.name,
        })

    for species, size, limit in inland_tables[3][1:]:
        if species == 'Diğer türler':
            continue
        amateur.append({
            'name': species, 'min_cm': number(size), 'min_kg': None, 'limit': limit,
            'time_bans': INLAND_AMATEUR_TIME.get(species, []), 'source': '62',
            'article': 11, 'scope': 'inland', 'source_doc': GUIDE_04.name,
        })
    return commercial, amateur, inland_tables


def prohibited_names():
    text = GUIDE_03.read_text(encoding='utf-8')
    match = re.search(r'\n(Akdeniz foku,.*?Yunus ve Balinalar)\.', text, re.S)
    if not match:
        raise ValueError('03 rehberindeki yasak tür listesi bulunamadı')
    commercial = [clean_cell(name) for name in match.group(1).replace('\n', ' ').split(', ')]
    amateur_extra = ['Alakır alası', 'Ticari deniz süngerleri', 'Yılan balığı']
    return commercial, commercial + amateur_extra


def item(title, details, index):
    return {'id': str(index), 'title': title, 'details': details}


MONTHS = ('', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
          'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')


def display_number(value):
    return f'{value:g}'.replace('.', ',')


def display_bans(bans):
    periods = []
    for period in bans:
        start, end = period.split('/')
        sm, sd = map(int, start.split('-'))
        em, ed = map(int, end.split('-'))
        periods.append(f'{sd} {MONTHS[sm]} – {ed} {MONTHS[em]}')
    return ', '.join(periods) if periods else '—'


def species_detail(row, amateur=False):
    if row['min_kg'] is None:
        weight = '—'
    elif row.get('scope') == 'inland':
        weight = f"{display_number(row['min_kg'] * 1000)} gr"
    else:
        weight = f"{display_number(row['min_kg'])} kg"
    details = {
        'Türkçe Adı': display_name(row['name']),
        'Asgari Boy': f"{display_number(row['min_cm'])} cm" if row['min_cm'] is not None else '—',
        'Asgari Ağırlık': weight,
    }
    if amateur:
        details['Alıkonulabilir Miktar'] = row['limit']
    details['Zaman Yasağı'] = row.get('display_time') or SPECIAL_TIME_TEXT.get(row['name']) or display_bans(row['time_bans'])
    return details


DISPLAY_NAMES = {'Istakoz': 'İstakoz'}


def display_name(name):
    return DISPLAY_NAMES.get(name, name).replace('*', '')


def table_items(table, prefix, rows=None):
    headers = table[0]
    values = []
    for n, row in enumerate(table[1:] if rows is None else rows):
        details = {headers[i]: value.replace(' - ', ' – ') for i, value in enumerate(row)
                   if i < len(headers) and headers[i].casefold() != 'kaynak'}
        values.append(item(row[0], details, f'{prefix}_{n}'))
    return values


def amateur_inland_region_rows(inland_tables):
    """Çizelge 6'daki kısaltılmış satırları ("Tatlısu kefali\\*", "(aynı türler)",
    "Afyonkarahisar…Zonguldak") sazangiller tablosundaki tam il listeleriyle açar."""
    carp, amateur = inland_tables[1], inland_tables[4]
    species = amateur[1][0].replace('\\*', ' (akarsular hariç)')
    rows = []
    for n, row in enumerate(amateur[1:]):
        row = list(row)
        if n < len(carp) - 1:
            region, period = carp[n + 1]
            if row[2] != period or (n and row[0] != '(aynı türler)'):
                raise ValueError('04 rehberindeki amatör içsu bölge satırları sazangiller tablosuyla eşleşmiyor')
            row[:2] = [species, region]
        rows.append(row)
    return rows


def build_species_guide(commercial, amateur, inland_tables):
    commercial_forbidden, amateur_forbidden = prohibited_names()
    sea_commercial = [x for x in commercial if x['scope'] == 'sea']
    sea_amateur = [x for x in amateur if x['scope'] == 'sea']
    inland_commercial = [x for x in commercial if x['scope'] == 'inland']
    inland_amateur = [x for x in amateur if x['scope'] == 'inland']
    sea_other = {'name': 'Diğer türler', 'min_cm': None, 'min_kg': None, 'limit': '5 kg', 'time_bans': []}
    inland_other = {'name': 'Diğer türler', 'min_cm': None, 'min_kg': None, 'limit': '5 kg', 'time_bans': [],
                    'display_time': INLAND_AMATEUR_TIME_TEXT['Diğer türler']}
    inland_commercial = [dict(row, display_time=INLAND_COMMERCIAL_TIME_TEXT.get(row['name']))
                         for row in inland_commercial]
    inland_amateur = [dict(row, display_time=INLAND_AMATEUR_TIME_TEXT.get(row['name'], 'Bölgesel — bkz. 3.4'))
                      for row in inland_amateur]

    return [
        {
            'id': '1', 'title': '1. Ticari Avcılık', 'items': [],
            'sub': [
                {'id': '1.1', 'title': '1.1 Bütün Sularda Avlanması Tamamen Yasak Türler',
                 'items': [item(name, {'Türkçe Adı': name, 'Kapsam': 'Ticari avcılıkta tamamen yasak'}, f'1.1_{i}') for i, name in enumerate(commercial_forbidden)]},
                {'id': '1.2', 'title': '1.2 Deniz Ürünleri Asgari Boy, Ağırlık ve Zaman Kuralları',
                 'items': [item(display_name(row['name']), species_detail(row), f'1.2_{i}') for i, row in enumerate(sea_commercial)]},
            ], 'content': '', 'source_doc': GUIDE_03.name,
        },
        {
            'id': '2', 'title': '2. Amatör Avcılık', 'items': [],
            'sub': [
                {'id': '2.1', 'title': '2.1 Bütün Sularda Avlanması Tamamen Yasak Türler',
                 'items': [item(name, {'Türkçe Adı': name, 'Kapsam': 'Amatör avcılıkta tamamen yasak'}, f'2.1_{i}') for i, name in enumerate(amateur_forbidden)]},
                {'id': '2.2', 'title': '2.2 Deniz Türleri Boy, Miktar ve Zaman Kuralları',
                 'items': [item(display_name(row['name']), species_detail(row, True), f'2.2_{i}')
                           for i, row in enumerate(sea_amateur + [sea_other])]},
            ], 'content': '', 'source_doc': GUIDE_03.name,
        },
        {
            'id': '3', 'title': '3. İçsu Türleri ve Bölgesel Zaman Yasakları', 'items': [],
            'sub': [
                {'id': '3.1', 'title': '3.1 Ticari İçsu Asgari Boy/Ağırlık',
                 'items': [item(display_name(row['name']), species_detail(row), f'3.1_{i}') for i, row in enumerate(inland_commercial)]},
                {'id': '3.2', 'title': '3.2 Amatör İçsu Boy/Miktar',
                 'items': [item(display_name(row['name']), species_detail(row, True), f'3.2_{i}')
                           for i, row in enumerate(inland_amateur + [inland_other])]},
                {'id': '3.3', 'title': '3.3 Ticari Sazangiller Bölgesel Zaman Yasakları',
                 'items': table_items(inland_tables[1], '3.3')},
                {'id': '3.4', 'title': '3.4 Amatör İçsu Bölgesel Zaman Yasakları',
                 'items': table_items(inland_tables[4], '3.4', amateur_inland_region_rows(inland_tables))},
            ], 'content': '', 'source_doc': GUIDE_04.name,
        },
    ]


PENALTY_TITLES = {
    'a': 'A) Ruhsat ve İzin Belgesi İhlalleri',
    'b': 'B) İstihsal Hakkı Kiralama İhlalleri',
    'c': 'C) İstihsal Yerinde Değişiklik',
    'd': 'D) Su Alımı ve Çevresel Tedbir İhlalleri',
    'e': 'E) İzinsiz Yetiştiricilik Tesisi ve Yönetmelik İhlalleri',
    'f': 'F) Balıkçı Barınakları Mevzuatına Aykırılık',
    'g': 'G) Patlayıcı/Zehirli Madde ile Avcılık',
    'h': 'H) Sulara Zararlı Madde Dökülmesi',
    'i': 'I) Yabancıların Su Ürünleri İstihsali Yasağı',
    'j': 'J) Akarsu Engelleme ve Balık Geçidi İhlalleri',
    'k': 'K) Ticari Avcılık Usul ve Esasına Aykırılık',
    'l': 'L) Trol Yasağı İhlalleri',
    'm': 'M) Yasak Ürün Ticareti ve İzinsiz İthalat/İhracat',
    'n': 'N) Bilgi/Belge ve Hedef Dışı Av Bildirim İhlalleri',
    'o': 'O) Bilimsel/Teknik Çalışma İzni İhlali',
    'p': 'P) BAGİS İhlalleri',
    'r': 'R) Karaya Çıkış ve Nakil Belgesi İhlalleri',
    's': 'S) İzinsiz Balıklandırma',
    't': 'T) Uluslararası Sularda İzinsiz Avcılık',
    '-': 'Diğer Excel Kayıtları',
}


def tr_money(value):
    return f'{int(value):,}'.replace(',', '.') + ' TL'


def build_penalties():
    cards = read_json('penalty_cards.json')
    for card in cards:
        if card.get('art36') == '1':
            card['art36'] = 'l'
        if card.get('art36') == 'l':
            note = 'Exceldeki “1” değeri yeni 08 rehberine göre Kanun m.36/l olarak düzeltilmiştir.'
            if note not in (card.get('notes') or ''):
                card['notes'] = ((card.get('notes') or '') + ' ' + note).strip()
        if card.get('id') == 82:
            card['art36'] = 'o'
            note = 'Yeni 08 rehberi bu ihlalin Kanun m.36/o kapsamında olduğunu belirtir.'
            if note not in (card.get('notes') or ''):
                card['notes'] = ((card.get('notes') or '') + ' ' + note).strip()
        card['source_doc'] = '08 GÜNCEL İDARİ CEZA UYGULAMA TABLOSU (EXCEL - DOĞRULANMIŞ).md'

    grouped = {key: [] for key in PENALTY_TITLES}
    for card in cards:
        key = card.get('art36') or '-'
        grouped.setdefault(key, []).append(card)

    result = []
    for key, title in PENALTY_TITLES.items():
        entries = []
        for index, card in enumerate(grouped.get(key, [])):
            details = {'İhlal': card.get('violation') or card.get('option') or 'Belirtilmemiş'}
            if card.get('option'):
                details['Durum/Seçenek'] = card['option']
            refs = []
            if card.get('law'):
                refs.append('K.' + str(card['law']))
            if card.get('regulation'):
                refs.append('Y.' + str(card['regulation']).replace('\n', ' / '))
            if card.get('teblig'):
                refs.append('T.' + str(card['teblig']))
            refs.append('36/' + key)
            details['Dayanak'] = ' · '.join(refs)
            amounts = card.get('amounts') or {}
            if amounts:
                details['İPC'] = '; '.join(f'{label}: {tr_money(amount)}' for label, amount in amounts.items())
            elif card.get('base_ipc') is not None:
                details['İPC'] = tr_money(card['base_ipc'])
            if card.get('product_seizure') or card.get('means_seizure'):
                details['El Koyma'] = f"Ürün: {card.get('product_seizure') or '-'}; vasıta: {card.get('means_seizure') or '-'}"
            if card.get('repeat'):
                details['Tekrar'] = card['repeat']
            if card.get('license_action'):
                details['Ruhsat İşlemi'] = card['license_action']
            if card.get('notes'):
                details['Uyarı/Not'] = card['notes'].strip()
            details['Kaynak'] = card['source_doc']
            entries.append(item(card.get('option') or card['violation'], details, f'{key}_{index}'))
        if entries:
            result.append({'id': key, 'title': title, 'items': entries, 'sub': [], 'content': '',
                           'source_doc': cards[0]['source_doc']})
    return cards, result


NEW_FIELD_RULES = [
    {'id':'dalyan_lagoon','cat':'İçsu/Dalyan','title':'Dalyan ve lagün kontrolü','summary':'Ağızların ilan edilen zamanda açık tutulması, %10 damızlık geçişi, 3 cm çit aralığı, 1 mil/500 m koruma alanı ile ışık ve zıpkın yasağı birlikte kontrol edilir.','refs':[{'s':'61','a':34}]},
    {'id':'inland_closed','cat':'İçsu/Dalyan','title':'Tamamen yasak içsular','summary':'Avlanılan göl, baraj gölü veya diğer kaynağın 6/1 Tebliğ Madde 35 listesindeki tamamen yasak sulardan olup olmadığı il bazında kontrol edilir.','refs':[{'s':'61','a':35}]},
    {'id':'inland_partial','cat':'İçsu/Dalyan','title':'Kısmen yasak içsular','summary':'Kaynağa özgü alan, tür, av aracı ve dönem sınırlamaları 6/1 Tebliğ Madde 36 kapsamında ayrıca kontrol edilir.','refs':[{'s':'61','a':36}]},
    {'id':'inland_season','cat':'İçsu/Dalyan','title':'İçsu bölgesel zaman yasağı','summary':'Sazangiller ve diğer içsu türlerinin bölgesel zaman yasakları il, tür ve faaliyet türüne göre kontrol edilir.','refs':[{'s':'61','a':37},{'s':'62','a':11}]},
    {'id':'inland_gear','cat':'İçsu/Dalyan','title':'İçsu av aracı kısıtları','summary':'Ticari ve amatör içsu avcılığında kullanılabilecek ağ, olta ve diğer araçlar ile tamamen yasak yöntemler ayrı ayrı kontrol edilir.','refs':[{'s':'61','a':51},{'s':'62','a':12}]},
    {'id':'health_quarantine','cat':'Tesis/Sağlık','title':'Karantina ve hastalık bildirimi','summary':'Hastalık şüphesinde bildirim, karantina, ürün hareketi ve Bakanlık tedbirlerine uyum kontrol edilir.','refs':[{'s':'reg','a':21}]},
    {'id':'health_import','cat':'Tesis/Sağlık','title':'Sağlık yönünden ithalat/ihracat','summary':'İthal ve ihraç edilen su ürünlerinin sağlık belgesi, kontrol ve uygunluk şartları incelenir.','refs':[{'s':'reg','a':22}]},
    {'id':'facility_permit','cat':'Tesis/Sağlık','title':'İşleme tesisi çalışma izni','summary':'İşleme ve değerlendirme tesisinin çalışma izni ile asgari genel sağlık şartları kontrol edilir.','refs':[{'s':'reg','a':25},{'s':'reg','a':26}]},
    {'id':'processing_rules','cat':'Tesis/Sağlık','title':'İşleme, ambalajlama ve nakliye','summary':'Taze, dondurulmuş ve işlenmiş ürün şartları ile ambalajlama, etiketleme, muhafaza ve nakliye hükümleri kontrol edilir.','refs':[{'s':'reg','a':27},{'s':'reg','a':28},{'s':'reg','a':29},{'s':'reg','a':30},{'s':'reg','a':31},{'s':'reg','a':32}]},
    {'id':'facility_control','cat':'Tesis/Sağlık','title':'Tesis ve ürünlerde genel kontrol yetkisi','summary':'İşyeri, balıkhane, mezat yeri, işleme tesisi, ürün, istihsal yeri ve vasıtalar üzerindeki kontrol ve el koyma yetkisi birlikte değerlendirilir.','refs':[{'s':'reg','a':33}]},
]


NEW_GUIDES = [
    {'key':'20_Serpme_Ag','short_title':'Serpme Ağ','title':'SERPME AĞ — SAHA KONTROL FÖYÜ','subtitle':'Ticari/amatör kullanım ve teknik ölçü kontrolü','rows':[
        {'no':1,'text':'Faaliyet ticariyse serpme ağ, yalnız motorsuz gemide veya 12 metreden küçük motorlu gemide mi bulunduruluyor?','ref':['reg',13],'penalty_query':'av aracı'},
        {'no':2,'text':'Amatör deniz avcılığında ağ kapalıyken yerden yüksekliği en fazla 3 metre mi?','ref':['62',16],'penalty_query':'amatör av aracı'},
        {'no':3,'text':'Amatör deniz avcılığında ağ gözü açıklığı 28 mm veya daha büyük mü?','ref':['62',16],'penalty_query':'amatör av aracı'},
        {'no':4,'text':'Ticari av aracı Bakanlık usulüne göre markalı ve SUBİS kayıtlı mı?','ref':['61',49],'penalty_query':'markasız av aracı'}],
     'measure_fields':['Kapalı ağ yüksekliği (m)','Ağ gözü açıklığı (mm)'],'refs':[['reg',13],['62',16],['61',49]],'source_docs':['01 TEKNE VE AV ARACI TÜRÜNE GÖRE KURALLAR.md','05 AMATÖR BALIKÇILIK KURALLARI.md']},
    {'key':'21_Sepet_Pinter_Tuzak','short_title':'Sepet/Pinter','title':'SEPET, PİNTER VE TUZAK — SAHA KONTROL FÖYÜ','subtitle':'Tür, faaliyet ve su alanına göre kullanım kontrolü','rows':[
        {'no':1,'text':'Lagos avcılığında sepet, pinter veya benzeri tuzak kullanılmıyor mu?','ref':['61',26],'penalty_query':'lagos av aracı'},
        {'no':2,'text':'Amatör içsu avcılığında pinter, sepet, düzen veya çökertme kullanılmıyor mu?','ref':['62',12],'penalty_query':'amatör av aracı'},
        {'no':3,'text':'Amatör deniz avcılığında pinter veya sepet kullanılmıyor mu?','ref':['62',16],'penalty_query':'amatör av aracı'}],
     'measure_fields':[],'refs':[['61',26],['62',12],['62',16]],'source_docs':['01 TEKNE VE AV ARACI TÜRÜNE GÖRE KURALLAR.md','05 AMATÖR BALIKÇILIK KURALLARI.md']},
    {'key':'22_Dalyan_Lagun','short_title':'Dalyan/Lagün','title':'DALYAN VE LAGÜN — SAHA KONTROL FÖYÜ','subtitle':'Ağız, geçiş, koruma alanı ve av yöntemi kontrolü','rows':[
        {'no':1,'text':'Lagün/dalyan ağzı il müdürlüğünün ilan ettiği zamanda açık tutuluyor ve bu sırada lagün içinde avcılık yapılmıyor mu?','ref':['61',34],'penalty_query':'dalyan lagün'},
        {'no':2,'text':'Üreme döneminde gelen türlerin %10’u görevli nezaretinde denize salınıyor mu?','ref':['61',34],'penalty_query':'dalyan lagün'},
        {'no':3,'text':'Dalyan kuzuluğu çit aralıkları dikey ve en az 3 cm mi?','ref':['61',34],'penalty_query':'dalyan lagün'},
        {'no':4,'text':'Ağız açıkken 1 mil, kapalıyken 500 metre yarıçaptaki avcılık yasağına uyuluyor mu?','ref':['61',34],'penalty_query':'yasak saha'},
        {'no':5,'text':'Lagünde ışık veya zıpkın kullanılmıyor ve yeni/izinsiz ağ dalyanı ya da çökertme ağı kurulmuyor mu?','ref':['61',34],'penalty_query':'yasak av aracı'}],
     'measure_fields':['Çit aralığı (cm)','Ağızdan mesafe (m/mil)','Salınan damızlık oranı (%)'],'refs':[['61',34]],'source_docs':['04 İÇSULAR, DALYAN VE LAGÜNLER.md']},
]


def build_outputs():
    commercial, amateur, inland_tables = build_species()
    commercial_forbidden, amateur_forbidden = prohibited_names()
    prohibited = [{'name': name, 'commercial': True, 'amateur': name in amateur_forbidden,
                   'source': '61', 'article': 16, 'source_doc': GUIDE_03.name}
                  for name in commercial_forbidden]
    for name in amateur_forbidden:
        if name not in commercial_forbidden:
            prohibited.append({'name': name, 'commercial': False, 'amateur': True,
                               'source': '62', 'article': 6, 'source_doc': GUIDE_03.name})

    cards, penalty_guide = build_penalties()
    rules = read_json('field_rules.json')
    rules = [rule for rule in rules if rule['id'] not in {x['id'] for x in NEW_FIELD_RULES}]
    for rule in rules:
        rule['source_docs'] = ['00 İÇİNDEKİLER VE GENEL ESASLAR.md', '01 TEKNE VE AV ARACI TÜRÜNE GÖRE KURALLAR.md', '02 BÖLGEYE GÖRE KURALLAR (DENİZLER).md', '03 TÜRLERE GÖRE AV YASAKLARI, BOY-AĞIRLIK VE KOTALAR.md', '05 AMATÖR BALIKÇILIK KURALLARI.md', '06 RUHSAT, İZİN BELGELERİ, GEMİ İZLEME SİSTEMİ VE İDARİ CEZALAR.md']
    rules.extend(copy.deepcopy(NEW_FIELD_RULES))

    guides = read_json('vessel_guides.json')
    guides = [guide for guide in guides if guide['key'] not in {x['key'] for x in NEW_GUIDES}]
    for guide in guides:
        guide['source_docs'] = ['01 TEKNE VE AV ARACI TÜRÜNE GÖRE KURALLAR.md', '02 BÖLGEYE GÖRE KURALLAR (DENİZLER).md', '03 TÜRLERE GÖRE AV YASAKLARI, BOY-AĞIRLIK VE KOTALAR.md', '05 AMATÖR BALIKÇILIK KURALLARI.md', '06 RUHSAT, İZİN BELGELERİ, GEMİ İZLEME SİSTEMİ VE İDARİ CEZALAR.md']
    guides.extend(copy.deepcopy(NEW_GUIDES))

    outputs = {
        'commercial_species.json': commercial,
        'amateur_species.json': amateur,
        'prohibited_species.json': prohibited,
        'tur_cizelgesi.json': build_species_guide(commercial, amateur, inland_tables),
        'penalty_cards.json': cards,
        'ceza_rehberi_v2.json': penalty_guide,
        'field_rules.json': rules,
        'vessel_guides.json': guides,
    }
    articles = read_json('articles.json')
    valid_articles = {(row['source'], row['article']) for row in articles}
    refs = [(ref['s'], ref['a']) for rule in rules for ref in rule.get('refs', [])]
    refs += [(ref[0], ref[1]) for guide in guides for ref in guide.get('refs', [])]
    missing_refs = sorted(set(refs) - valid_articles)
    if missing_refs:
        raise ValueError(f'Yapılandırılmış veride karşılığı olmayan madde bağlantısı: {missing_refs}')
    represented_cards = sum(len(group['items']) for group in penalty_guide)
    if represented_cards != len(cards):
        raise ValueError(f'Ceza rehberinde {len(cards) - represented_cards} kart eksik')
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build_outputs()
    changed = []
    for name, value in outputs.items():
        rendered = dump(value)
        path = DATA / name
        if not path.exists() or path.read_bytes() != rendered:
            changed.append(name)
            if not args.check:
                path.write_bytes(rendered)
    if args.check and changed:
        raise SystemExit('Güncel olmayan yapılandırılmış veri: ' + ', '.join(changed))
    print(('doğrulandı' if args.check else 'üretildi') + ': ' + ', '.join(outputs))


if __name__ == '__main__':
    main()
