"""Su Ürünleri Kolluk Asistanı — ekranlar ve akışlar.

Eski Telegram botunun bütün ekranları buradadır; düğme verileri (callback) ve
metin modları aynen korunur. Telegram yerine web.py her istekte bir Screen
oluşturur, ilgili fonksiyonu çağırır ve ortaya çıkan ekranı tarayıcıya yollar.
"""

import html
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import accounts
import db

logger = logging.getLogger(__name__)

ASSET_DIR = Path('/app/data') if os.path.exists('/app/data') else Path(__file__).parent / 'data'
with open(ASSET_DIR / 'ceza_rehberi_v2.json', 'r', encoding='utf-8') as f:
    CEZA_REHBERI = json.load(f)

with open(ASSET_DIR / 'tur_cizelgesi.json', 'r', encoding='utf-8') as f:
    TUR_CIZELGESI = json.load(f)


class ParseMode:
    HTML = 'HTML'



# Yönetici panelinde gösterilen kişi adları; web.py hesabın görünen adıyla doldurur.
USER_NAMES = {}


class _AdminIds:
    """`uid in ADMIN_IDS` denetimini sitedeki yönetici hesaplarına bağlar."""

    def __contains__(self, uid):
        return accounts.is_admin_uid(uid)


ADMIN_IDS = _AdminIds()

options = {}
if os.path.exists('/data/options.json'):
    try:
        with open('/data/options.json', 'r') as f:
            options = json.load(f)
    except Exception:
        pass
elif os.path.exists('options.json'):
    try:
        with open('options.json', 'r') as f:
            options = json.load(f)
    except Exception:
        pass

TZ = ZoneInfo(os.environ.get('TZ') or 'Europe/Istanbul')
try:
    LIMIT = int(os.environ.get('RESULT_LIMIT') or options.get('result_limit', 8))
except ValueError:
    LIMIT = 8
GEMINI_API_KEY = (os.environ.get('GEMINI_API_KEY') or options.get('gemini_api_key') or '').strip()
GEMINI_MODEL = (os.environ.get('GEMINI_MODEL') or options.get('gemini_model') or 'gemini-3.5-flash-lite').strip()
# Home Assistant keeps existing option values across addon updates. Migrate the
# previous project default automatically so an installed 5.9.2 instance does
# not continue using Gemini 3.6 Flash after this update.
if GEMINI_MODEL == 'gemini-3.6-flash':
    GEMINI_MODEL = 'gemini-3.5-flash-lite'

SRC_LABEL = {
    'law': '1380 Kanun',
    'reg': 'Yönetmelik',
    '61': '6/1 Ticari Tebliğ',
    '62': '6/2 Amatör Tebliğ',
    'bagis': 'BAGİS Tebliği',
    'excel': 'Ceza Excel',
}


REGION_LABEL = {
    'karadeniz': 'Karadeniz',
    'marmara': 'Marmara Denizi',
    'istanbul': 'İstanbul Boğazı',
    'canakkale': 'Çanakkale Boğazı',
    'ege': 'Ege Denizi',
    'akdeniz': 'Akdeniz',
    'international': 'Uluslararası / MEB',
    'inland': 'İçsu (göl, baraj, akarsu)',
    'lagoon': 'Dalyan / Lagün',
    'facility': 'Tesis / Sağlık Denetimi',
}

ACTIVITY_SCOPE_LABEL = {
    'commercial': 'Ticari avcılık',
    'amateur': 'Amatör avcılık',
    'processing': 'İşleme / değerlendirme tesisi',
    'aquaculture': 'Yetiştiricilik / sağlık',
}

LENGTH_BANDS = {
    'none': ('Gemi/Tekne yok', 0.0),
    'lt12': ('12 metreden küçük', 11.0),
    '12to22': ('12 m – 22 m altı', 17.0),
    'ge22': ('22 m ve üzeri', 22.0),
}

SUBJECT_LABEL = {
    'fishing': 'Avcılık faaliyeti',
    'vessel': 'Gemi / ruhsat / donanım',
    'species': 'Ürün / tür kontrolü',
    'transport': 'Nakil / satış kontrolü',
    'facility': 'Tesis izin ve şartları',
    'health': 'Ürün sağlığı ve kalite',
    'environment': 'Atık / çevresel tedbir',
}

GUIDE_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'vessel_guides.json')
with open(GUIDE_DATA_PATH, 'r', encoding='utf-8') as _guide_file:
    GUIDE_LIST = json.load(_guide_file)
GUIDES = {g['key']: g for g in GUIDE_LIST}

GUIDE_GEAR_MAP = {
    'gırgır': ['01_Girgir'],
    'dip trolü': ['02_Dip_Trolu'],
    'ortasu trolü': ['03_Ortasu_Trolu'],
    'uzatma ağı': ['04_Uzatma_Agi'],
    'parakete': ['05_Parakete'],
    'algarna': ['06_Algarna_Karides', '08_Algarna_Deniz_Salyangozu', '09_Drec_Beyaz_Kum_Midyesi'],
    'manyat': ['07_Manyat_Karides'],
    'dreç': ['09_Drec_Beyaz_Kum_Midyesi'],
    'ışık': ['11_Isik_Teknesi'],
    'dalma': ['10_Dalma_Yontemi', '16_Deniz_Patlicani', '17_Denizkestanesi', '18_Sunger'],
    'deniz patlıcanı': ['16_Deniz_Patlicani'],
    'denizkestanesi': ['17_Denizkestanesi', '18_Sunger'],
    'monofilament': ['15_Monofilament'],
    'turizm': ['19_Amator_Turizm'],
    'serpme': ['20_Serpme_Ag'],
    'sepet / pinter': ['21_Sepet_Pinter_Tuzak'],
    'dalyan / lagün': ['22_Dalyan_Lagun'],
}


def audit_activity_label(context):
    value = context.user_data.get('audit_activity')
    return ACTIVITY_SCOPE_LABEL.get(value, value or 'Belirtilmedi')


def audit_species_scope(context):
    return 'inland' if context.user_data.get('audit_region') == 'inland' else 'sea'


def audit_length_label(context):
    exact = context.user_data.get('audit_length_exact')
    if exact is not None:
        return f'{exact:g} m'
    band = context.user_data.get('audit_length_band')
    if band in LENGTH_BANDS:
        return LENGTH_BANDS[band][0]
    length = context.user_data.get('audit_length')
    return f'{length:g} m' if length is not None else 'Belirtilmedi'


def audit_rule_length(context):
    exact = context.user_data.get('audit_length_exact')
    if exact is not None:
        return float(exact)
    band = context.user_data.get('audit_length_band')
    if band in LENGTH_BANDS:
        return float(LENGTH_BANDS[band][1])
    return float(context.user_data.get('audit_length') or 0)


def audit_date(context):
    value = context.user_data.get('audit_date')
    if hasattr(value, 'year'):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            pass
    return datetime.now(TZ).date()


def esc(value):
    return html.escape(str(value if value is not None else '—'))


def money(value):
    if value is None:
        return '—'
    return f'{float(value):,.0f} TL'.replace(',', '.')


def kb(rows):
    return [[{'text': title, 'data': data} for title, data in row] for row in rows]


# ── Shared visual language ────────────────────────────────────────────────
# Telegram gives us HTML and Unicode only, so hierarchy has to come from a
# small, consistently applied set of building blocks rather than styling.

HR = '━━━━━━━━━━━━━━━━━━━━'


def progress_bar(current, total, width=10):
    """Render '▰▰▰▱▱▱▱▱▱▱ 3/12' for a step in a multi-step flow."""
    total = max(int(total), 1)
    current = min(max(int(current), 0), total)
    filled = round(width * current / total)
    return f'{"▰" * filled}{"▱" * (width - filled)}  {current}/{total}'


def trend_bar(value, scale, width=12):
    """Render '▰▰▰▱▱▱▱▱▱▱▱▱ 3' — a fixed-width block bar sized against the
    largest value in a series, followed by the raw count. Used for the admin
    panel's day-by-day trend table; wrap the result in <code> so the blocks
    line up across rows (monospace)."""
    scale = max(int(scale), 1)
    filled = round(width * min(int(value), scale) / scale)
    return f'{"▰" * filled}{"▱" * (width - filled)} {int(value)}'


def header(icon, title, subtitle=None):
    """A consistent title block: icon + bold caps title, optional subtitle."""
    out = f'{icon} <b>{esc(title)}</b>'
    if subtitle:
        out += f'\n<i>{esc(subtitle)}</i>'
    return out


def field(label, value, icon=''):
    """One aligned 'label … value' row for a detail card."""
    prefix = f'{icon} ' if icon else ''
    return f'{prefix}{esc(label)}: <b>{esc(value)}</b>'


def badge(state, title, detail=''):
    """A prominent status line: state is 'ok', 'warn' or 'stop'."""
    icon = {'ok': '🟢', 'warn': '🟡', 'stop': '🔴'}.get(state, 'ℹ️')
    out = f'{icon} <b>{esc(title)}</b>'
    if detail:
        out += f'\n{detail}'
    return out


def items_table(items):
    """Ceza/tür çizelgesi öğelerini süzülebilir bir HTML tabloya çevirir.
    Sütunlar bütün öğelerin detay anahtarlarının birleşimidir: ceza
    kartlarının bir kısmında olan "Tekrar", "Ruhsat İşlemi" gibi alanlar ilk
    satırda yok diye gizlenmez. Yeni anahtar, o öğede kendisinden önce gelen
    anahtarın hemen arkasına yerleşir. app.js tabloyu bulup büyükse üstüne
    bir metin filtresi ekler (bkz. attachTableFilters)."""
    if not items:
        return ''
    columns = []
    for it in items:
        position = -1
        for key in it.get('details', {}):
            if key in columns:
                position = columns.index(key)
            else:
                position += 1
                columns.insert(position, key)
    head = ''.join(f'<th>{esc(c)}</th>' for c in columns)
    body = []
    for it in items:
        details = it.get('details', {})
        cells = ''.join(f'<td>{esc(details.get(c, "")).replace("*", "")}</td>' for c in columns)
        body.append(f'<tr>{cells}</tr>')
    return f'<table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def tally(answers):
    """Running counts for a checklist: '✅ 3 · ❌ 1 · ⚪ 2 · ⋯ 6'."""
    ok = sum(1 for a in answers if a == 'ok')
    bad = sum(1 for a in answers if a == 'bad')
    skip = sum(1 for a in answers if a == 'skip')
    left = sum(1 for a in answers if a is None)
    return f'✅ {ok}  ·  ❌ {bad}  ·  ⚪ {skip}  ·  ⋯ {left}'





class AIError(Exception):
    """A Gemini call failed in a way the user should see a plain message for."""


AI_SYSTEM_INSTRUCTION = (
    "[GÖREV VE ROL]\n"
    "Sen bir su ürünleri denetim personelisin. Temel görevin; kullanıcı tarafından yüklenen veya "
    "sisteme eklenen belgelere dayalı olarak resmi, doğru ve kesin bilgileri aktarmaktır.\n\n"
    "[ÜSLUP VE TON]\n"
    "- Resmi ve Kesin: Ciddi, askeri/kurumsal disipline uygun, açık ve net bir dil kullan.\n"
    "- Tarafsız ve Otoriter: Gereksiz yorumlardan, kişisel görüşlerden, duygusal ifadelerden "
    "ve samimi hitaplardan kesinlikle kaçın.\n"
    "- Doğrudan: Cümleleri uzatmadan, net bilgi ver.\n\n"
    "[KURALLAR VE KISITLAMALAR]\n"
    "- Ekli Belgelere Kesin Bağlılık: Yalnızca aşağıda verilen Markdown belgelerindeki "
    "verilere sadık kal. Genel bilgini veya belge dışı başka bir kaynağı kullanma.\n"
    "- Kaynak Önceliği: Kanun, Yönetmelik ve Tebliğlerin tam metinleri hukuki hüküm için "
    "birincil kaynaktır. 00-07 numaralı konu rehberlerini olayın ilgili hükümlerini bulmak "
    "ve uygulama bağlamını görmek için; 08 numaralı doğrulanmış tabloyu güncel idari ceza "
    "tutarları ve uygulama notları için kullan. Belgeler arasında açık bir uyuşmazlık veya "
    "doğrulanamamış not varsa bunu kesin hüküm gibi sunma; belgedeki uyarıyı aynen koru.\n"
    "- Varsayım ve Uydurma Yasağı: Belgelerde yer almayan hiçbir bilgiyi türetme, tahmin "
    "etme veya uydurma. Madde numarası, tarih, tutar, yaptırım ve hüküm ekleme.\n"
    "- Eksik Bilgi Durumu: İstenen bilgi ekli belgelerde yer almıyorsa yalnızca şu ifadeyi "
    "kullan: \"Verilen belgelerde bu hususla ilgili bir bilgi bulunmamaktadır.\"\n\n"
    "[ÇIKTI FORMATI]\n"
    "- Bütün yanıtları anlaşılır başlıklar ve madde işaretleri kullanarak yapılandır.\n"
    "- Karmaşık paragraf blokları yerine liste formatını tercih et.\n"
    "- Başlıkları **kalın**, maddeleri '- ' işaretiyle yaz. HTML kullanma.\n\n"
    "[ZORUNLU CEVAP ŞABLONU VE SIRALAMA]\n"
    "- Her cevapta aşağıdaki ana başlıkları aynen ve daima aynı sırayla kullan. "
    "Olayda en açık karşılık Tebliğde bulunsa dahi sıralamayı değiştirme:\n\n"
    "**OLAYIN HUKUKİ TESPİTİ VE MEVZUAT KARŞILIKLARI**\n"
    "- Olayın belgelerden doğrudan çıkan kısa ve kesin hukuki tespitini yaz.\n\n"
    "**1. KANUN KARŞILIĞI VE İDARİ YAPTIRIMLAR**\n"
    "**(1380 Sayılı Su Ürünleri Kanunu)**\n"
    "**İhlal Edilen Kanun Maddeleri**\n"
    "- **Madde [numara]:** Belgedeki hükmü ve somut olayla doğrudan ilişkisini yaz.\n"
    "**Uygulanacak İdari/Cezai Yaptırımlar**\n"
    "- Belgede olay için açıkça yer alan para cezası, el koyma, mülkiyetin kamuya geçirilmesi, "
    "ruhsat işlemi ve tekrar hükümlerini yaz.\n"
    "**Görev ve Yetki**\n"
    "- Belgede olay bakımından açıkça yer alan görev ve yetki hükümlerini yaz.\n\n"
    "**2. YÖNETMELİK KARŞILIĞI**\n"
    "**(Su Ürünleri Yönetmeliği)**\n"
    "**[Hükmün Konusu]**\n"
    "- **Madde [numara]:** Belgedeki hükmü ve somut olayla doğrudan ilişkisini yaz.\n\n"
    "**3. TEBLİĞ KARŞILIĞI**\n"
    "**([İlgili Tebliğin Tam Adı ve Numarası])**\n"
    "**[Hükmün Konusu]**\n"
    "- **Madde [numara/fıkra]:** Belgedeki hükmü ve somut olayla doğrudan ilişkisini yaz.\n\n"
    "- Üç ana mevzuat başlığını her cevapta mutlaka göster. Kanun, Yönetmelik veya Tebliğ "
    "bölümlerinden birinde somut olaya doğrudan karşılık gelen hüküm yoksa o bölümün ana "
    "başlığını koru; altını tamamen boş bırak. Kaynak adı, alt başlık, madde, 'hüküm yoktur', "
    "'uygulanmaz' veya benzeri "
    "bir açıklama yazma. Yakın ya da dolaylı bir hükümle boşluğu doldurma.\n"
    "- Bir bölümde yalnızca belgelerde somut olayla doğrudan ilişkili olan maddeleri göster. "
    "Her maddeyi kendi mevzuat bölümüne yerleştir.\n"
    "- Birden fazla ilgili Tebliğ varsa her birinin tam adını ayrı bir kalın alt başlık altında "
    "yaz; ancak tamamını üçüncü ana bölüm içinde tut.\n"
    "- Madde numarasını önce, hükmü sonra yaz. Hükmün somut olaya etkisini kısa bir cümleyle "
    "belirt. Belgede bulunmayan bir yaptırım sonucu veya hukuki nitelendirme ekleme."
)


_AI_CORPUS_CACHE = None
AI_MARKDOWN_DIR = ASSET_DIR / 'markdown'


def ai_full_corpus():
    """Load the complete canonical corpus from the packaged Markdown mirror."""
    global _AI_CORPUS_CACHE
    if _AI_CORPUS_CACHE is not None:
        return _AI_CORPUS_CACHE

    markdown_files = sorted(AI_MARKDOWN_DIR.glob('*.md'), key=lambda path: path.name.casefold())
    if not markdown_files:
        logger.error('Hukuki değerlendirme için Markdown kaynağı bulunamadı: %s',
                     AI_MARKDOWN_DIR)
        raise AIError('Hukuki değerlendirme kaynakları bulunamadı.')

    parts = []
    for path in markdown_files:
        document = path.read_text(encoding='utf-8').strip()
        if document:
            parts.append(f"=== BELGE: {path.name} ===\n{document}")

    if not parts:
        logger.error('Hukuki değerlendirme Markdown kaynakları boş: %s', AI_MARKDOWN_DIR)
        raise AIError('Hukuki değerlendirme kaynakları boş.')

    _AI_CORPUS_CACHE = '\n\n'.join(parts)
    logger.info('Hukuki değerlendirme için %s Markdown belgesi yüklendi.', len(parts))
    return _AI_CORPUS_CACHE


def ai_prompt_prefix():
    """The document context shared by every question and stored in Gemini's cache."""
    return '=== EKLİ MARKDOWN BELGELERİ ===\n' + ai_full_corpus()


def ai_prompt_tail(scenario):
    """The only part that changes between questions."""
    return '\n\n=== SORU / OLAY ===\n' + scenario.strip() + '\n\n=== CEVAP ==='


def ai_build_prompt(scenario):
    """The document context and question used when explicit caching is unavailable."""
    return ai_prompt_prefix() + ai_prompt_tail(scenario)


AI_NO_INFO_MESSAGE = 'Verilen belgelerde bu hususla ilgili bir bilgi bulunmamaktadır.'
AI_MAIN_HEADING = '**OLAYIN HUKUKİ TESPİTİ VE MEVZUAT KARŞILIKLARI**'
AI_SECTION_HEADINGS = {
    'law': '**1. KANUN KARŞILIĞI VE İDARİ YAPTIRIMLAR**',
    'regulation': '**2. YÖNETMELİK KARŞILIĞI**',
    'communique': '**3. TEBLİĞ KARŞILIĞI**',
}
_AI_TURKISH_HEADING_CHARS = str.maketrans('ÇĞİÖŞÜ', 'CGIOSU')


def _ai_heading_fold(text):
    return text.upper().translate(_AI_TURKISH_HEADING_CHARS)


def _ai_section_key(line):
    """Recognize a model-produced main legal section despite minor Markdown variation."""
    plain = re.sub(r'[*_#`]', '', line).strip()
    plain = re.sub(r'^\d+\s*[.)-]\s*', '', plain)
    folded = _ai_heading_fold(plain)
    if folded.startswith('KANUN KARSILIGI'):
        return 'law'
    if folded.startswith('YONETMELIK KARSILIGI'):
        return 'regulation'
    if folded.startswith('TEBLIG KARSILIGI'):
        return 'communique'
    return None


def enforce_ai_section_order(text):
    """Keep Kanun → Yönetmelik → Tebliğ order even if the model drifts."""
    stripped = text.strip()
    if stripped == AI_NO_INFO_MESSAGE:
        return stripped

    intro = []
    sections = {key: [] for key in AI_SECTION_HEADINGS}
    current = None
    for line in stripped.splitlines():
        plain = re.sub(r'[*_#`]', '', line).strip()
        if _ai_heading_fold(plain) == 'OLAYIN HUKUKI TESPITI VE MEVZUAT KARSILIKLARI':
            continue
        key = _ai_section_key(line)
        if key:
            current = key
            continue
        if current:
            sections[current].append(line)
        else:
            intro.append(line)

    output = [AI_MAIN_HEADING]
    intro_text = '\n'.join(intro).strip()
    if intro_text:
        output.append(intro_text)
    for key, heading_text in AI_SECTION_HEADINGS.items():
        output.append(heading_text)
        section_text = '\n'.join(sections[key]).strip()
        if section_text:
            output.append(section_text)
    return '\n\n'.join(output)


def md_to_tg_html(text):
    """Convert the small Markdown subset requested from Gemini to safe Telegram HTML."""
    escaped = esc(text)
    escaped = re.sub(r'(?m)^#{1,6}\s+(.+?)\s*#*\s*$', r'**\1**', escaped)
    escaped = re.sub(r'(?m)^\s*[-*+]\s+', '• ', escaped)
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped, flags=re.S)


# ── Gemini bağlam önbelleği ─────────────────────────────────────────────
# The corpus prefix is ~75K tokens and never changes, so re-uploading it on
# every question is the biggest cost in this feature, both in latency and in
# billed input tokens. The cachedContents endpoint stores that prefix
# server-side and lets a request reference it by name.
#
# The cache is strictly an optimisation: if creating or using one fails for
# any reason (a model without cache support, quota, expiry, network), the
# call falls back to sending the full prompt inline, which is exactly what
# the feature did before caching existed. The text the model sees is
# identical either way, so the answer never depends on which path ran.
GEMINI_API_ROOT = 'https://generativelanguage.googleapis.com/v1beta'
AI_CACHE_TTL_SECONDS = 3600
# Stop reusing a cache slightly before it expires server-side, so a request
# never races the deletion.
AI_CACHE_SAFETY_MARGIN = 300

_ai_cache = {'name': None, 'model': None, 'expires': 0.0, 'unavailable': False}


class _AIRequestRejected(Exception):
    """The service refused the request itself (4xx). Carries the status code so
    the caller can tell a stale cache reference from a genuinely bad request."""

    def __init__(self, code, body):
        super().__init__(f'HTTP {code}')
        self.code = code
        self.body = body


def _gemini_post(path, body, timeout):
    url = f'{GEMINI_API_ROOT}/{path}?key={GEMINI_API_KEY}'
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _ai_ensure_cache():
    """Name of a live context cache holding the corpus, or None.

    Never raises: a failure here only means the caller sends the full prompt.
    """
    if _ai_cache['unavailable']:
        return None
    now = time.monotonic()
    if (_ai_cache['name'] and _ai_cache['model'] == GEMINI_MODEL
            and now < _ai_cache['expires']):
        return _ai_cache['name']
    body = {
        'model': f'models/{GEMINI_MODEL}',
        'displayName': 'su-urunleri-mevzuat',
        'ttl': f'{AI_CACHE_TTL_SECONDS}s',
        'systemInstruction': {'parts': [{'text': AI_SYSTEM_INSTRUCTION}]},
        'contents': [{'role': 'user', 'parts': [{'text': ai_prompt_prefix()}]}],
    }
    try:
        # Uploading the corpus is much slower than asking a question about it.
        data = _gemini_post('cachedContents', body, 180)
        name = data.get('name')
        if not name:
            raise ValueError(f'yanitta cache adi yok: {str(data)[:200]}')
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:300]
        logger.warning('Mevzuat önbelleği kurulamadı (HTTP %s): %s — tam istem gönderilecek.',
                       e.code, detail)
        _ai_cache['unavailable'] = True
        return None
    except Exception as e:
        logger.warning('Mevzuat önbelleği kurulamadı: %s — tam istem gönderilecek.', e)
        _ai_cache['unavailable'] = True
        return None
    tokens = (data.get('usageMetadata') or {}).get('totalTokenCount')
    logger.info('Mevzuat önbelleği kuruldu: %s (%s token, ttl %s sn)', name, tokens,
                AI_CACHE_TTL_SECONDS)
    _ai_cache.update(name=name, model=GEMINI_MODEL,
                     expires=now + AI_CACHE_TTL_SECONDS - AI_CACHE_SAFETY_MARGIN)
    return name


def _ai_generate(body):
    """One generateContent round trip. Returns the answer text."""
    try:
        # The uncached path carries the full corpus, so a slow response there
        # takes noticeably longer than a cached one.
        data = _gemini_post(f'models/{GEMINI_MODEL}:generateContent', body, 120)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8', 'replace')[:300]
        logger.error('Hukuki değerlendirme HTTP %s (model=%s): %s', e.code,
                     GEMINI_MODEL, body_text)
        if e.code == 429:
            raise AIError('Sorgu kotanız doldu, birkaç dakika sonra tekrar deneyin.') from e
        if 400 <= e.code < 500:
            raise _AIRequestRejected(e.code, body_text) from e
        raise AIError('Sorgu şu anda tamamlanamadı, birkaç dakika sonra tekrar deneyin.') from e
    except urllib.error.URLError as e:
        logger.error('Hukuki değerlendirme bağlantı hatası: %s', e.reason)
        raise AIError('Bağlantı kurulamadı, birkaç dakika sonra tekrar deneyin.') from e
    except TimeoutError:
        logger.error('Hukuki değerlendirme zaman aşımına uğradı (model=%s).', GEMINI_MODEL)
        raise AIError('Sorgu zaman aşımına uğradı, tekrar deneyin.')

    candidates = data.get('candidates') or []
    if not candidates:
        reason = (data.get('promptFeedback') or {}).get('blockReason')
        logger.error('Hukuki değerlendirme boş/engellenmiş yanıt: %s', reason)
        raise AIError('Bu soruya şu anda yanıt üretilemedi.')
    try:
        text = ''.join(p.get('text', '') for p in candidates[0]['content']['parts']).strip()
    except (KeyError, IndexError, TypeError) as e:
        logger.error('Hukuki değerlendirme beklenmeyen yanıt biçimi: %r', data)
        raise AIError('Beklenmeyen bir hata oluştu.') from e
    if not text:
        logger.error('Hukuki değerlendirme boş metin döndürdü.')
        raise AIError('Bu soruya şu anda yanıt üretilemedi.')
    return text


def _ai_call_gemini_sync(scenario):
    """Blocking HTTP call, run off the event loop via asyncio.to_thread.

    Talks to the plain REST endpoint with urllib instead of the
    google-generativeai SDK: that SDK pulls in grpcio/protobuf, which need a
    C toolchain and previously broke the Alpine addon build (see the
    requirements.txt history). A stdlib POST has no such dependency.
    """
    # User-facing messages are deliberately generic (no service or model
    # names) so the feature does not read as AI-powered from the chat; the
    # real cause always goes to the container log for whoever administers
    # the bot to diagnose.
    if not GEMINI_API_KEY:
        logger.error('Hukuki değerlendirme: GEMINI_API_KEY yapılandırılmamış.')
        raise AIError('Bu özellik şu anda yapılandırılmamış.')

    generation_config = {'temperature': 0.15, 'maxOutputTokens': 4096}
    cache_name = _ai_ensure_cache()
    if cache_name:
        try:
            return _ai_generate({
                'contents': [{'role': 'user', 'parts': [{'text': ai_prompt_tail(scenario)}]}],
                'cachedContent': cache_name,
                'generationConfig': generation_config,
            })
        except _AIRequestRejected as e:
            # Most likely the cache expired or was deleted server-side. Forget
            # it and answer from the full prompt rather than failing the user.
            logger.warning('Önbellekli istek reddedildi (HTTP %s), tam istemle tekrar deneniyor.',
                           e.code)
            _ai_cache.update(name=None, expires=0.0)

    try:
        return _ai_generate({
            'contents': [{'parts': [{'text': ai_build_prompt(scenario)}]}],
            'systemInstruction': {'parts': [{'text': AI_SYSTEM_INSTRUCTION}]},
            'generationConfig': generation_config,
        })
    except _AIRequestRejected as e:
        logger.error('Hukuki değerlendirme reddedildi (HTTP %s): %s', e.code, e.body)
        raise AIError('Bu özellik şu anda kullanılamıyor.') from e


def ai_analyze(scenario):
    """Run the question against the full legal corpus. Returns (raw, html)."""
    raw_text = _ai_call_gemini_sync(scenario)
    ordered_text = enforce_ai_section_order(raw_text)
    return ordered_text, md_to_tg_html(ordered_text)


# ── Per-user rate limit ─────────────────────────────────────────────────
# In-memory only: one request per user per AI_RATE_LIMIT_SECONDS. A dict
# resets on restart, which just means a fresh 2-minute allowance after an
# addon update — an acceptable trade for not needing a DB round trip on
# every question. Deliberately scoped to this feature; the bot's normal
# navigation has no such limit.
AI_RATE_LIMIT_SECONDS = 120
_ai_last_request = {}


def ai_rate_limit_remaining(uid):
    """Seconds left before this user may ask again; 0 or less means allowed."""
    last = _ai_last_request.get(uid)
    if last is None:
        return 0
    elapsed = time.monotonic() - last
    return max(0, int(AI_RATE_LIMIT_SECONDS - elapsed) + 1)


def ai_rate_limit_mark(uid):
    _ai_last_request[uid] = time.monotonic()


# ── Web ekran adaptörü ──────────────────────────────────────────────────
# Ekran fonksiyonları Telegram botundan taşındı ve aynı çağrı biçimini korur:
# q.edit_message_text(...) ekranı değiştirir, q.message.reply_text(...) ekrana
# yeni bir blok ekler, q.answer(..., show_alert=True) uyarı gösterir. web.py
# her istek için bir Screen oluşturur ve sonucu tarayıcıya JSON olarak yollar.


class Screen:
    def __init__(self):
        self.blocks = []
        self.buttons = []
        self.alert = None
        self.touched = False

    def replace(self, text, reply_markup=None):
        self.blocks = [str(text)]
        self.buttons = reply_markup or []
        self.touched = True

    def append(self, text, reply_markup=None):
        self.blocks.append(str(text))
        if reply_markup is not None:
            self.buttons = reply_markup
        self.touched = True


class WebContext:
    def __init__(self, user_data, screen):
        self.user_data = user_data
        self.screen = screen


class _WebMessage:
    def __init__(self, screen, uid):
        self._screen = screen
        self.chat_id = uid
        self.message_id = 0

    def reply_text(self, text, parse_mode=None, reply_markup=None, **_):
        self._screen.append(text, reply_markup)


class WebQuery:
    """Bir düğmeye basılması (eski callback query)."""

    def __init__(self, screen, uid, data):
        self.data = data
        self.from_user = SimpleNamespace(id=uid)
        self.message = _WebMessage(screen, uid)
        self._screen = screen

    def edit_message_text(self, text, parse_mode=None, reply_markup=None, **_):
        self._screen.replace(text, reply_markup)

    def answer(self, text=None, show_alert=False, **_):
        if text:
            self._screen.alert = str(text)


class WebUpdate:
    """Arama kutusuna yazılan metin (eski metin mesajı)."""

    def __init__(self, uid, text):
        self.effective_user = SimpleNamespace(id=uid)
        self.effective_message = SimpleNamespace(text=text)
        self.effective_chat = SimpleNamespace(id=uid)


def ai_show(context, chat_id, text, new=False, **kwargs):
    if new:
        context.screen.append(text, kwargs.get('reply_markup'))
    else:
        context.screen.replace(text, kwargs.get('reply_markup'))


def send_or_edit(update, context, text, force_new=False, **kwargs):
    context.screen.replace(text, kwargs.get('reply_markup'))


MAIN = [
    [('📋 Tekne Türü Kılavuzları', 'guide:menu'), ('🚨 Denetime Başla', 'audit:start')],
    [('📖 Pratik Ceza Rehberi', 'ceza:menu'), ('📖 Pratik Tür Çizelgesi', 'turcizelge:menu')],
    [('🚢 Gemi / Ruhsat / BAGİS', 'vessel:menu'), ('🧾 Kolluk İşlem Rehberi', 'field:Kolluk İşlemi')],
    [('🏞️ İçsu / Dalyan', 'field:İçsu/Dalyan'), ('🏭 Tesis / Sağlık', 'field:Tesis/Sağlık')],
    [('⚖️ Hukuki Değerlendirme', 'ai:start')],
]


def send_menu(target, user_id=None, edit=False, update=None, context=None, force_new=False):
    text = (
        '<b>Denetimde bilgi,\nkararlarınızda dayanak.</b>\n\n'
        'Deniz, içsu, dalyan/lagün ve tesislerde su ürünleri denetimi için kontrol föyleri, mevzuat ve tür rehberleri. '
        'Görevinize uygun aracı aşağıdan seçin.\n\n'
        'Üstteki arama alanında tür, ceza veya mevzuat arayın: '
        '<code>hamsi</code>  <code>ruhsatsız</code>  <code>BAGİS</code>'
    )
    rows = list(MAIN)
    if user_id:
        try:
            if db.open_draft(user_id):
                rows = [[('\u21a9\ufe0f Yar\u0131da Kalan Denetime Devam', 'insp:resume')],
                        [('\U0001f5d1 Yar\u0131da Kalan\u0131 Sil', 'insp:discard')]] + rows
        except Exception:
            pass
    if user_id in ADMIN_IDS:
        rows = rows + [[('🔐 Yönetici Paneli', 'admin:panel')]]
    if edit:
        target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    else:
        if update and context:
            send_or_edit(update, context, text, force_new=force_new, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
        else:
            target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def callback(q, context):
    data = q.data
    uid = q.from_user.id

    if data == 'menu':
        context.user_data.clear()
        return send_menu(q, uid, edit=True)


    if data == 'guide:menu':
        return guide_menu(q, context)
    if data == 'guide:fromgear':
        return guide_from_gear(q, context)
    if data.startswith('guide:open:'):
        return guide_open(q, context, data.split(':', 2)[2])
    if data.startswith('guide:view:'):
        _, _, key, page = data.split(':', 3)
        return guide_view(q, context, key, int(page))
    if data.startswith('guide:refs:'):
        return guide_refs(q, context, data.split(':', 2)[2])
    if data.startswith('guide:start:'):
        return guide_start(q, context, data.split(':', 2)[2])
    if data.startswith('guide:go:'):
        return guide_render(q, context, int(data.rsplit(':', 1)[1]))
    if data.startswith('guide:ans:'):
        _, _, idx, ans = data.split(':', 3)
        return guide_answer(q, context, int(idx), ans)
    if data == 'guide:finish' or data == 'guide:result':
        return guide_finish(q, context)
    if data == 'guide:badmenu':
        return guide_bad_menu(q, context)
    if data.startswith('guide:pen:'):
        return guide_penalty_search(q, context, int(data.rsplit(':', 1)[1]))
    if data == 'guide:measure:start':
        return guide_measure_start(q, context)
    if data == 'guide:measure:skip':
        return guide_measure_skip(q, context)



    if data == 'ceza:menu':
        rows = []
        for c in CEZA_REHBERI:
            rows.append([(f"{c['title']}", f"ceza:view:{c['id']}")])
        rows.append([('🔎 Kelimeyle Ceza Ara', 'mode:penalty')])
        rows.append([('🏠 Ana Menü', 'menu')])
        return q.edit_message_text('<b>📖 PRATİK CEZA REHBERİ</b>\n\nİncelemek istediğiniz başlığı seçin:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if data.startswith('ceza:view:'):
        cid = data.split(':', 2)[2]
        c_main = next((c for c in CEZA_REHBERI if c['id'] == cid), None)
        if c_main:
            nav = [[('🔙 Ceza Rehberi', 'ceza:menu')], [('🏠 Ana Menü', 'menu')]]
            parts = [f"<b>{esc(c_main['title'])}</b>"]
            if c_main.get('sub'):
                parts.append('Lütfen bir seçenek belirleyin:')
                if c_main.get('items'):
                    parts.append(items_table(c_main['items']))
                rows = [[(s['title'], f"ceza:sub:{c_main['id']}:{s['id']}")] for s in c_main['sub']]
                return q.edit_message_text('\n\n'.join(parts), parse_mode=ParseMode.HTML, reply_markup=kb(rows + nav))
            if c_main.get('items'):
                parts.append(items_table(c_main['items']))
            elif c_main.get('content'):
                parts.append(c_main['content'])
            return q.edit_message_text('\n\n'.join(parts), parse_mode=ParseMode.HTML, reply_markup=kb(nav))

    if data.startswith('ceza:sub:'):
        _, _, cid, sid = data.split(':')
        c_main = next((c for c in CEZA_REHBERI if c['id'] == cid), None)
        if c_main:
            s_sub = next((s for s in c_main['sub'] if s['id'] == sid), None)
            if s_sub:
                parts = [f"<b>{esc(s_sub['title'])}</b>"]
                if s_sub.get('items'):
                    parts.append(items_table(s_sub['items']))
                elif s_sub.get('content'):
                    parts.append(s_sub['content'])
                nav = [[('🔙 Üst Başlık', f"ceza:view:{cid}")], [('🏠 Ana Menü', 'menu')]]
                return q.edit_message_text('\n\n'.join(parts), parse_mode=ParseMode.HTML, reply_markup=kb(nav))

    if data == 'ai:audit':
        return ai_audit_preview(q, context)
    if data == 'ai:audit:run':
        return ai_audit_run(q, context)
    if data == 'ai:start':
        context.user_data['mode'] = 'ai_analysis'
        text_ai = (
            header('⚖️', 'HUKUKİ DEĞERLENDİRME', 'Ekli Markdown belgelerine göre') + '\n' + HR + '\n\n'
            'Olayı serbest metinle anlatın — ne yapıldığı, hangi av aracı, hangi belge/ruhsat durumu vb.\n\n'
            '<i>Örnek: Teknenin birincil av aracı algarna ama dip trolü ile avcılık yapıyor.</i>\n\n'
            f'🕑 <b>Bu özellik {AI_RATE_LIMIT_SECONDS // 60} dakikada bir kez kullanılabilir</b> — sorunuzu göndermeden önce net ve eksiksiz yazın.\n\n'
            '📄 Yanıt yalnızca sisteme eklenen Markdown belgelerindeki bilgilere dayanır.'
        )
        return q.edit_message_text(text_ai, parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Ana Menü', 'menu')]]))

    if data.startswith('mode:'):
        mode = data.split(':', 1)[1]
        context.user_data['mode'] = mode
        prompts = {
            'penalty': '⚖️ İhlali/olayı yazın. Örnek: <code>BAGİS arızası</code>, <code>kalkan parakete</code>, <code>ruhsatsız gemi</code>, <code>nakil belgesi</code>.',
            'gear': '🎣 Av aracını veya yöntemi yazın. Örnek: <code>gırgır</code>, <code>dip trolü</code>, <code>algarna</code>, <code>ışık</code>.',
            'place': '📍 Yer, il, koy, burun veya saha adını yazın. Koordinatla tarif edilen alanlarda sistem kaynak hükmünü gösterir; geometrik sınırdan emin olmadığı yerde kendiliğinden ihlal kararı vermez.',
            'lawsearch': '📚 Aranacak mevzuat kelimesini veya konuyu yazın. Örnek: <code>el koyma</code>, <code>ruhsat geri alma</code>, <code>gırgır</code>.',
        }
        return q.edit_message_text(prompts[mode], parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Ana Menü', 'menu')]]))

    if data.startswith('src:'):
        key = data.split(':', 1)[1]
        if key == 'excel':
            context.user_data['mode'] = 'penalty'
            return q.edit_message_text('📊 <b>Ceza Excel tablosunda ara</b>\n\nİhlal, madde veya anahtar kelime yazın.', parse_mode=ParseMode.HTML, reply_markup=kb([[('🏠 Ana Menü', 'menu')]]))
        context.user_data.update(mode='source_search', source=key)
        return q.edit_message_text(
            f'📚 <b>{esc(SRC_LABEL.get(key, key))}</b>\n\nMadde numarası yazabilir (örn. <code>36</code>) veya deniz, içsu, tesis ve sağlık konularında arama yapabilirsiniz.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📑 Maddeleri Listele', f'srclist:{key}:0')], [('🏠 Menü', 'menu')]]),
        )
    if data.startswith('srclist:'):
        _, source, page = data.split(':')
        return show_source_list(q, source, int(page))
    if data.startswith('artp:'):
        _, source, article, page = data.split(':')
        return show_article(q, source, int(article), int(page))
    if data.startswith('art:'):
        _, source, article = data.split(':')
        return show_article(q, source, int(article), 0)


    if data.startswith('rule:'):
        return show_rule(q, data.split(':', 1)[1])
    if data.startswith('field:'):
        return show_field(q, data.split(':', 1)[1])

    if data == 'vessel:menu':
        return q.edit_message_text(
            '🚤 <b>GEMİ / RUHSAT / BAGİS</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [('📄 Gemi & Ruhsat', 'field:Gemi/Ruhsat'), ('📡 BAGİS', 'field:BAGİS')],
                [('🎣 Av Aracı Kuralları', 'field:Av Aracı'), ('🚫 Yasak Araç Görsel Rehberi', 'gear:vis:menu')],
                [('↩️ Menü', 'menu')],
            ]),
        )

    if data == 'admin:panel' or data.startswith('admin:stats:'):
        section = data.split(':', 2)[2] if data.startswith('admin:stats:') else 'main'
        return show_admin_panel(q, section)
    if data == 'admin:issues':
        return show_admin_issues(q)
    issue_match = re.fullmatch(r'admin:issue:resolve:(\d+)', data)
    if issue_match:
        if q.from_user.id not in ADMIN_IDS:
            return q.answer('Yönetici yetkisi gerekli.', show_alert=True)
        report_id = int(issue_match.group(1))
        changed = db.resolve_issue_report(report_id, q.from_user.id)
        if changed:
            db.log_activity(q.from_user.id, 'issue_resolve', f'Bildirim #{report_id}')
        q.answer('Bildirim çözüldü olarak işaretlendi.' if changed else 'Bildirim zaten kapatılmış.')
        return show_admin_issues(q)

    if data == 'gear:vis:menu':
        return show_gear_visual_menu(q)
    if data.startswith('gear:vis:item:'):
        return show_gear_visual_item(q, data.split(':', 3)[3])

    if data == 'species:vis:menu':
        return show_species_visual_menu(q)
    if data.startswith('species:vis:item:'):
        return show_species_visual_item(q, data.split(':', 3)[3])


    if data == 'turcizelge:menu':
        rows = []
        for c in TUR_CIZELGESI:
            rows.append([(f"{c['title']}", f"turcizelge:view:{c['id']}")])
        rows.append([('🔎 Detaylı Tür Arama / Görsel Rehber', 'species:menu')])
        rows.append([('🏠 Ana Menü', 'menu')])
        return q.edit_message_text('<b>📖 PRATİK TÜR ÇİZELGESİ</b>\n\nİncelemek istediğiniz başlığı seçin:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if data.startswith('turcizelge:view:'):
        cid = data.split(':', 2)[2]
        c_main = next((c for c in TUR_CIZELGESI if c['id'] == cid), None)
        if c_main:
            nav = [[('🔙 Çizelge Menüsü', 'turcizelge:menu')], [('🏠 Ana Menü', 'menu')]]
            if c_main.get('sub'):
                rows = [[(s['title'], f"turcizelge:sub:{c_main['id']}:{s['id']}")] for s in c_main['sub']]
                return q.edit_message_text(f"<b>{esc(c_main['title'])}</b>\n\nLütfen bir seçenek belirleyin:", parse_mode=ParseMode.HTML, reply_markup=kb(rows + nav))
            parts = [f"<b>{esc(c_main['title'])}</b>"]
            if c_main.get('content'):
                parts.append(c_main['content'])
            if c_main.get('items'):
                parts.append(items_table(c_main['items']))
            return q.edit_message_text('\n\n'.join(parts), parse_mode=ParseMode.HTML, reply_markup=kb(nav))

    if data.startswith('turcizelge:sub:'):
        _, _, cid, sid = data.split(':')
        c_main = next((c for c in TUR_CIZELGESI if c['id'] == cid), None)
        if c_main:
            s_sub = next((s for s in c_main['sub'] if s['id'] == sid), None)
            if s_sub:
                parts = [f"<b>{esc(s_sub['title'])}</b>"]
                if s_sub.get('content'):
                    parts.append(s_sub['content'])
                if s_sub.get('items'):
                    parts.append(items_table(s_sub['items']))
                nav = [[('🔙 Üst Başlık', f"turcizelge:view:{cid}")], [('🏠 Ana Menü', 'menu')]]
                return q.edit_message_text('\n\n'.join(parts), parse_mode=ParseMode.HTML, reply_markup=kb(nav))

    if data == 'species:menu':
        return q.edit_message_text(
            '🐟 <b>TÜR / BOY / ZAMAN</b>\n\nFaaliyet ve su alanını seçin.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [('🌊 Ticari Deniz', 'species:kind:commercial:sea'), ('🌊 Amatör Deniz', 'species:kind:amateur:sea')],
                [('🏞️ Ticari İçsu', 'species:kind:commercial:inland'), ('🏞️ Amatör İçsu', 'species:kind:amateur:inland')],
                [('🚫 Ticari Yasak Tür', 'species:kind:prohibited:commercial'), ('🚫 Amatör Yasak Tür', 'species:kind:prohibited:amateur')],
                [('🔎 Görsel Balık Teşhis Rehberi', 'species:vis:menu')],
                [('🔙 Geri', 'turcizelge:menu')],
                [('🏠 Ana Menü', 'menu')],
            ]),
        )
    if data.startswith('species:kind:'):
        parts = data.split(':')
        kind = parts[2]
        qualifier = parts[3] if len(parts) > 3 else None
        values = {'mode':'species_search', 'species_kind':kind}
        if kind == 'prohibited':
            values['prohibited_activity'] = qualifier
        else:
            values['species_scope'] = qualifier
        context.user_data.update(values)
        return q.edit_message_text('Tür adını yazın. Örnek: <code>kalkan</code>, <code>mavi yengeç</code>, <code>palamut</code>.', parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Tür Menüsü', 'species:menu')]]))
    if data.startswith('sp:'):
        _, kind, sid = data.split(':')
        return show_species(q, kind, int(sid), context)

    if data.startswith('pen:length:'):
        pid=int(data.rsplit(':',1)[1])
        context.user_data.update(mode='penalty_length',penalty_pid=pid)
        return q.edit_message_text('🚤 Gemi tam boyunu metre olarak yazın. Örnek: <code>17.4</code>',parse_mode=ParseMode.HTML,reply_markup=kb([[('↩️ Ceza Kartı',f'pen:{pid}')]]))
    if data.startswith('pen:'):
        return show_penalty(q, int(data.split(':', 1)[1]), context)
    if data.startswith('raw:'):
        row = db.raw_row(int(data.split(':', 1)[1]))
        if not row:
            return q.answer('Excel satırı bulunamadı.', show_alert=True)
        return q.edit_message_text(
            f'📊 <b>Excel satır {row["source_row"]}</b>\n\n<code>{esc(row["raw_text"])}</code>\n\n<i>Değerler yüklediğiniz Excel kaynağındaki haliyle gösterilir.</i>',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('↩️ Ana Menü', 'menu')]]),
        )

    if data == 'audit:start':
        return audit_start(q, context)
    if data.startswith('audit:region:'):
        context.user_data['audit_region'] = data.rsplit(':', 1)[1]
        if context.user_data['audit_region'] == 'inland':
            context.user_data['mode'] = 'audit_location'
            return q.edit_message_text(
                '🏞️ <b>İÇSU KONUMU</b>\n\nİl ile göl, baraj, akarsu veya kaynak adını yazın. '
                'Örnek: <code>Ankara — Mogan Gölü</code>.',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('➡️ Konumu Sonra Belirt', 'audit:location:skip')], [('↩️ Alan Seçimine Dön', 'audit:start')]])
            )
        return audit_choose_activity(q, context)
    if data == 'audit:location:skip':
        context.user_data.pop('mode', None)
        return audit_choose_activity(q, context)
    if data == 'audit:activitymenu':
        return audit_choose_activity(q, context)
    if data.startswith('audit:activity:'):
        context.user_data['audit_activity'] = data.rsplit(':', 1)[1]
        if context.user_data['audit_activity'] in {'processing', 'aquaculture'}:
            context.user_data['audit_length_band'] = 'none'
            context.user_data['audit_length'] = 0.0
            return audit_choose_date(q, context)
        return audit_choose_length(q, context)
    if data.startswith('audit:length:'):
        choice = data.rsplit(':', 1)[1]
        if choice == 'exact':
            context.user_data['mode'] = 'audit_length_exact'
            return q.edit_message_text(
                '🚤 <b>GEMİ / TEKNE TAM BOYU</b>\n\nTam boyu metre olarak yazın. Örnek: <code>17.4</code>',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('🏠 Ana Menü', 'menu')]])
            )
        _, rule_value = LENGTH_BANDS[choice]
        context.user_data['audit_length_band'] = choice
        context.user_data['audit_length'] = rule_value
        context.user_data.pop('audit_length_exact', None)
        return audit_choose_date(q, context)
    if data == 'audit:datemenu':
        return audit_choose_date(q, context)
    if data == 'audit:subjectmenu':
        return audit_choose_subject(q, context)
    if data == 'audit:gearmenu':
        return audit_choose_gear(q, context)
    if data == 'audit:date:today':
        context.user_data['audit_date'] = datetime.now(TZ).date().isoformat()
        return audit_choose_subject(q, context)
    if data == 'audit:date:other':
        context.user_data['mode'] = 'audit_date'
        return q.edit_message_text(
            '📅 <b>OLAY / KONTROL TARİHİ</b>\n\nTarihi <code>GG.AA.YYYY</code> biçiminde yazın. Örnek: <code>20.05.2026</code>.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📅 Bugünü Kullan', 'audit:date:today')], [('↩️ Tarih Seçimine Dön', 'audit:datemenu'), ('🏠 Ana Menü', 'menu')]])
        )
    if data.startswith('audit:subject:'):
        subject = data.rsplit(':', 1)[1]
        context.user_data['audit_subject'] = subject
        if subject == 'fishing':
            return audit_choose_gear(q, context)
        if subject == 'species':
            context.user_data.update(mode='audit_species_search', species_kind=context.user_data.get('audit_activity','commercial'), species_scope=audit_species_scope(context), guided_species=True)
            examples = 'sazan, yayın, inci kefali' if audit_species_scope(context) == 'inland' else 'kalkan, palamut, hamsi'
            return q.edit_message_text(
                f'🐟 <b>ÜRÜN / TÜR</b>\n\nKontrol edilen türün adını yazın. Örnek: <code>{examples}</code>.',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('➡️ Tür belirtmeden devam', 'audit:guided:check')], [('🏠 Ana Menü', 'menu')]])
            )
        return audit_quick_start(q, context)
    if data.startswith('audit:gear:'):
        context.user_data['audit_gear'] = data.split(':', 2)[2]
        if context.user_data.get('guided_active'):
            return audit_after_gear(q, context)
        return audit_gear_result(q, context)
    if data == 'audit:guided:species':
        context.user_data.update(mode='audit_species_search', species_kind=context.user_data.get('audit_activity','commercial'), species_scope=audit_species_scope(context), guided_species=True)
        examples = 'sazan, yayın, inci kefali' if audit_species_scope(context) == 'inland' else 'kalkan, palamut, hamsi'
        return q.edit_message_text(
            f'🐟 <b>TÜRÜ YAZIN</b>\n\nTür adını yazın (örnek: <code>{examples}</code>). Tür bilinmiyorsa tür belirtmeden devam edebilirsiniz.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('➡️ Tür belirtmeden devam', 'audit:guided:check')], [('🏠 Ana Menü', 'menu')]])
        )
    if data == 'audit:guided:check':
        context.user_data.pop('mode', None)
        return audit_quick_start(q, context)
    if data == 'audit:hub':
        return audit_hub_edit(q, context)
    if data == 'classify:start':
        return amateur_classification_start(q, context)
    if data.startswith('classify:ans:'):
        _, _, idx, ans = data.split(':', 3)
        return amateur_classification_answer(q, context, int(idx), ans)
    if data == 'audit:quick:start':
        return audit_quick_start(q, context)
    if data.startswith('audit:quick:ans:'):
        _, _, _, idx, ans = data.split(':', 4)
        return audit_quick_answer(q, context, int(idx), ans)

    if data == 'insp:resume':
        return resume_draft(q, context)
    if data == 'insp:discard':
        db.drop_draft(uid)
        context.user_data.clear()
        return send_menu(q, uid, edit=True)


def article_chunks(text, limit=2450):
    text = (text or '').strip()
    if not text:
        return ['—']
    chunks=[]
    while len(text)>limit:
        cut=text.rfind('\n',0,limit)
        if cut<limit//2:
            cut=text.rfind(' ',0,limit)
        if cut<limit//2:
            cut=limit
        chunks.append(text[:cut].strip())
        text=text[cut:].strip()
    if text: chunks.append(text)
    return chunks or ['—']


def show_source_list(q, source, page=0):
    rows_all=db.list_articles(source)
    per=8
    pages=max(1,(len(rows_all)+per-1)//per)
    page=max(0,min(page,pages-1))
    part=rows_all[page*per:(page+1)*per]
    rows=[[(f'Md.{r["article"]} — {(r["title"] or "Başlıksız madde")[:37]}',f'art:{source}:{r["article"]}')] for r in part]
    nav=[]
    if page>0: nav.append(('◀️ Önceki',f'srclist:{source}:{page-1}'))
    if page+1<pages: nav.append(('Sonraki ▶️',f'srclist:{source}:{page+1}'))
    if nav: rows.append(nav)
    rows.append([('🔎 Bu Kaynakta Ara',f'src:{source}'),])
    q.edit_message_text(
        f'📑 <b>{esc(SRC_LABEL.get(source,source))} — TÜM MADDELER</b>\n\nSayfa {page+1}/{pages}. Deniz, içsu, tesis ve genel hükümler birlikte gösterilir.',
        parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_article(q, source, article, page=0, context=None):
    row = db.get_article(source, article)
    if not row:
        return q.answer('Madde bulunamadı.', show_alert=True)
    chunks=article_chunks(row['body'])
    page=max(0,min(page,len(chunks)-1))
    pages = str(row['page_start']) if row['page_start'] == row['page_end'] else f'{row["page_start"]}–{row["page_end"]}'
    text = f'📚 <b>{esc(SRC_LABEL.get(source, source))} — Madde {article}</b>\n'
    if row['title']:
        text += f'<b>{esc(row["title"])}</b>\n'
    text += f'<i>Kaynak PDF sayfa {pages} | Metin bölümü {page+1}/{len(chunks)}</i>\n\n{esc(chunks[page])}'
    nav=[]
    if page>0: nav.append(('◀️ Önceki',f'artp:{source}:{article}:{page-1}'))
    if page+1<len(chunks): nav.append(('Sonraki ▶️',f'artp:{source}:{article}:{page+1}'))
    rows=[]
    if nav: rows.append(nav)
    rows.append([('📑 Madde Listesi', f'srclist:{source}:0')])
    if context and context.user_data.get('guide_key'):
        rows.append([('🔙 Uygunsuzluk Listesine Dön', 'guide:badmenu')])
    rows.append([('🏠 Ana Menü', 'menu')])
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_field(q, category):
    rules = db.search_rules(cat=category, limit=20)
    rows = [[(r['title'][:45], f'rule:{r["id"]}')] for r in rules]
    rows.append([('↩️ Ana Menü', 'menu')])
    q.edit_message_text(f'🛡️ <b>{esc(category)}</b>\n\nKontrol kartını seçin:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_rule(q, rule_id):
    row = db.get_rule(rule_id)
    if not row:
        return q.answer('Kontrol kartı bulunamadı.', show_alert=True)
    refs = json.loads(row['refs'])
    buttons, ref_text = [], []
    for ref in refs:
        label = SRC_LABEL.get(ref['s'], ref['s'])
        ref_text.append(f'{label} Md. {ref["a"]}')
        buttons.append((f'📚 {label} {ref["a"]}', f'art:{ref["s"]}:{ref["a"]}'))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([('🔙 Geri', f"field:{row['cat']}"), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(
        f'🛡️ <b>{esc(row["title"])}</b>\n\n{esc(row["summary"])}\n\n<b>Dayanak:</b> {esc("; ".join(ref_text))}',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


SPECIES_VISUAL_GUIDE = {
    'barbunya_tekir': {
        'title': 'Barbunya vs Tekir Ayrımı',
        'species': 'Barbunya (Mullus barbatus) & Tekir (Mullus surmuletus)',
        'min_cm': 'Her ikisi için asgari boy: 12 cm',
        'key_points': [
            '🐟 <b>Barbunya (Mullus barbatus):</b> Burun profili diktir (alın 90 dereceye yakın dik iner). 1. sırt yüzgeci renksiz ve desensizdir. Vücut pembe-kırmızıdır.',
            '🐟 <b>Tekir (Mullus surmuletus):</b> Burun profili tatlı bir eğimle uzundur. 1. sırt yüzgecinde koyu sarı-siyah enine bantlar bulunur. Vücutta sarı boyuna çizgiler vardır.',
            '🔎 <b>Saha Püf Noktası:</b> Sırt yüzgecine bakın: Bantlı/çizgili ise Tekir, lekesiz düz ise Barbunya.'
        ],
        'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Mullus_surmuletus_Gervais.jpg/640px-Mullus_surmuletus_Gervais.jpg'
    },
    'lufer_boylar': {
        'title': 'Lüfer Boy Kademeleri ve Yasağı',
        'species': 'Lüfer (Pomatomus saltatrix)',
        'min_cm': 'Asgari Avlanabilir Boy: 18 cm',
        'key_points': [
            '🚫 <b>Yaprak / Çinekop (&lt;15 cm):</b> Avlanması, satışı ve nakli KESİNLİKLE YASAKTIR.',
            '🚫 <b>Sarıkanat (15 – 18 cm):</b> Avlanması ve satışı KESİNLİKLE YASAKTIR.',
            '✅ <b>Lüfer (18 – 25 cm):</b> Yasal asgari boy sınırıdır (18 cm).',
            '✅ <b>Kofana / Sırtıkara (&gt;25 cm / &gt;35 cm):</b> Yasal boydadır.',
            '🔎 <b>Saha Püf Noktası:</b> Ağızda jilet gibi kesici dişler, geniş çatal kuyruk ve sarımsı göz halkası belirgindir.'
        ],
        'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Pomatomus_saltatrix_Gervais.jpg/640px-Pomatomus_saltatrix_Gervais.jpg'
    },
    'hamsi_caca': {
        'title': 'Hamsi vs Çaça Ayrımı',
        'species': 'Hamsi (Engraulis encrasicolus) & Çaça (Sprattus sprattus)',
        'min_cm': 'Hamsi Asgari Boy: 9 cm | Çaça: Endüstriyel serbest',
        'key_points': [
            '🐟 <b>Hamsi:</b> Üst çene alt çeneyi belirgin şekilde aşar (sivri burun). Ağız yarığı gözün çok gerisine kadar uzanır. Karın altı düz ve pürüzsüzdür.',
            '🐟 <b>Çaça:</b> Alt çene üst çeneden hafifçe öne çıkıktır. Karın altında kuyruğa doğru parmak sürüldüğünde sert testere dişi pullar (karina) ele gelir.',
            '🔎 <b>Saha Püf Noktası:</b> Balığın karnında parmağınızı sürtün; takılma varsa ÇAÇA, kaygan ve pürüzsüzse HAMSİ.'
        ],
        'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Engraulis_encrasicolus.jpg/640px-Engraulis_encrasicolus.jpg'
    },
    'orfoz_lahoz': {
        'title': 'Orfoz vs Lahoz (Girida) Ayrımı',
        'species': 'Orfoz (Epinephelus marginatus) & Lahoz (Epinephelus aeneus)',
        'min_cm': 'Her ikisi için asgari boy: 50 cm',
        'key_points': [
            '🐟 <b>Orfoz:</b> Kuyruk yüzgeci kenarı yuvarlaktır. Vücut koyu kahve-yeşil zemin üzerine sarımsı mermer desenlidir. 15 Haziran – 31 Ağustos arası üreme yasağı vardır.',
            '🐟 <b>Lahoz (Girida):</b> Kuyruk yüzgeci kenarı düz kesimlidir. Solungaç kapağında ve yanaklarında gözün arkasından uzanan 2-3 adet açık renkli/mavi-beyaz paralel şerit bulunur.',
            '🔎 <b>Saha Püf Noktası:</b> Yanakta paralel beyaz çizgiler varsa Lahoz, gövde mermer benekli ve kuyruk yuvarlaksa Orfoz.'
        ],
        'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Epinephelus_marginatus.jpg/640px-Epinephelus_marginatus.jpg'
    },
    'kalkan_pisi_dil': {
        'title': 'Kalkan vs Pisi vs Dil Balığı Ayrımı',
        'species': 'Kalkan (Scophthalmus), Pisi (Platichthys), Dil (Solea solea)',
        'min_cm': 'Kalkan: 45 cm | Pisi: 20 cm | Dil: 20 cm',
        'key_points': [
            '🐟 <b>Kalkan:</b> Vücut tam bir daire şeklindedir. Üst derisinde sert, kemiksi düğmeler (tüberkül) bulunur. Min. boy 45 cm.',
            '🐟 <b>Pisi:</b> Vücut ovaldir, derisi pürüzsüzdür, kemiksi düğme yoktur. Min. boy 20 cm.',
            '🐟 <b>Dil Balığı:</b> Vücut uzunca oval dil biçimindedir. Burun yuvarlak ve çene altı bıyıklıdır. Min. boy 20 cm.'
        ],
        'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Scophthalmus_maximus.jpg/640px-Scophthalmus_maximus.jpg'
    },
    'yasakli_kopekbaligi_vatoz': {
        'title': 'Yasaklı Köpekbalığı ve Vatoz Türleri',
        'species': 'Büyük Beyaz, Camgöz, Domuzbalığı, Keler, Şeytan Vatozu, Manta',
        'min_cm': 'Tamamen Avlanması ve Satışı Yasak Türler',
        'key_points': [
            '🚫 <b>Yasak Kapsamı:</b> 1380 Sayılı Kanun ve 6/1-6/2 Tebliğleri Ek-1 kapsamında bu türlerin avlanması, karaya çıkarılması, teknede bulundurulması, nakli ve satışı KESİNLİKLE YASAKTIR.',
            '⚠️ <b>Ağda Canlı Yakalanırsa:</b> Derhal ve zarar verilmeden denize iade edilmek zorundadır.',
            '📋 <b>Yaptırım:</b> İdari para cezası uygulanır ve ürüne/av aracına el konulur.'
        ],
        'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/White_shark.jpg/640px-White_shark.jpg'
    }
}

GEAR_VISUAL_GUIDE = {
    'tiriviri': {
        'title': '🚫 Tırıvırı (Paraşüt Ağ / Katil Ağ)',
        'status': 'Üretimi, Satışı, Bulundurulması ve Kullanımı KESİNLİKLE YASAK',
        'description': (
            'İnce monofilament misinadan örülmüş, bir ucu kurşun ağırlıklı diğer ucu fırdöndülü '
            'küçük paraşüt benzeri ölüm tuzağı ağdır.\n\n'
            '🔍 <b>Saha Tespiti:</b> Olta kamışlarının ucuna takılı veya takımların arasında poşetlenmiş olarak bulunur. '
            'Kopup dipte kalarak yıllarca balık ve su canlılarını öldürmeye devam eder (hayalet avcılık).\n\n'
            '⚖️ <b>Yaptırım:</b> 1380 Sayılı Kanun Ek Madde 3 ve Madde 36 uyarınca idari para cezası ve araca/ağa doğrudan el koyma işlemi uygulanır.'
        )
    },
    'manyat': {
        'title': '🚫 Manyat (Kıyı Sürütme Ağı)',
        'status': 'Marmara Karides Manyatı Dışında Tüm Sularda Yasaktır',
        'description': (
            'Kıyıdan veya sığ sudan çekilen, iki uzun kanadı ve ortasında torbası bulunan ince gözlü sürütme ağıdır.\n\n'
            '🔍 <b>Saha Tespiti:</b> Kıyıya yakın teknelerden veya karadan çekilen halatlar ve kıyıya serilmiş torba ağlar.\n\n'
            '⚖️ <b>Yaptırım:</b> Yetkisiz bölge ve dönemde kullanımında 1380 sayılı Kanun kapsamında cezai işlem ve ağa el koyma uygulanır.'
        )
    },
    'elektrosok_patlayici': {
        'title': '🚫 Elektroşok, Patlayıcı (Dinamit) ve Kimyasal Maddeler',
        'status': 'Ağır Adli Suç ve Müsadere Kapsamındadır',
        'description': (
            'Suya elektrik akımı verilmesi (invertör/akü/jeneratör), dinamit/torpil atılması veya kireç/zehir dökülmesidir.\n\n'
            '🔍 <b>Saha Tespiti:</b> Teknede açık uçlu kablolu kepçeler, 12V-220V invertör tertibatı, şüpheli patlayıcı fitil veya kimyasal kokusu.\n\n'
            '⚖️ <b>Yaptırım:</b> 1380 Sayılı Kanun Madde 19 ve 36 gereğince en ağır para cezası, adli sevk, tekne ve tüm av araçlarına el koyma.'
        )
    },
    'isik_luks': {
        'title': '🚫 Işıkla Avcılık (Projektör / Lüks) Sınırları',
        'status': 'İzne Tabi — Belirlenen Güç ve Alan Dışında Yasak',
        'description': (
            'Yüksek güçte lüks lambaları veya projektörlerle balıkların ışığa toplanıp çevrilmesi.\n\n'
            '🔍 <b>Saha Tespiti:</b> Ruhsatında ışıkla avcılık izni olmayan tekneler, ışık yasağı bulunan körfez ve koylarda projektör yakılması veya izin verilen jeneratör/lümen sınırının aşılması.\n\n'
            '⚖️ <b>Yaptırım:</b> İdari para cezası ve yetkisiz donanıma el koyma.'
        )
    },
    'dip_trolu': {
        'title': '🚫 Dip Trolü Donanımı ve Mesafe/Bölge İhlali',
        'status': 'Marmara, Boğazlar ve Kıyıdan 3 Mil İçinde Kesinlikle Yasak',
        'description': (
            'Deniz tabanını tarayarak çeken torba ağ ve iki adet ağır çelik/ahşap trol kapısı tertibatıdır.\n\n'
            '🔍 <b>Saha Tespiti:</b> Kıçta matafora (bom), çelik çekme telleri ve asılı duran ağır trol kapıları. Kapıların ıslaklığı veya ağın denize salınmış olması tespit için kritiktir.\n\n'
            '⚖️ <b>Yaptırım:</b> Yasak sahada trol çekilmesinde yüksek idari para cezası, ruhsatın askıya alınması ve av araçlarına el koyma.'
        )
    },
    'algarna': {
        'title': '🚫 Algarna / Dreç (Demir Kafesli Kazıma Aleti)',
        'status': 'Özel Ruhsat ve İzne Tabidir — Bölge Kısıtlamaları Vardır',
        'description': (
            'Deniz salyangozu ve çift kabuklu yumuşakçaları toplamak için deniz dibini kazıyan demir kafes ve alt tarama bıçağıdır.\n\n'
            '🔍 <b>Saha Tespiti:</b> Tekne güvertesinde veya kıçında ağır metal çerçeveli kafesler, alt bıçak tertibatı ve çelik halatlar.\n\n'
            '⚖️ <b>Yaptırım:</b> Yasak bölge/dönemde kullanımında idari para cezası ve ruhsat işlemi uygulanır.'
        )
    }
}


def show_species_visual_menu(q):
    rows = []
    for key, item in SPECIES_VISUAL_GUIDE.items():
        rows.append([(f'🐟 {item["title"]}', f'species:vis:item:{key}')])
    rows.append([('↩️ Tür Menüsü', 'species:menu'), ('🏠 Ana Menü', 'menu')])
    text = (
        '🖼️ <b>GÖRSEL BALIK TEŞHİS VE AYRIM REHBERİ</b>\n\n'
        'Sahada sıkça karıştırılan türleri ve kritik boy kademelerini görsel tanı kriterleriyle inceleyin:\n'
    )
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_species_visual_item(q, key):
    item = SPECIES_VISUAL_GUIDE.get(key)
    if not item:
        return q.answer('Görsel kart bulunamadı.', show_alert=True)
    text = f'🖼️ <b>{esc(item["title"])}</b>\n'
    text += f'<b>Tür(ler):</b> {esc(item["species"])}\n'
    text += f'📏 <b>Ölçü Kriteri:</b> {esc(item["min_cm"])}\n\n'
    text += '<b>Ayırt Edici Tanı Kriterleri:</b>\n'
    for pt in item['key_points']:
        text += f'• {pt}\n'
    if item.get('photo_url'):
        text += f'\n<a href="{item["photo_url"]}">&#8205;</a><i>(Fotoğraf önizlemesi yukarıda görüntülenmektedir)</i>\n'
    rows = [[('↩️ Görsel Rehber', 'species:vis:menu'), ('🐟 Tür Menüsü', 'species:menu')]]
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_gear_visual_menu(q):
    rows = []
    for key, item in GEAR_VISUAL_GUIDE.items():
        rows.append([(f'{item["title"][:40]}', f'gear:vis:item:{key}')])
    rows.append([('🔙 Gemi / Donanım Menüsü', 'vessel:menu'), ('🏠 Ana Menü', 'menu')])
    text = (
        '🚫 <b>YASAK AV ARAÇLARI GÖRSEL TESPİT REHBERİ</b>\n\n'
        'Sahada şüpheli veya yasaklı av donanımlarını tespit etmek için kılavuz kartlarını seçin:\n'
    )
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_gear_visual_item(q, key):
    item = GEAR_VISUAL_GUIDE.get(key)
    if not item:
        return q.answer('Donanım kartı bulunamadı.', show_alert=True)
    text = f'🚫 <b>{esc(item["title"])}</b>\n'
    text += f'⚠️ <b>Durum:</b> {esc(item["status"])}\n\n'
    text += f'{item["description"]}\n'
    rows = [[('↩️ Yasak Araçlar Listesi', 'gear:vis:menu'), ('🏠 Ana Menü', 'menu')]]
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def in_date_range(today, span):
    start, end = span.split('/')
    sm, sd = map(int, start.split('-'))
    em, ed = map(int, end.split('-'))
    x, lo, hi = (today.month, today.day), (sm, sd), (em, ed)
    return lo <= x <= hi if lo <= hi else (x >= lo or x <= hi)


def show_species(q, kind, sid, context=None):
    row = db.get_species(kind, sid)
    if not row:
        return q.answer('Tür bulunamadı.', show_alert=True)
    bans = json.loads(row['time_bans'])
    today = audit_date(context) if context is not None and context.user_data.get('guided_active') else datetime.now(TZ).date()
    closed = any(in_date_range(today, span) for span in bans)
    water = 'İçsu' if row['scope'] == 'inland' else 'Deniz'
    title = f'{"Ticari — 6/1" if kind == "commercial" else "Amatör — 6/2"} · {water}'
    text = f'{header("🐟", row["name"], title)}\n{HR}\n'
    if row['min_cm'] is not None:
        text += field('Asgari boy', f'{row["min_cm"]:g} cm', '📏') + '\n'
    if row['min_kg'] is not None:
        text += field('Asgari ağırlık', f'{row["min_kg"]:g} kg', '⚖️') + '\n'
    if kind == 'amateur':
        text += field('Alıkonulabilir miktar', row['limit_text'], '🎒') + '\n'
    if bans:
        human = ', '.join(span.replace('/', ' – ') for span in bans)
        text += field('Zaman yasağı', human, '📅') + '\n'
        stamp = today.strftime('%d.%m.%Y')
        text += HR + '\n'
        if closed:
            text += badge(
                'stop', f'{stamp} — ZAMAN YASAĞI DÖNEMİ',
                'Bu tarih, tür için kaydedilmiş zaman yasağı aralığına denk geliyor. '
                'İzin ve istisnalar varsa özel maddeden ayrıca kontrol edilmelidir.',
            ) + '\n'
        else:
            text += badge(
                'ok', f'{stamp} — Yasak aralığı dışında',
                'Kaydedilmiş zaman yasağı aralığına denk gelmiyor; özel saha/izin/kota '
                'hükümleri yine devam edebilir.',
            ) + '\n'
    else:
        text += HR + '\n'
        text += badge(
            'warn', 'Zaman yasağı kaydı yok',
            'Boy/miktar veri satırında tek bir zaman yasağı aralığı kaydedilmemiştir. '
            'Türün özel maddesi varsa bölge, kota, izin veya dönem hükümleri ayrıca '
            'kontrol edilmelidir.',
        ) + '\n'

    if row['scope'] == 'inland':
        text += badge(
            'warn', 'Bölgesel içsu kuralları ayrıca kontrol edilmeli',
            'İçsu zaman yasakları ve bazı miktar şartları il, bölge veya su kaynağına göre değişebilir. '
            'Denetim konumunu ilgili Tebliğ maddesindeki bölgesel çizelgeyle eşleştirin.',
        ) + '\n'

    source = '61' if kind == 'commercial' else '62'
    article = row['article_size'] if kind == 'commercial' else row['article']
    rows = [[('📚 Boy/Miktar Kaynağı', f'art:{source}:{article}'), ('⚖️ Yaptırım Ara', 'mode:penalty')]]
    
    # Check if a visual guide exists for this species
    vis_key = None
    lower_name = row['name'].lower()
    if 'barbunya' in lower_name or 'tekir' in lower_name:
        vis_key = 'barbunya_tekir'
    elif 'lüfer' in lower_name or 'lufer' in lower_name or 'çinekop' in lower_name or 'sarıkanat' in lower_name:
        vis_key = 'lufer_boylar'
    elif 'hamsi' in lower_name or 'çaça' in lower_name:
        vis_key = 'hamsi_caca'
    elif 'orfoz' in lower_name or 'lahoz' in lower_name or 'girida' in lower_name:
        vis_key = 'orfoz_lahoz'
    elif 'kalkan' in lower_name or 'pisi' in lower_name or 'dil' in lower_name:
        vis_key = 'kalkan_pisi_dil'
        
    if vis_key:
        rows.append([('🖼️ Görsel / Teşhis Kartı', f'species:vis:item:{vis_key}')])
        
    if kind == 'commercial' and row['article_time']:
        rows.append([('📅 Tür Özel Maddesi', f'art:61:{row["article_time"]}')])
    if context is not None and context.user_data.get('mode') == 'audit_species_search':
        context.user_data['audit_species_name'] = row['name']
        context.user_data['audit_species_id'] = row['id']
        context.user_data['audit_species_kind'] = kind
        context.user_data.pop('mode', None)
        if context.user_data.get('guided_active'):
            rows.append([('➡️ Duruma Özel Kontrole Devam', 'audit:guided:check')])
            rows.append([('↩️ Denetim Özeti', 'audit:hub'), ('⚖️ Yaptırım Ara', 'mode:penalty')])
        else:
            rows.append([('🚨 Kontrole Dön', 'audit:hub'), ('⚖️ Yaptırım Ara', 'mode:penalty')])
    else:
        rows.append([('🖼️ Görsel Rehber', 'species:vis:menu'), ('↩️ Tür Menüsü', 'species:menu')])
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def _first_article(value):
    if not value:
        return None
    m = re.search(r'(?<![A-Za-z])(?:Madde\s*)?(\d+)', str(value), re.I)
    return int(m.group(1)) if m else None


def _amount_for_length(amounts, length):
    if length is None:
        return None, None
    if length < 12 and '<12 m' in amounts:
        return '<12 m', amounts['<12 m']
    if 12 <= length < 22 and '12–<22 m' in amounts:
        return '12–<22 m', amounts['12–<22 m']
    if length >= 22 and '≥22 m' in amounts:
        return '≥22 m', amounts['≥22 m']
    return None, None


def show_penalty(q, pid, context):
    row = db.get_penalty(pid)
    if not row:
        return q.answer('Ceza kaydı bulunamadı.', show_alert=True)
    amounts = json.loads(row['amounts'] or '{}')
    text = f'⚖️ <b>{esc(row["violation"])}</b>\n'
    if row['option_text']:
        text += f'<b>Seçenek:</b> {esc(row["option_text"])}\n'
    text += f'\n💰 <b>Temel/tekil Excel tutarı: {money(row["base_ipc"])}</b>\n'
    if amounts:
        text += '💰 <b>Excel’deki özel tutarlar:</b>\n'
        for label, amount in amounts.items():
            text += f'• {esc(label)} → <b>{money(amount)}</b>\n'
        has_length_context = any(k in context.user_data for k in ('audit_length', 'audit_length_band', 'audit_length_exact'))
        length = audit_rule_length(context) if has_length_context else None
        lab, selected = _amount_for_length(amounts, length)
        if selected is not None:
            text += f'➡️ Seçili kontrol bağlamı ({esc(audit_length_label(context))}): <b>{esc(lab)} = {money(selected)}</b>\n'
        if context.user_data.get('audit_gear') == 'gırgır' and 'Gırgır' in amounts:
            text += f'➡️ Seçili av aracı gırgır: Excel’de ayrıca <b>{money(amounts["Gırgır"])}</b> gösterilmiş.\n'
    text += (
        f'\n📜 Kanun: {esc(row["law"])} | Yönetmelik: {esc(row["regulation"])} | Tebliğ: {esc(row["teblig"])} | 36. md: {esc(row["art36"])}\n'
        f'🐟 Ürüne el koyma: {esc(row["product_seizure"])}\n'
        f'🪢 İstihsal vasıtası: {esc(row["means_seizure"])}\n'
        f'📊 <b>Excel kaynak satırı: {row["source_row"]}</b>'
    )
    if row['repeat_text']:
        text += f'\n🔁 {esc(row["repeat_text"])}'
    if row['license_action']:
        text += f'\n📄 {esc(row["license_action"])}'
    if row['notes']:
        text += f'\n📝 {esc(row["notes"])}'
    text += (
        '\n\n⚠️ <i>Tutarlar ve Excel’deki el koyma/tekrar notları, yüklediğiniz ceza tablosundaki haliyle gösterilir. '
        'Sistem farklı katsayıları kendiliğinden üst üste çarpmaz. Somut olayın maddi unsurları ve asli mevzuat maddesi ayrıca kontrol edilmelidir.</i>'
    )

    source_buttons = []
    la = _first_article(row['law'])
    if la and db.get_article('law', la):
        source_buttons.append((f'📘 Kanun Md.{la}', f'art:law:{la}'))
    ra = _first_article(row['regulation'])
    if ra and db.get_article('reg', ra):
        source_buttons.append((f'📗 Yön. Md.{ra}', f'art:reg:{ra}'))
    tsrc = row['teblig_source'] or '61'
    if row['teblig'] and '6/2' in str(row['teblig']):
        tsrc = '62'
    ta = _first_article(row['teblig'])
    if ta and db.get_article(tsrc, ta):
        source_buttons.append((f'📙 {SRC_LABEL.get(tsrc, tsrc)} Md.{ta}', f'art:{tsrc}:{ta}'))
    rows = []
    for i in range(0, len(source_buttons), 2):
        rows.append(source_buttons[i:i+2])
    if any(k in amounts for k in ['<12 m','12–<22 m','≥22 m']):
        rows.append([('🚤 Gemi Boyuna Göre Göster',f'pen:length:{pid}')])
    rows.append([('📊 Excel Ham Satır', f'raw:{row["source_row"]}'), ('🧾 Kolluk İşlemi', 'field:Kolluk İşlemi')])
    rows.append([('🏠 Ana Menü', 'menu')])
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def guide_ref_label(ref):
    source, article = ref
    return f'{SRC_LABEL.get(source, source)} Md.{article}'


def guide_current(context):
    key = context.user_data.get('guide_key')
    return GUIDES.get(key)


def guide_short(text, n=82):
    s = str(text or '').strip()
    return s if len(s) <= n else s[:n-1].rstrip() + '…'


def guide_menu(q, context):
    db.log(q.from_user.id, 'guide_menu')
    rows = []
    for i in range(0, len(GUIDE_LIST), 2):
        line = []
        for g in GUIDE_LIST[i:i+2]:
            line.append((f'🚤 {g["short_title"][:28]}', f'guide:open:{g["key"]}'))
        rows.append(line)
    rows.append([('🚨 Yönlendirilmiş Denetim', 'audit:start'), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(
        '📋 <b>TEKNE TÜRÜNE GÖRE SAHA KILAVUZU</b>\n\n'
        'Kontrol edeceğiniz tekne/av yöntemi türünü seçin. Her föy yalnız o faaliyette sahada bakılması gereken '
        'belge, donanım, av aracı, yer-zaman ve ürün kontrollerini açar.\n\n'
        '<i>Deniz, içsu, dalyan/lagün ve amatör av araçlarına ait föyler birlikte gösterilir.</i>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


def guide_open(q, context, key):
    g = GUIDES.get(key)
    if not g:
        return q.answer('Kontrol föyü bulunamadı.', show_alert=True)
    context.user_data['guide_key'] = key
    measurements = ' · '.join(g.get('measure_fields') or [])
    text = (
        f'🚤 <b>{esc(g["title"])}</b>\n\n'
        f'{esc(g["subtitle"])}\n\n'
        f'☑️ Kontrol kalemi: <b>{len(g["rows"])}</b>\n'
        f'📐 Ölçüm/kayıt alanları: <b>{esc(measurements)}</b>\n\n'
        'Tekneye çıkmadan önce <b>Hızlı Kılavuz</b> ile bütün maddeleri okuyabilir veya '
        '<b>İnteraktif Kontrol</b> ile her maddeyi tek tek işaretleyebilirsiniz.'
    )
    rows = [
        [('👁️ Hızlı Kılavuzu Aç', f'guide:view:{key}:0'), ('✅ İnteraktif Kontrol', f'guide:start:{key}')],
        [('📐 Ölçüm / Kayıt Alanları', 'guide:measure:start')],
    ]
    if context.user_data.get('guided_active'):
        rows.append([('🚨 Denetime Dön', 'audit:hub'), ('↩️ Tekne Türleri', 'guide:menu')])
    else:
        rows.append([('↩️ Tekne Türleri', 'guide:menu'), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def guide_view(q, context, key, page=0):
    g = GUIDES.get(key)
    if not g:
        return q.answer('Kontrol föyü bulunamadı.', show_alert=True)
    context.user_data['guide_key'] = key
    per_page = 4
    total_pages = max(1, (len(g['rows']) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    chunk = g['rows'][start:start+per_page]
    text = f'👁️ <b>{esc(g["short_title"])} — HIZLI KILAVUZ</b>\nSayfa {page+1}/{total_pages}\n\n'
    for item in chunk:
        text += f'<b>{item["no"]}.</b> {esc(item["text"])}\n'
        text += f'<i>Dayanak: {esc(guide_ref_label(item["ref"]))}</i>\n\n'
    nav = []
    if page > 0:
        nav.append(('⬅️ Önceki', f'guide:view:{key}:{page-1}'))
    if page < total_pages - 1:
        nav.append(('Sonraki ➡️', f'guide:view:{key}:{page+1}'))
    rows = [nav] if nav else []
    rows += [
        [('✅ İnteraktif Kontrolü Başlat', f'guide:start:{key}')],
        [('↩️ Föye Dön', f'guide:open:{key}')],
    ]
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def guide_refs(q, context, key):
    g = GUIDES.get(key)
    if not g:
        return q.answer('Kontrol föyü bulunamadı.', show_alert=True)
    rows = []
    buttons = []
    for source, article in g.get('refs') or []:
        if db.get_article(source, int(article)):
            buttons.append((guide_ref_label((source, article)), f'art:{source}:{article}'))
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i+2])
    rows.append([('↩️ Föye Dön', f'guide:open:{key}'), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(
        f'📚 <b>{esc(g["short_title"])} — KAYNAK MADDELER</b>\n\n'
        'Föydeki kontrollerin dayandığı kaynak maddeler aşağıdadır. Somut uygunsuzlukta ilgili maddenin tam metni ve ceza tablosu birlikte doğrulanmalıdır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


def guide_start(q, context, key):
    g = GUIDES.get(key)
    if not g:
        return q.answer('Kontrol föyü bulunamadı.', show_alert=True)
    context.user_data['guide_key'] = key
    context.user_data['guide_answers'] = [None] * len(g['rows'])
    context.user_data['guide_measurements'] = {}
    context.user_data.pop('mode', None)
    db.log(q.from_user.id, 'guide_start', g['short_title'])
    return guide_render(q, context, 0)


def guide_render(q, context, idx):
    g = guide_current(context)
    if not g:
        return q.answer('Aktif kontrol föyü bulunamadı.', show_alert=True)
    if idx < 0:
        idx = 0
    if idx >= len(g['rows']):
        return guide_finish(q, context)
    item = g['rows'][idx]
    answers = context.user_data.get('guide_answers') or [None] * len(g['rows'])
    current = answers[idx] if idx < len(answers) else None
    state = {'ok':'✅ Uygun', 'bad':'❌ Uygunsuz', 'skip':'⚪ Kontrol Edilmedi'}.get(current, '— Henüz işaretlenmedi')
    text = (
        f'{header("📋", g["short_title"])}\n'
        f'{progress_bar(idx + 1, len(g["rows"]))}\n'
        f'{tally(answers)}\n'
        f'{HR}\n\n'
        f'<b>{esc(item["text"])}</b>\n\n'
        f'{HR}\n'
        f'📚 <i>{esc(guide_ref_label(item["ref"]))}</i>\n'
        f'🔖 İşaret: <b>{esc(state)}</b>'
    )
    rows = [
        [('✅ Uygun', f'guide:ans:{idx}:ok'), ('❌ Uygunsuz', f'guide:ans:{idx}:bad')],
        [('⚪ Kontrol Edilmedi', f'guide:ans:{idx}:skip')],
        [('📚 İlgili Madde', f'art:{item["ref"][0]}:{item["ref"][1]}')],
    ]
    nav = []
    if idx > 0:
        nav.append(('⬅️ Önceki', f'guide:go:{idx-1}'))
    if idx < len(g['rows']) - 1:
        nav.append(('➡️ Sonraki', f'guide:go:{idx+1}'))
    if nav:
        rows.append(nav)
    rows.append([('📊 Sonucu Gör / Bitir', 'guide:finish'), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def guide_answer(q, context, idx, ans):
    g = guide_current(context)
    if not g or ans not in {'ok','bad','skip'}:
        return q.answer('Kontrol oturumu bulunamadı.', show_alert=True)
    answers = context.user_data.setdefault('guide_answers', [None] * len(g['rows']))
    while len(answers) < len(g['rows']):
        answers.append(None)
    if 0 <= idx < len(answers):
        answers[idx] = ans
    remember_draft(q, context, 'guide')
    next_idx = idx + 1
    if next_idx >= len(g['rows']):
        return guide_finish(q, context)
    return guide_render(q, context, next_idx)


def guide_result_parts(context):
    g = guide_current(context)
    if not g:
        return None, [], [], []
    answers = context.user_data.get('guide_answers') or [None] * len(g['rows'])
    ok, bad, unchecked = [], [], []
    for idx, item in enumerate(g['rows']):
        ans = answers[idx] if idx < len(answers) else None
        if ans == 'ok':
            ok.append((idx, item))
        elif ans == 'bad':
            bad.append((idx, item))
        else:
            unchecked.append((idx, item))
    return g, ok, bad, unchecked


def inspection_title(context, kind):
    """Short label stored with the record and shown in listings."""
    if kind == 'guide':
        g = guide_current(context)
        return g['short_title'] if g else 'Kontrol f\u00f6y\u00fc'
    region = REGION_LABEL.get(context.user_data.get('audit_region'), '\u2014')
    return f'Denetim \u2014 {region}'


def remember_draft(q, context, kind):
    """Snapshot the in-progress inspection so a restart cannot lose it."""
    try:
        db.save_draft(q.from_user.id, kind, inspection_title(context, kind), dict(context.user_data))
    except Exception:
        # Persistence is a safety net; never let it break the flow.
        pass


def resume_draft(q, context):
    """Reload the stored draft and drop the inspector back where they stopped."""
    row = db.open_draft(q.from_user.id)
    if not row:
        return q.answer('Yar\u0131da kalan denetim yok.', show_alert=True)
    context.user_data.clear()
    context.user_data.update(db.load_state(row))
    if row['kind'] == 'guide' and guide_current(context):
        answers = context.user_data.get('guide_answers') or []
        idx = next((i for i, a in enumerate(answers) if a is None), 0)
        return guide_render(q, context, idx)
    return audit_hub_edit(q, context)


def guide_finish(q, context):
    g, ok, bad, unchecked = guide_result_parts(context)
    if not g:
        return q.answer('Aktif kontrol föyü bulunamadı.', show_alert=True)
    measurements = context.user_data.get('guide_measurements') or {}
    text = (
        f'📊 <b>{esc(g["short_title"])} — KONTROL SONUCU</b>\n\n'
        f'✅ Uygun: <b>{len(ok)}</b>\n'
        f'❌ Uygunsuz: <b>{len(bad)}</b>\n'
        f'⚪ Kontrol Edilmedi: <b>{len(unchecked)}</b>\n'
    )
    if bad:
        text += '\n❌ <b>UYGUNSUZ İŞARETLENENLER</b>\n'
        for idx, item in bad:
            text += f'• {idx+1}. {esc(guide_short(item["text"], 115))}\n'
    if unchecked:
        text += '\n⚪ <b>KONTROL EDİLMEYENLER</b>\n'
        for idx, item in unchecked:
            text += f'• {idx+1}. {esc(guide_short(item["text"], 105))}\n'
    if measurements:
        text += '\n📐 <b>ÖLÇÜM / KAYITLAR</b>\n'
        for field in g.get('measure_fields') or []:
            if field in measurements:
                text += f'• {esc(field)}: <b>{esc(measurements[field])}</b>\n'
    text += '\n⚠️ <i>“Uygunsuz” işareti nihai yaptırım kararı değildir. İlgili kaynak maddesi ile ceza tablosundaki maddi unsurlar ayrıca doğrulanmalıdır.</i>'
    rows = [[('📐 Ölçüm / Kayıt Gir', 'guide:measure:start')]]
    if bad:
        rows.append([('⚖️ Uygunsuzluk → Yaptırım', 'guide:badmenu')])
    rows.append([('⚖️ Bu Denetimi Değerlendir', 'ai:audit')])
    rows.append([('🔄 Aynı Föyü Yenile', f'guide:start:{g["key"]}')])
    if context.user_data.get('guided_active'):
        rows.append([('🚨 Denetime Dön', 'audit:hub'), ('🏠 Ana Menü', 'menu')])
    else:
        rows.append([('↩️ Föye Dön', f'guide:open:{g["key"]}'), ('🏠 Ana Menü', 'menu')])
    db.log(q.from_user.id, 'guide_finish', f'{g["short_title"]}: bad={len(bad)}, unchecked={len(unchecked)}')
    try:
        # Closes the open draft so the "yarıda kalan denetim" prompt clears.
        db.finish_inspection(q.from_user.id, 'guide', inspection_title(context, 'guide'),
                             dict(context.user_data), '')
    except Exception:
        pass
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def guide_bad_menu(q, context):
    g, _, bad, _ = guide_result_parts(context)
    if not g:
        return q.answer('Aktif kontrol föyü bulunamadı.', show_alert=True)
    if not bad:
        return q.answer('Uygunsuz işaretlenmiş kontrol yok.', show_alert=True)
    rows = []
    for idx, item in bad:
        rows.append([(f'⚖️ {idx+1}. {guide_short(item["text"], 38)}', f'guide:pen:{idx}')])
    rows.append([('↩️ Sonuca Dön', 'guide:result'), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(
        f'⚖️ <b>{esc(g["short_title"])} — UYGUNSUZLUKLAR</b>\n\n'
        'Ceza/yaptırım tablosunda kontrol etmek istediğiniz uygunsuzluğu seçin.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


def guide_penalty_search(q, context, idx):
    g, _, _, _ = guide_result_parts(context)
    if not g or idx < 0 or idx >= len(g['rows']):
        return q.answer('Kontrol maddesi bulunamadı.', show_alert=True)
    item = g['rows'][idx]
    query = item.get('penalty_query') or g['short_title']
    results = db.search_penalties(query, LIMIT)
    rows = []
    for r in results:
        label = r['violation'][:31]
        if r['option_text']:
            label += ' / ' + r['option_text'][:12]
        rows.append([(f'⚖️ {label}', f'pen:{r["id"]}')])
    if not rows:
        for r in db.search_raw(query, 4):
            rows.append([(f'📊 Excel satır {r["source_row"]}', f'raw:{r["source_row"]}')])
    rows.append([('📚 İlgili Madde', f'art:{item["ref"][0]}:{item["ref"][1]}'), ('↩️ Uygunsuzluklar', 'guide:badmenu')])
    q.edit_message_text(
        f'⚖️ <b>YAPTIRIM ARAMASI</b>\n\n'
        f'Kontrol maddesi: {esc(guide_short(item["text"], 150))}\n\n'
        f'Arama anahtarı: <code>{esc(query)}</code>\n'
        f'Yapılandırılmış sonuç: <b>{len(results)}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


def guide_measure_start(q, context):
    g = guide_current(context)
    if not g:
        return q.answer('Önce bir tekne kontrol föyü seçin.', show_alert=True)
    context.user_data.setdefault('guide_measurements', {})
    context.user_data['guide_measure_idx'] = 0
    context.user_data['mode'] = 'guide_measure'
    return guide_measure_prompt_q(q, context)


def guide_measure_prompt_q(q, context):
    g = guide_current(context)
    idx = int(context.user_data.get('guide_measure_idx', 0))
    # Some guides define no measure_fields at all; the Telegram bot crashed here for them.
    fields = (g.get('measure_fields') or []) if g else []
    if not g or idx >= len(fields):
        context.user_data.pop('mode', None)
        back = [('↩️ Föye Dön', f'guide:open:{g["key"]}')] if g else [('📋 Tekne Türü Kılavuzları', 'guide:menu')]
        return q.edit_message_text(
            '📐 Ölçüm/kayıt alanları tamamlandı.' if fields else '📐 Bu kontrol föyünde ölçüm/kayıt alanı tanımlı değil.',
            reply_markup=kb([[('📊 Kontrol Sonucunu Aç', 'guide:result')] + back])
        )
    field = fields[idx]
    old = (context.user_data.get('guide_measurements') or {}).get(field)
    extra = f'\nMevcut değer: <b>{esc(old)}</b>' if old else ''
    q.edit_message_text(
        f'📐 <b>{esc(g["short_title"])} — ÖLÇÜM/KAYIT</b>\n\n'
        f'{idx+1}/{len(fields)} — <b>{esc(field)}</b>{extra}\n\n'
        'Değeri mesaj olarak yazın. Birim alan adında belirtilmemişse kısa açıklama da yazabilirsiniz.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([[('⏭️ Kontrol Edilmedi / Atla', 'guide:measure:skip')], [('📊 Sonuca Dön', 'guide:result')]]),
    )


def guide_measure_skip(q, context):
    g = guide_current(context)
    if not g:
        return q.answer('Aktif föy bulunamadı.', show_alert=True)
    idx = int(context.user_data.get('guide_measure_idx', 0))
    fields = g.get('measure_fields') or []
    if idx < len(fields):
        context.user_data.setdefault('guide_measurements', {})[fields[idx]] = 'Kontrol edilmedi'
    context.user_data['guide_measure_idx'] = idx + 1
    return guide_measure_prompt_q(q, context)


def guide_from_gear(q, context):
    gear = context.user_data.get('audit_gear')
    keys = GUIDE_GEAR_MAP.get(gear, [])
    if context.user_data.get('audit_activity') == 'amateur' and not keys:
        return guide_open(q, context, '14_Amator_Tekne')
    if not keys:
        return guide_menu(q, context)
    if len(keys) == 1:
        return guide_open(q, context, keys[0])
    rows = [[(f'🚤 {GUIDES[k]["short_title"][:35]}', f'guide:open:{k}')] for k in keys]
    rows.append([('↩️ Av Aracı Seçimine Dön', 'audit:gearmenu'), ('🏠 Ana Menü', 'menu')])
    q.edit_message_text(
        f'📋 <b>{esc(str(gear).title())} — HANGİ FAALİYET?</b>\n\n'
        'Bu av aracı birden fazla özel faaliyette kullanılabildiği için uygun kontrol föyünü seçin.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


AUDIT_STEPS = 7


def audit_breadcrumb(context):
    """Everything the guided audit has captured so far, one line per answer."""
    d = context.user_data
    parts = []
    if d.get('audit_region'):
        parts.append(f'📍 {esc(REGION_LABEL.get(d["audit_region"], d["audit_region"]))}')
    if d.get('audit_location'):
        parts.append(f'🗺️ {esc(d["audit_location"])}')
    if d.get('audit_activity'):
        line = '⚓ ' + esc(audit_activity_label(context))
        if d.get('audit_length_exact') is not None or d.get('audit_length_band') or d.get('audit_length') is not None:
            line += f' \u00b7 {esc(audit_length_label(context))}'
        parts.append(line)
    if d.get('audit_date'):
        parts.append('\U0001f4c5 ' + audit_date(context).strftime('%d.%m.%Y'))
    if d.get('audit_subject'):
        parts.append(f'\U0001f3af {esc(SUBJECT_LABEL.get(d["audit_subject"], d["audit_subject"]))}')
    if d.get('audit_gear'):
        parts.append(f'\U0001fa9d {esc(d["audit_gear"])}')
    return '\n'.join(parts)


def audit_step(context, n):
    """Header for step n: title, progress bar and the answers so far."""
    out = '\U0001f6a8 <b>YEN\u0130 DENET\u0130M</b>\n' + progress_bar(n, AUDIT_STEPS) + '\n'
    crumbs = audit_breadcrumb(context)
    if crumbs:
        out += HR + '\n' + crumbs + '\n'
    return out + HR + '\n\n'


def audit_start(q, context):
    context.user_data.clear()
    context.user_data['guided_active'] = True
    db.log(q.from_user.id, 'audit_start')
    q.edit_message_text(
        audit_step(context, 1) +
        'Önce <b>denetim alanını</b> seçin. Sonraki sorular alanın mevzuat kapsamına göre daraltılacaktır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('🌊 Karadeniz', 'audit:region:karadeniz'), ('🌊 Marmara', 'audit:region:marmara')],
            [('🌉 İstanbul Boğazı', 'audit:region:istanbul'), ('🌉 Çanakkale Boğazı', 'audit:region:canakkale')],
            [('🌊 Ege', 'audit:region:ege'), ('🌊 Akdeniz', 'audit:region:akdeniz')],
            [('🧭 Uluslararası / MEB', 'audit:region:international')],
            [('🏞️ İçsu', 'audit:region:inland'), ('🪸 Dalyan / Lagün', 'audit:region:lagoon')],
            [('🏭 İşleme / Yetiştiricilik Tesisi', 'audit:region:facility')],
            [('↩️ Ana Menü', 'menu')],
        ]),
    )


def audit_choose_activity(q, context):
    if context.user_data.get('audit_region') == 'facility':
        choices = [
            [('🏭 İşleme / Değerlendirme', 'audit:activity:processing')],
            [('🧪 Yetiştiricilik / Ürün Sağlığı', 'audit:activity:aquaculture')],
        ]
    else:
        choices = [[('🚤 Ticari avcılık', 'audit:activity:commercial'), ('🎣 Amatör avcılık', 'audit:activity:amateur')]]
    q.edit_message_text(
        audit_step(context, 2) +
        'Kontrol edilen faaliyet hangi kapsamda?',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(choices + [[('↩️ Alanı Değiştir', 'audit:start'), ('🏠 Ana Menü', 'menu')]]),
    )


def audit_choose_length(q, context):
    q.edit_message_text(
        audit_step(context, 3) +
        'Gemi/tekne durumunu seçin. Boy grubu; BAGİS, donanım ve yaptırım değerlendirmesinde kullanılacaktır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('⚓ Gemi/Tekne yok', 'audit:length:none')],
            [('🚤 12 m altı', 'audit:length:lt12'), ('🚢 12–22 m altı', 'audit:length:12to22')],
            [('🛳 22 m ve üzeri', 'audit:length:ge22')],
            [('✍️ Tam boyu yaz', 'audit:length:exact')],
            [('↩️ Faaliyeti Değiştir', f'audit:region:{context.user_data.get("audit_region")}'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


def audit_choose_date(q, context):
    q.edit_message_text(
        audit_step(context, 4) +
        'Olay veya kontrol tarihi nedir? Tarih; kapalı dönem ve tür zaman yasaklarının değerlendirilmesinde kullanılır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('📅 Bugün', 'audit:date:today'), ('🗓 Başka tarih', 'audit:date:other')],
            [('↩️ Faaliyeti Değiştir', 'audit:activitymenu'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


def audit_choose_subject(q, context):
    remember_draft(q, context, 'audit')
    activity = context.user_data.get('audit_activity')
    text = (
        audit_step(context, 5) +
        '<b>Denetimin ana konusu nedir?</b> Bundan sonra yalnız ilgili ayrıntılar sorulacaktır.'
    )
    if activity == 'commercial':
        if audit_rule_length(context) > 0:
            rows = [
                [('🎣 Avcılık faaliyeti', 'audit:subject:fishing'), ('🚤 Gemi / Ruhsat / Donanım', 'audit:subject:vessel')],
                [('🐟 Ürün / Tür', 'audit:subject:species'), ('📦 Nakil / Satış', 'audit:subject:transport')],
            ]
        else:
            rows = [
                [('🎣 Avcılık faaliyeti', 'audit:subject:fishing'), ('🐟 Ürün / Tür', 'audit:subject:species')],
                [('📦 Nakil / Satış', 'audit:subject:transport')],
            ]
    elif activity == 'amateur':
        rows = [
            [('🎣 Avcılık faaliyeti', 'audit:subject:fishing'), ('🐟 Ürün / Tür', 'audit:subject:species')],
            [('📦 Satış / Nakil', 'audit:subject:transport'), ('🔎 Ticari Nitelik Kontrolü', 'classify:start')],
        ]
    else:
        rows = [
            [('🏭 Tesis İzin / Şartları', 'audit:subject:facility'), ('🧪 Sağlık / Kalite', 'audit:subject:health')],
            [('📦 Ambalaj / Nakliye', 'audit:subject:transport'), ('🌱 Atık / Çevre', 'audit:subject:environment')],
        ]
    rows += [[('↩️ Tarihi Değiştir', 'audit:datemenu'), ('🏠 Ana Menü', 'menu')]]
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def audit_choose_gear(q, context):
    activity = context.user_data.get('audit_activity')
    inland = context.user_data.get('audit_region') == 'inland'
    lagoon = context.user_data.get('audit_region') == 'lagoon'
    if activity == 'commercial' and inland:
        rows = [
            [('Uzatma ağı', 'audit:gear:uzatma ağı'), ('Parakete', 'audit:gear:parakete')],
            [('Serpme ağ', 'audit:gear:serpme'), ('Sepet / Pinter', 'audit:gear:sepet / pinter')],
            [('Gırgır', 'audit:gear:gırgır'), ('Trol', 'audit:gear:dip trolü')],
            [('Iğrıp / Manyat', 'audit:gear:manyat'), ('Diğer', 'audit:gear:diğer')],
        ]
    elif activity == 'commercial':
        rows = [
            [('Gırgır', 'audit:gear:gırgır'), ('Dip trolü', 'audit:gear:dip trolü')],
            [('Ortasu trolü', 'audit:gear:ortasu trolü'), ('Algarna', 'audit:gear:algarna')],
            [('Manyat', 'audit:gear:manyat'), ('Dreç', 'audit:gear:dreç')],
            [('Uzatma ağı', 'audit:gear:uzatma ağı'), ('Parakete', 'audit:gear:parakete')],
            [('Işıkla avcılık', 'audit:gear:ışık'), ('Dalma / Sualtı', 'audit:gear:dalma')],
            [('Deniz Patlıcanı', 'audit:gear:deniz patlıcanı'), ('Sünger / Kestane', 'audit:gear:denizkestanesi')],
            [('Monofilament', 'audit:gear:monofilament'), ('Olta / Çapari / Diğer', 'audit:gear:diğer')],
        ]
        if lagoon:
            rows.insert(0, [('Dalyan / Lagün', 'audit:gear:dalyan / lagün')])
    else:
        if inland:
            rows = [
                [('Olta / Çapari', 'audit:gear:olta'), ('Yemlik uzatma ağı', 'audit:gear:yemlik uzatma ağı')],
                [('Tırıvırı / Ağ', 'audit:gear:tırıvırı'), ('Parakete', 'audit:gear:parakete')],
                [('Sepet / Pinter', 'audit:gear:sepet / pinter'), ('Serpme ağ', 'audit:gear:serpme')],
                [('Sualtı tüfeği / Zıpkın', 'audit:gear:dalma'), ('Diğer', 'audit:gear:diğer')],
            ]
        else:
            rows = [
                [('Olta / Çapari', 'audit:gear:olta'), ('Yemlik uzatma ağı', 'audit:gear:yemlik uzatma ağı')],
                [('Sualtı tüfeği / Dalma', 'audit:gear:dalma'), ('Parakete', 'audit:gear:parakete')],
                [('Turizm (Ek-9)', 'audit:gear:turizm'), ('Tırıvırı / Paraşüt', 'audit:gear:tırıvırı')],
                [('Serpme ağ', 'audit:gear:serpme'), ('Sepet / Pinter', 'audit:gear:sepet / pinter')],
                [('Diğer', 'audit:gear:diğer')],
            ]
    rows += [[('↩️ Konuyu Değiştir', 'audit:subjectmenu'), ('🏠 Ana Menü', 'menu')]]
    q.edit_message_text(
        audit_step(context, 6) +
        'Kullanılan veya kontrol edilen <b>av aracı / yöntemi</b> seçin.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


def audit_after_gear(q, context):
    remember_draft(q, context, 'audit')
    flags = build_context_flags(context)
    warning = ''
    if flags:
        warning = '\n\n' + '\n'.join(f'🔴 {esc(x["tag"])}' for x in flags[:3])
    q.edit_message_text(
        audit_step(context, 7) +
        f'Kontrol edilen ürün/tür belli mi?{warning}',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('🐟 Türü seç / yaz', 'audit:guided:species')],
            [('➡️ Tür belirtmeden devam', 'audit:guided:check')],
            [('📋 Bu Av Aracının Kontrol Föyü', 'guide:fromgear')],
            [('↩️ Av Aracını Değiştir', 'audit:gearmenu'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


def audit_hub_edit(q, context):
    remember_draft(q, context, 'audit')
    activity = context.user_data.get('audit_activity')
    gear = context.user_data.get('audit_gear')
    species = context.user_data.get('audit_species_name')
    subject = context.user_data.get('audit_subject')
    text = (
        '🚨 <b>DENETİM BAĞLAMI</b>\n\n'
        f'📍 Alan: <b>{esc(REGION_LABEL.get(context.user_data.get("audit_region"), "—"))}</b>\n'
        f'⚓ Faaliyet: <b>{esc(audit_activity_label(context))}</b>\n'
        f'📅 Tarih: <b>{audit_date(context).strftime("%d.%m.%Y")}</b>\n'
    )
    if activity in {'commercial', 'amateur'}:
        text += f'🚤 Gemi/Tekne: <b>{esc(audit_length_label(context))}</b>\n'
    if context.user_data.get('audit_location'):
        text += f'🗺️ Konum: <b>{esc(context.user_data["audit_location"])}</b>\n'
    if subject:
        text += f'🎯 Konu: <b>{esc(SUBJECT_LABEL.get(subject, subject))}</b>\n'
    if gear:
        text += f'🎣 Av aracı: <b>{esc(gear)}</b>\n'
    if species:
        text += f'🐟 Tür: <b>{esc(species)}</b>\n'
    rows = [[('✅ Duruma Özel Kontrole Devam', 'audit:guided:check')]]
    if activity == 'amateur':
        rows.append([('🔎 Amatör → Ticari Nitelik', 'classify:start')])
    rows += [[('🏠 Ana Menü', 'menu')]]
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def _q(text, expected, ref, tag, *, procedure=False, penalty_query=None):
    item = {'q': text, 'expected': expected, 'ref': ref, 'tag': tag}
    if procedure:
        item['procedure'] = True
    if penalty_query:
        item['penalty_query'] = penalty_query
    return item


def build_context_flags(context):
    activity = context.user_data.get('audit_activity')
    region = context.user_data.get('audit_region')
    gear = context.user_data.get('audit_gear')
    length = audit_rule_length(context)
    day = audit_date(context)
    flags = []

    def add(tag, ref, penalty_query=None):
        key = (tag, ref)
        if any((x['tag'], x['ref']) == key for x in flags):
            return
        flags.append({'tag': tag, 'ref': ref, 'penalty_query': penalty_query})

    if activity == 'commercial':
        if region == 'inland' and gear in {'gırgır', 'dip trolü', 'ortasu trolü'}:
            add('İçsularda trol ve gırgır ağı kullanımı tamamen yasaktır', ('61', 51), 'içsularda trol gırgır')
        if gear == 'ışık' and region in {'karadeniz', 'marmara', 'istanbul', 'canakkale'}:
            add('Seçilen bölgede ışıkla avcılık yasağı', ('61', 13), 'ışık ile avcılık')
        if gear in {'dip trolü', 'ortasu trolü'} and region in {'marmara', 'istanbul', 'canakkale'}:
            add('Seçilen bölgede trol yasağı', ('61', 9), 'Marmara Denizi ve boğazlarda trol avcılığı')
        if gear == 'algarna' and region in {'ege', 'akdeniz'}:
            add('Seçilen bölgede algarna kullanımı yasağı', ('61', 14), 'algarna')
        if gear == 'gırgır' and 0 < length < 12:
            add('12 metreden küçük gemi ile gırgır avcılığı', ('61', 50), '12 metreden küçük tekne ile gırgır avcılığı')
        if gear == 'gırgır' and region in {'karadeniz', 'marmara', 'istanbul', 'canakkale', 'ege', 'akdeniz'}:
            span = '04-15/09-15' if region == 'akdeniz' else '04-15/08-31'
            if in_date_range(day, span):
                add(f'{day.strftime("%d.%m.%Y")} tarihinde genel gırgır kapalı dönemi', ('61', 12), 'yasak zamanda gırgır ağları ile istihsal yapmak')
    elif activity == 'amateur':
        if region == 'inland' and gear in {'parakete', 'tırıvırı', 'sepet / pinter', 'serpme', 'dalma'}:
            add('Seçilen av aracı amatör içsu avcılığında yasaktır', ('62', 12), 'amatör içsu av aracı')
        elif gear == 'parakete':
            add('Denizlerde amatör avcılıkta parakete kullanımı', ('62', 16), 'amatör avcılık kurallarının ihlali')
        if gear == 'tırıvırı' and region != 'inland':
            add('Tırıvırı / paraşüt kullanımı', ('62', 8), 'amatör avcılık kurallarının ihlali')

    sid = context.user_data.get('audit_species_id')
    skind = context.user_data.get('audit_species_kind')
    if sid and skind in {'commercial', 'amateur'}:
        row = db.get_species(skind, int(sid))
        if row:
            bans = json.loads(row['time_bans'] or '[]')
            if bans and any(in_date_range(day, span) for span in bans):
                ref = (('61', int(row['article_time'] or row['article_size'])) if skind == 'commercial'
                       else ('62', int(row['article'])))
                pq = 'yasak zamanda avcılık' if skind == 'commercial' else 'amatör avcılık kurallarının ihlali'
                add(f'{row["name"]}: seçilen tarih zaman yasağına denk geliyor', ref, pq)
    return flags


def build_quick_questions(context):
    activity = context.user_data.get('audit_activity')
    subject = context.user_data.get('audit_subject') or 'fishing'
    region = context.user_data.get('audit_region')
    length = audit_rule_length(context)
    gear = context.user_data.get('audit_gear')
    day = audit_date(context)
    qs = []

    # Tesis/sağlık denetimleri gemi ve av aracı sorularından bağımsızdır.
    if activity in {'processing', 'aquaculture'}:
        if subject == 'facility':
            qs += [
                _q('Tesisin çalışma izni, üretim/işleme izni ve faaliyet kapsamı güncel ve yapılan işle uyumlu mu?', 'yes', ('reg', 25), 'Tesis izinleri'),
                _q('Tesis, alet-ekipman ve personel için genel hijyen şartları sağlanıyor mu?', 'yes', ('reg', 26), 'Genel hijyen'),
                _q('Yetkili kontrol görevlilerinin tesise, ürünlere ve ilgili belgelere erişimi sağlanıyor mu?', 'yes', ('reg', 33), 'Kontrole erişim'),
            ]
        elif subject == 'health':
            qs += [
                _q('Hastalık şüphesi, karantina ve bildirim yükümlülükleri yönünden gerekli tedbirler alınmış mı?', 'yes', ('reg', 21), 'Hastalık / karantina'),
                _q('İthalat, ihracat veya sevke konu ürünlerde sağlık belgesi ve sağlık şartları uygun mu?', 'yes', ('reg', 22), 'Sağlık belgesi'),
                _q('Damızlık, yumurta ve yavrular için gerekli belge ve sağlık şartları uygun mu?', 'yes', ('reg', 23), 'Damızlık belgesi'),
                _q('Koruyucu veya tedavi edici maddeler izinli, kayıtlı ve kullanım şartlarına uygun mu?', 'yes', ('reg', 24), 'Koruyucu / tedavi edici maddeler'),
            ]
            if activity == 'processing':
                qs.append(_q('İşleme, muhafaza ve ürün kabul süreçleri ürün güvenliği şartlarına uygun mu?', 'yes', ('reg', 27), 'İşleme ve ürün güvenliği'))
        elif subject == 'transport':
            qs.append(_q('Ürün; ambalajlama, etiketleme, muhafaza, soğuk zincir ve taşıma şartlarına uygun mu?', 'yes', ('reg', 32), 'Muhafaza / nakil şartları', penalty_query='nakil belgesi'))
        elif subject == 'environment':
            qs += [
                _q('Tesisten alıcı ortama arıtılmamış atık, ölü ürün veya çevreye zarar verecek madde bırakılmıyor mu?', 'yes', ('reg', 11), 'Atık ve çevre koruma'),
                _q('Atıkların uzaklaştırılması ve varsa arıtma sistemi kayıtlı, çalışır ve uygun durumda mı?', 'yes', ('reg', 12), 'Atık yönetimi'),
            ]

    # Önce genel hukuki/gemi unsurları, sonra faaliyete özgü ayrıntılar.
    if activity == 'commercial' and subject == 'fishing':
        qs.append(_q('Ticari avcılığı yapan kişi/tüzel kişi için gerekli ruhsat veya izin mevcut ve gerektiğinde ibraz ediliyor mu?', 'yes', ('law', 3), 'Kişi / faaliyet ruhsatı', penalty_query='ruhsatsız avcılık'))

    if activity == 'commercial' and subject in {'fishing', 'vessel'} and length > 0:
        qs += [
            _q('Gemi için gerekli ruhsat tezkeresi/izin mevcut ve talep edildiğinde ibraz edildi mi?', 'yes', ('law', 3), 'Gemi ruhsatı / izin', penalty_query='ruhsatsız gemi'),
            _q('Gemi ruhsat kodu/plakası uygun ve görünür durumda mı?', 'yes', ('reg', 5), 'Ruhsat kodu / plaka'),
            _q('Gemideki personelin ruhsat durumu uygun mu; ruhsatsız yardımcı varsa 16–18 yaş ve toplam çalışanların %20 sınırı içinde mi?', 'yes', ('reg', 4), 'Personel ruhsatı'),
        ]
        if length >= 22:
            qs.append(_q('22 m ve üzeri gemide Yönetmelikte aranan zorunlu donanım ve muhafaza şartları uygun mu?', 'yes', ('reg', 13), '22 m+ zorunlu donanım'))
        if 0 < length < 12:
            qs.append(_q('12 m altı gemide özel izin istisnası dışında vinç, çelik halat, bom, matafora veya bunlara uyarlanmış/modifiye donanım bulunmuyor mu?', 'yes', ('61', 50), '12 m altı özel donanım'))
        if length >= 12:
            qs += [
                _q('BAGİS cihazı takılı, çalışır ve işler durumda mı?', 'yes', ('bagis', 5), 'BAGİS', penalty_query='BAGİS'),
                _q('E-seyir defteri ve zorunlu av kayıtları uygun şekilde tutuluyor mu?', 'yes', ('61', 49), 'E-seyir'),
            ]
        if subject == 'fishing':
            qs += [
                _q('Kullanılan/bulundurulan av aracı markalı, kayıtlı ve gerekli işaretleri taşıyor mu?', 'yes', ('61', 49), 'Av aracı markalama'),
                _q('Kullanılan av aracı ruhsattaki birincil av aracıyla uyumlu mu?', 'yes', ('61', 50), 'Birincil av aracı'),
            ]

    if subject == 'fishing':
        if activity == 'commercial':
            if region == 'inland':
                qs += [
                    _q('Avcılık, kiralanmış/izin verilmiş istihsal sahasında ve ruhsatlı araçlarla mı yapılıyor?', 'yes', ('61', 51), 'İçsu sahası / ruhsat'),
                    _q('Avcılık yapılan içsu tamamen veya kısmen yasaklanan alanlar dışında mı?', 'yes', ('61', 35), 'Yasaklanan içsular'),
                    _q('İl, tür ve bölge için ilan edilen zaman yasağına uyuluyor mu?', 'yes', ('61', 37), 'İçsu zaman yasağı'),
                    _q('Kullanılan av aracının göz açıklığı, boyu, sayısı ve diğer teknik şartları içsu kurallarına uygun mu?', 'yes', ('61', 51), 'İçsu av aracı şartları'),
                ]
            elif region == 'lagoon':
                qs += [
                    _q('Dalyan açıklıkları toplam açıklığın en az %10’u ve her biri en az 3 metre olacak şekilde açık mı?', 'yes', ('61', 34), 'Dalyan açıklıkları'),
                    _q('Dalyan kuzulukları, ışıkla avcılık, zıpkın ve yeni ağ kullanımına ilişkin özel şartlara uyuluyor mu?', 'yes', ('61', 34), 'Dalyan / lagün özel şartları'),
                ]
            else:
                qs += [
                _q('Seçilen av aracının yer, saha, mesafe, derinlik ve saat şartlarının tamamı uygun mu?', 'yes', ('61', 50), 'Yer / saha / mesafe / derinlik'),
                _q('Yasak dönem nedeniyle gemide veya istihsal yerinde bulundurulması yasak bir av aracı bulunmuyor mu?', 'yes', ('61', 50), 'Yasak av aracı bulundurma'),
                ]
            if region != 'inland' and gear == 'gırgır':
                qs += [
                    _q('Gırgır için asgari su derinliği ve ağ derinliği şartları uygun mu?', 'yes', ('61', 12), 'Gırgır derinlik şartları', penalty_query='gırgır'),
                    _q('Gırgır ağı için gerekli Ağ Ölçüm Belgesi mevcut ve geçerli mi?', 'yes', ('61', 12), 'Ağ Ölçüm Belgesi', penalty_query='gırgır ağı ölçüm belgesi'),
                ]
            elif region != 'inland' and gear in {'dip trolü', 'ortasu trolü'}:
                qs.append(_q('Trol faaliyeti saha, zaman, kıyı mesafesi/derinlik, ağ gözü ve diğer teknik şartlara uygun mu?', 'yes', ('61', 10 if gear == 'dip trolü' else 11), 'Trol teknik/saha şartları', penalty_query='trol'))
            elif region != 'inland' and gear == 'ışık':
                qs.append(_q('Işıkla avcılık izin, güç, derinlik, yetiştiricilik tesisi mesafesi ve diğer özel şartlara uygun mu?', 'yes', ('61', 13), 'Işıkla avcılık şartları', penalty_query='ışık ile avcılık'))
            elif region != 'inland' and gear == 'algarna':
                qs.append(_q('Algarna faaliyeti hedef tür, izin, saat, saha ve teknik ölçü şartlarına uygun mu?', 'yes', ('61', 14), 'Algarna şartları', penalty_query='algarna'))
            elif region != 'inland' and gear == 'parakete':
                qs.append(_q('Parakete işaretleme ve iğne şartları uygun mu; hedef tür kalkan ise parakete kullanılmıyor mu?', 'yes', ('61', 15), 'Parakete şartları', penalty_query='parakete'))
            if region != 'inland' and gear in {'algarna', 'manyat', 'dreç', 'dalma'} and day >= datetime(2026, 9, 1, tzinfo=TZ).date():
                qs.append(_q('Bu faaliyet için 1 Eylül 2026 itibarıyla istenen gemi izleme/kayıt cihazı işler ve çalışır durumda mı?', 'yes', ('61', 50), 'İzleme / kayıt cihazı'))
        elif activity == 'amateur':
            if region == 'inland':
                qs += [
                    _q('Olta sayısı, iğne sayısı, tekne boyu ve kullanılan diğer araçlar içsu amatör avcılık sınırlarına uygun mu?', 'yes', ('62', 12), 'İçsu amatör av aracı', penalty_query='amatör avcılık kurallarının ihlali'),
                    _q('Avcılık yapılan içsu tamamen/kısmen yasaklanan alanların dışında ve bölgesel zaman yasağına uygun mu?', 'yes', ('62', 11), 'İçsu yer / zaman yasağı', penalty_query='amatör avcılık kurallarının ihlali'),
                ]
            else:
                qs += [
                    _q('Kullanılan av aracı/yöntem denizlerde amatör avcılık için izin verilen araç ve yöntemlere uygun mu?', 'yes', ('62', 16), 'Amatör av aracı', penalty_query='amatör avcılık kurallarının ihlali'),
                    _q('Avcılık yapılan saha; yüzme alanı, yetiştiricilik tesisi ve diğer yer sınırlamalarına uygun mu?', 'yes', ('62', 17), 'Amatör yer yasağı', penalty_query='amatör avcılık kurallarının ihlali'),
                ]
                if region == 'lagoon':
                    qs.append(_q('Dalyan/lagün açıklıkları ve özel avcılık sınırlamalarına uyuluyor mu?', 'yes', ('61', 34), 'Dalyan / lagün şartları'))

    if subject in {'fishing', 'species'}:
        if activity == 'commercial' and region == 'inland':
            qs += [
                _q('Avlanan/tespit edilen içsu ürününün asgari boy veya ağırlık şartı uygun mu?', 'yes', ('61', 38), 'İçsu ürün boy / ağırlık', penalty_query='yasak boyda su ürünü'),
                _q('Türe özgü kota, adet, izin ve özel içsu avcılığı şartları uygun mu?', 'yes', ('61', 39), 'İçsu tür özel şartları'),
            ]
        elif activity == 'commercial':
            qs += [
                _q('Avlanan/tespit edilen ürünün asgari boy veya ağırlık şartı uygun mu?', 'yes', ('61', 17), 'Ürün boy / ağırlık', penalty_query='yasak boyda su ürünü'),
                _q('Türün kota, tolerans, izin ve varsa özel avcılık şartları uygun mu?', 'yes', ('61', 18), 'Kota / tolerans / özel izin'),
            ]
        elif activity == 'amateur' and region == 'inland':
            qs += [
                _q('Avlanan/tespit edilen içsu ürününün bölgesel asgari boy şartı uygun mu?', 'yes', ('62', 11), 'İçsu amatör asgari boy', penalty_query='amatör avcılık kurallarının ihlali'),
                _q('Alıkonulan içsu ürünü miktarı bölgesel adet/kg sınırları içinde mi?', 'yes', ('62', 11), 'İçsu amatör miktar', penalty_query='amatör avcılık kurallarının ihlali'),
            ]
        elif activity == 'amateur':
            qs += [
                _q('Avlanan/tespit edilen ürünün asgari boy şartı uygun mu?', 'yes', ('62', 15), 'Amatör asgari boy', penalty_query='amatör avcılık kurallarının ihlali'),
                _q('Alıkonulan ürün miktarı adet/kg sınırları içinde mi?', 'yes', ('62', 15), 'Amatör alıkonulabilir miktar', penalty_query='amatör avcılık kurallarının ihlali'),
            ]

    if subject == 'transport':
        if activity in {'processing', 'aquaculture'}:
            # Tesis nakil sorusu yukarıdaki tesis dalında eklendi.
            pass
        elif activity == 'commercial' and region == 'inland':
            qs += [
                _q('Canlı içsu ürünlerinin nakli, stoklanması ve başka su kaynağına bırakılması gerekli izin ve şartlara uygun mu?', 'yes', ('61', 51), 'İçsu canlı nakli / stoklama', penalty_query='nakil belgesi'),
                _q('Ürün yasak tür, yasak boy, yasak zaman veya mevzuata aykırı avcılıktan elde edilmiş ürün niteliğinde değil mi?', 'yes', ('law', 25), 'Yasak ürünün nakli / satışı', penalty_query='nakleden satan'),
            ]
        elif activity == 'commercial':
            qs += [
                _q('Nakil/Menşe veya somut sevk için gerekli diğer belge mevcut ve uygun mu?', 'yes', ('61', 46), 'Nakil / Menşe belgesi', penalty_query='nakil belgesi'),
                _q('Ürün yasak tür, yasak boy, yasak zaman veya mevzuata aykırı avcılıktan elde edilmiş ürün niteliğinde değil mi?', 'yes', ('law', 25), 'Yasak ürünün nakli / satışı', penalty_query='nakleden satan'),
                _q('Ürün Bakanlıkça belirlenen karaya çıkış noktası zorunluluğuna tabi ise uygun noktadan boşaltıldı mı?', 'yes', ('law', 36), 'Karaya çıkış noktası', penalty_query='karaya çıkış noktası'),
            ]
        else:
            qs.append(_q('Amatör avcılıkla elde edilen ürün satılmıyor, canlı nakledilmiyor ve başka kaynağa bırakılmıyor mu?', 'yes', ('62', 8), 'Amatör ürün satışı / canlı nakli', penalty_query='amatör avcılık kurallarının ihlali'))

    qs.append(_q('Tespit açısından mümkün olan fotoğraf, video, konum/koordinat, ölçüm veya diğer teknik deliller kayda alındı mı?', 'yes', ('reg', 37), 'Delillendirme', procedure=True))
    return qs


def audit_quick_start(q, context):
    questions = build_quick_questions(context)
    context.user_data['quick_questions'] = questions
    context.user_data['quick_answers'] = []
    context.user_data['context_flags'] = build_context_flags(context)
    return audit_quick_render(q, context, 0)


def audit_quick_render(q, context, idx):
    qs = context.user_data.get('quick_questions') or []
    if idx >= len(qs):
        return audit_quick_finish(q, context)
    item = qs[idx]
    subject = SUBJECT_LABEL.get(context.user_data.get('audit_subject'), 'Denetim')
    text = (
        f'{header("🛡️", "DURUMA ÖZEL DENETİM", subject)}\n'
        f'{progress_bar(idx + 1, len(qs))}\n'
        f'{HR}\n\n'
        f'<b>{esc(item["q"])}</b>\n\n'
        f'{HR}\n'
        '<i>“Bilinmiyor” seçeneği ihlal kararı üretmez; kontrol edilmesi gereken eksik unsur olarak sonuçta gösterilir.</i>'
    )
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb([
        [('✅ Evet', f'audit:quick:ans:{idx}:yes'), ('❌ Hayır', f'audit:quick:ans:{idx}:no')],
        [('❔ Bilinmiyor / Kontrol Edilmedi', f'audit:quick:ans:{idx}:unknown')],
        [('📚 İlgili Madde', f'art:{item["ref"][0]}:{item["ref"][1]}'), ('🏠 Ana Menü', 'menu')],
    ]))


def audit_quick_answer(q, context, idx, ans):
    qs = context.user_data.get('quick_questions') or []
    if idx >= len(qs):
        return q.answer('Kontrol oturumu bulunamadı.', show_alert=True)
    answers = context.user_data.setdefault('quick_answers', [])
    while len(answers) <= idx:
        answers.append(None)
    answers[idx] = ans
    return audit_quick_render(q, context, idx + 1)


def quick_result_parts(context):
    """Partition the guided-audit answers into the buckets both the result
    screen and the legal-assessment scenario need."""
    qs = context.user_data.get('quick_questions') or []
    answers = context.user_data.get('quick_answers') or []
    flags = context.user_data.get('context_flags') or build_context_flags(context)
    possible, unknown, procedure = [], [], []
    for i, item in enumerate(qs):
        ans = answers[i] if i < len(answers) else 'unknown'
        if ans == 'unknown':
            unknown.append(item)
        elif item.get('procedure'):
            if ans != item['expected']:
                procedure.append(item)
        elif ans != item['expected']:
            possible.append(item)
    return flags, possible, unknown, procedure


def ai_scenario_from_context(context):
    """Turn whatever the inspector has already entered into the plain-text
    scenario the legal assessment expects.

    Written straight from context.user_data rather than per-screen, so the
    same button works from the kontrol föyü result, the guided audit result,
    the ticari-nitelik screen and the av aracı screen — each one simply
    contributes the parts it has filled in. Returns None when nothing has
    been entered yet, so the caller can say so instead of asking the model
    about an empty inspection.
    """
    d = context.user_data
    facts, findings, missing = [], [], []

    if d.get('audit_region'):
        facts.append('Bölge: ' + str(REGION_LABEL.get(d['audit_region'], d['audit_region'])))
    if d.get('audit_location'):
        facts.append('İl / su kaynağı / tesis: ' + str(d['audit_location']))
    if d.get('audit_activity'):
        facts.append('Faaliyet: ' + audit_activity_label(context))
    if d.get('audit_length_exact') is not None or d.get('audit_length_band') or d.get('audit_length') is not None:
        facts.append('Gemi/tekne: ' + audit_length_label(context))
    if d.get('audit_date'):
        facts.append('Kontrol tarihi: ' + audit_date(context).strftime('%d.%m.%Y'))
    if d.get('audit_subject'):
        facts.append('Denetim konusu: ' + str(SUBJECT_LABEL.get(d['audit_subject'], d['audit_subject'])))
    if d.get('audit_gear'):
        facts.append('Kullanılan av aracı: ' + str(d['audit_gear']))
    if d.get('audit_species_name'):
        facts.append('Kontrol edilen tür: ' + str(d['audit_species_name']))

    # Kontrol föyü (tekne türü kılavuzu)
    g, _ok, bad, unchecked = guide_result_parts(context)
    if g:
        facts.append('Uygulanan kontrol föyü: ' + g['short_title'])
        for _idx, item in bad:
            findings.append(f"{item['text']} (dayanak: {guide_ref_label(item['ref'])})")
        for _idx, item in unchecked:
            missing.append(item['text'])
        for name, value in (d.get('guide_measurements') or {}).items():
            facts.append(f'Ölçüm/kayıt — {name}: {value}')

    # Yönlendirilmiş denetim: the tag alone is too terse to reason from, so
    # each question goes in with the answer that was actually given.
    if d.get('quick_questions'):
        flags, possible, unknown, procedure = quick_result_parts(context)
        for item in flags:
            findings.append(f"{item['tag']} — seçilen bilgilerden doğrudan çıkan mevzuat "
                            f"uyarısı (dayanak: {guide_ref_label(item['ref'])})")
        answer_label = {'yes': 'Evet', 'no': 'Hayır', 'unknown': 'Bilinmiyor'}
        given = d.get('quick_answers') or []
        for i, item in enumerate(d['quick_questions']):
            ans = given[i] if i < len(given) else 'unknown'
            line = (f"{item['q']} → Cevap: {answer_label.get(ans, ans)} "
                    f"(dayanak: {guide_ref_label(item['ref'])})")
            if item in possible:
                findings.append(line + ' — olası aykırılık')
            elif item in procedure:
                findings.append(line + ' — delil/işlem eksiği')
            elif item in unknown:
                missing.append(line)

    # Amatör → ticari nitelik değerlendirmesi
    answers = d.get('classify_answers') or []
    for i, ans in enumerate(answers):
        if i >= len(CLASSIFICATION_QUESTIONS):
            break
        if ans == 'yes':
            findings.append('6/2 Tebliğ Md.19/1 ölçütü gerçekleşti: ' + CLASSIFICATION_QUESTIONS[i])
        elif ans in {None, 'unknown'}:
            missing.append(CLASSIFICATION_QUESTIONS[i])

    if not facts and not findings:
        return None

    parts = ['Deniz, içsu, dalyan/lagün veya tesis kapsamında yapılan bir su ürünleri denetimidir.']
    if facts:
        parts.append('DENETİM BİLGİLERİ\n' + '\n'.join('- ' + f for f in facts))
    if findings:
        parts.append('DENETİMDE TESPİT EDİLEN / İŞARETLENEN HUSUSLAR\n'
                     + '\n'.join('- ' + f for f in findings))
    else:
        parts.append('DENETİMDE TESPİT EDİLEN / İŞARETLENEN HUSUSLAR\n'
                     '- Bu akışta doğrudan bir aykırılık işaretlenmedi.')
    if missing:
        parts.append('KONTROL EDİLEMEYEN / BİLİNMEYEN UNSURLAR\n'
                     + '\n'.join('- ' + m for m in missing))
    parts.append(
        'Yukarıdaki denetimi mevzuat karşısında değerlendir. Tespit edilen her husus için '
        'hangi hükmün ihlal edildiğini ve uygulanacak idari yaptırımı belirt. Kontrol '
        'edilemeyen unsurlardan hangilerinin sonucu değiştirebileceğini de kısaca yaz.'
    )
    return '\n\n'.join(parts)


def ai_run(context, chat_id, uid, scenario, show_first, log_action='ai_analysis'):
    """The legal-assessment pipeline, shared by the free-text question and the
    "bu denetimi değerlendir" button.

    show_first renders the first message of the flow, because the two entry
    points differ there: the text path goes through send_or_edit so the
    inspector's typed question is removed from the chat, while the button
    path just edits the screen that is already on show.
    """
    wait_left = ai_rate_limit_remaining(uid)
    if wait_left > 0:
        return show_first(
            header('⚖️', 'HUKUKİ DEĞERLENDİRME') + '\n' + HR + '\n\n'
            + badge('warn', 'Kotanız doldu', f'Lütfen {wait_left} saniye sonra tekrar deneyin.'),
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('🏠 Ana Menü', 'menu')]]),
        )
    ai_rate_limit_mark(uid)

    db.log(uid, log_action, scenario[:120])
    show_first(
        header('⚖️', 'HUKUKİ DEĞERLENDİRME', 'Markdown belgeleri taranıyor, 20-45 sn sürebilir…'),
        parse_mode=ParseMode.HTML,
    )
    try:
        _, html_text = ai_analyze(scenario)
    except AIError as e:
        fail = (header('⚖️', 'HUKUKİ DEĞERLENDİRME') + '\n' + HR + '\n\n'
                + badge('stop', 'Tamamlanamadı', esc(str(e))))
        return ai_show(context, chat_id, fail, parse_mode=ParseMode.HTML,
                             reply_markup=kb([[('🔁 Tekrar Dene', 'ai:start')],
                                              [('🏠 Ana Menü', 'menu')]]))
    body = header('⚖️', 'HUKUKİ DEĞERLENDİRME') + '\n' + HR + '\n\n' + html_text
    tail_rows = [[('🔁 Yeni Değerlendirme', 'ai:start'), ('🏠 Ana Menü', 'menu')]]
    ai_show(context, chat_id, body, parse_mode=ParseMode.HTML, reply_markup=kb(tail_rows))


def ai_audit_preview(q, context):
    """Show what would be sent for the current inspection, then let the
    inspector confirm. The preview matters because the assessment is
    rate-limited: it should be obvious what the one request will ask."""
    scenario = ai_scenario_from_context(context)
    if not scenario:
        return q.answer('Değerlendirilecek denetim bilgisi bulunamadı.', show_alert=True)
    context.user_data['ai_audit_scenario'] = scenario
    preview = esc(scenario.split('\n\nYukarıdaki denetimi')[0])
    text = (
        header('⚖️', 'BU DENETİMİ DEĞERLENDİR', 'Denetim bilgileri değerlendirmeye aktarıldı')
        + '\n' + HR + '\n\n'
        + f'<code>{preview}</code>\n\n'
        + f'🕑 <b>Bu özellik {AI_RATE_LIMIT_SECONDS // 60} dakikada bir kez kullanılabilir.</b>\n\n'
        + '📄 Yanıt yalnızca sisteme eklenen Markdown belgelerindeki bilgilere dayanır.'
    )
    return q.edit_message_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('⚖️ Değerlendirmeyi Başlat', 'ai:audit:run')],
            [('✍️ Kendim Yazayım', 'ai:start'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


def ai_audit_run(q, context):
    scenario = context.user_data.get('ai_audit_scenario') or ai_scenario_from_context(context)
    if not scenario:
        return q.answer('Değerlendirilecek denetim bilgisi bulunamadı.', show_alert=True)
    chat_id = q.message.chat_id

    def show_first(text, **kwargs):
        return ai_show(context, chat_id, text, **kwargs)

    return ai_run(context, chat_id, q.from_user.id, scenario, show_first,
                        log_action='ai_audit')


def audit_quick_finish(q, context):
    flags, possible, unknown, procedure = quick_result_parts(context)

    activity = context.user_data.get('audit_activity')
    region = REGION_LABEL.get(context.user_data.get('audit_region'), context.user_data.get('audit_region'))
    d = audit_date(context)
    gear = context.user_data.get('audit_gear')
    species = context.user_data.get('audit_species_name')
    subject = context.user_data.get('audit_subject')
    text = (
        '🛡️ <b>DENETİM SONUCU</b>\n\n'
        f'🌊 Alan: <b>{esc(region)}</b>\n'
        f'⚓ Faaliyet: <b>{esc(audit_activity_label(context))}</b>\n'
        f'📅 Tarih: <b>{d.strftime("%d.%m.%Y")}</b>\n'
        f'🎯 Konu: <b>{esc(SUBJECT_LABEL.get(subject, subject or "—"))}</b>\n'
    )
    if context.user_data.get('audit_location'):
        text += f'📍 İl / su kaynağı / tesis: <b>{esc(context.user_data["audit_location"])}</b>\n'
    if activity in {'commercial', 'amateur'}:
        text += f'🚤 Gemi/Tekne: <b>{esc(audit_length_label(context))}</b>\n'
    if gear:
        text += f'🎣 Av aracı: <b>{esc(gear)}</b>\n'
    if species:
        text += f'🐟 Tür: <b>{esc(species)}</b>\n'

    if flags:
        text += '\n🔴 <b>Seçilen bilgilerden doğrudan çıkan mevzuat uyarıları</b>\n'
        text += ''.join(f'• {esc(x["tag"])}\n' for x in flags)

    if possible:
        text += '\n🔴 <b>Verilen cevaplara göre olası aykırılık / ayrıntılı inceleme gereken başlıklar</b>\n'
        text += ''.join(f'• {esc(x["tag"])}\n' for x in possible)
    elif not flags:
        text += '\n🟢 Verilen seçim ve cevaplara göre bu akışta doğrudan bir aykırılık işaretlenmedi.\n'

    if unknown:
        text += '\n🟡 <b>Kontrol edilmemiş / eksik unsurlar</b>\n' + ''.join(f'• {esc(x["tag"])}\n' for x in unknown)
    if procedure:
        text += '\n🧾 <b>Delil / işlem eksikleri</b>\n' + ''.join(f'• {esc(x["tag"])}\n' for x in procedure)

    text += '\n⚠️ <i>Yaptırım uygulanmadan önce ilgili madde ve Excel yaptırım kartındaki maddi unsurlar doğrulanmalıdır.</i>'

    rows = []
    seen = set()
    for item in (flags + possible + unknown):
        src, art = item['ref']
        key = (src, art)
        if key in seen:
            continue
        seen.add(key)
        rows.append([(f'📚 {item["tag"][:34]}', f'art:{src}:{art}')])
        if len(rows) >= 6:
            break
    if flags or possible:
        rows.append([('⚖️ İhlal → Yaptırım', 'mode:penalty')])
    else:
        if activity == 'amateur':
            rows.append([('🔎 Amatör → Ticari Nitelik', 'classify:start')])
    rows.append([('⚖️ Bu Denetimi Değerlendir', 'ai:audit')])
    rows.append([('🔄 Yeni Denetim', 'audit:start'), ('🏠 Ana Menü', 'menu')])
    db.log(q.from_user.id, 'guided_audit', ', '.join([x['tag'] for x in flags + possible]))
    q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


CLASSIFICATION_QUESTIONS = [
    'Amatör avcılıkta alıkonulabilir miktara izin verilen ürün miktarının 3 katı veya daha fazlası tespit edildi mi?',
    'Avlanması tamamen yasak türlerden, tür veya sayı bazında birden fazla ürün tespit edildi mi?',
    'Zaman yasağındaki türlerden, amatör avcılıkta izin verilen miktarın 2 katı veya daha fazlası tespit edildi mi?',
    'İzin verilen av aracı sayısının (iğne sayısı hariç) 2 katı veya daha fazla av aracı tespit edildi mi?',
    'Yemlik uzatma ağı hariç germe/uzatma/sürütme/çevirme ağı veya ticari avcılıkta kullanımına izin verilen başka bir av aracı tespit edildi mi?',
    'Amatör avcılıkta kullanımı yasaklanmış birden fazla av aracı tespit edildi mi?',
    'Patlayıcı, öldürücü, bayıltıcı, uyuşturucu/uyutucu/uyarıcı madde, karpit, sönmemiş kireç, balık otu, elektroşok veya benzeri yöntem kullanıldığı tespit edildi mi?',
]


def amateur_classification_start(q, context):
    if context.user_data.get('audit_activity') != 'amateur':
        return q.answer('Bu kontrol 6/2 Tebliğ kapsamındaki amatör faaliyet için kullanılır.', show_alert=True)
    context.user_data['classify_answers'] = []
    return amateur_classification_render(q, context, 0)


def amateur_classification_render(q, context, idx):
    if idx >= len(CLASSIFICATION_QUESTIONS):
        return amateur_classification_finish(q, context)
    q.edit_message_text(
        f'🔎 <b>AMATÖR → TİCARİ NİTELİK KONTROLÜ</b> — {idx+1}/{len(CLASSIFICATION_QUESTIONS)}\n\n'
        f'{esc(CLASSIFICATION_QUESTIONS[idx])}\n\n'
        '<i>6/2 Tebliğ Madde 19 esas alınır. Bir “Evet” yanıtı ticari nitelik değerlendirmesini tetikleyebilir.</i>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('✅ Evet', f'classify:ans:{idx}:yes'), ('❌ Hayır', f'classify:ans:{idx}:no')],
            [('❔ Bilinmiyor', f'classify:ans:{idx}:unknown')],
            [('📚 6/2 Md.19', 'art:62:19'), ('🚨 Kontrole Dön', 'audit:hub')],
        ]),
    )


def amateur_classification_answer(q, context, idx, ans):
    answers=context.user_data.setdefault('classify_answers',[])
    while len(answers)<=idx:
        answers.append(None)
    answers[idx]=ans
    return amateur_classification_render(q, context, idx+1)


def amateur_classification_finish(q, context):
    answers=context.user_data.get('classify_answers') or []
    yes=[i for i,a in enumerate(answers) if a=='yes']
    unknown=[i for i,a in enumerate(answers) if a in {None,'unknown'}]
    if yes:
        text=(
            '🔴 <b>TİCARİ NİTELİK DEĞERLENDİRMESİ GEREKİYOR</b>\n\n'
            'Verilen cevaplarda 6/2 Tebliğ Madde 19/1’de sayılan ölçütlerden en az biri gerçekleşmiş görünüyor. '
            'Madde 19/2’ye göre bunlardan bir tanesinin gerçekleşmesi ticari olarak değerlendirme için yeterlidir.\n\n'
            '<b>Evet denilen ölçütler:</b>\n' + ''.join(f'• {esc(CLASSIFICATION_QUESTIONS[i])}\n' for i in yes)
        )
    else:
        text=(
            '🟢 <b>MD.19/1 TİCARİ NİTELİK EŞİĞİ İŞARETLENMEDİ</b>\n\n'
            'Verilen cevaplarda Madde 19/1 ölçütlerinden “Evet” seçilmedi. Bu sonuç tek başına faaliyetin kesin olarak amatör olduğu anlamına gelmez; '
            'somut olay, diğer mevzuat ve bilinmeyen unsurlar ayrıca değerlendirilmelidir.'
        )
    if unknown:
        text+='\n\n🟡 <b>Kontrol edilmemiş ölçütler:</b>\n'+''.join(f'• {esc(CLASSIFICATION_QUESTIONS[i])}\n' for i in unknown)
    text+='\n\n⚠️ <i>Yaptırım için olayın hangi bent kapsamında olduğuna göre Kanun/Excel ceza kartı ayrıca açılmalıdır.</i>'
    db.log(q.from_user.id,'amateur_classification',f'yes={len(yes)}, unknown={len(unknown)}')
    q.edit_message_text(text,parse_mode=ParseMode.HTML,reply_markup=kb([
        [('📚 6/2 Md.19','art:62:19'),('⚖️ Yaptırım Ara','mode:penalty')],
        [('⚖️ Bu Denetimi Değerlendir', 'ai:audit')],
        [('🚨 Kontrole Dön','audit:hub'),('🏠 Ana Menü','menu')],
    ]))


def audit_gear_result(q, context):
    gear = context.user_data['audit_gear']
    region = context.user_data.get('audit_region')
    activity = context.user_data.get('audit_activity')
    length = context.user_data.get('audit_length', 0)
    source = '61' if activity == 'commercial' else '62'
    results = db.search_articles(gear, 6, source=source)
    text = f'🎣 <b>{esc(gear.title())} — KONTROL</b>\n\nAlan: {esc(REGION_LABEL.get(region, region))} | Gemi: {length:g} m\n\n'
    if activity == 'commercial' and region == 'inland' and gear in {'gırgır', 'dip trolü', 'ortasu trolü'}:
        text += '🔴 <b>6/1 Md.51: içsularda trol ve gırgır ağlarının kullanılması yasaktır.</b>\n\n'
    if activity == 'commercial' and gear == 'ışık' and region in {'karadeniz', 'marmara', 'istanbul', 'canakkale'}:
        text += '🔴 <b>6/1 Md.13: seçilen bölgede ışıkla avcılık yasaktır.</b>\n\n'
    today = datetime.now(TZ).date()
    if activity == 'commercial' and gear == 'gırgır' and region != 'inland':
        text += 'Kontrol başlıkları: yer yasağı, kapalı dönem, su derinliği, ağ derinliği ve Ağ Ölçüm Belgesi.\n'
        # 6/1 Md.12: Akdeniz 15 Nisan–15 Eylül; diğer denizler 15 Nisan–31 Ağustos.
        closed = ((today.month, today.day) >= (4,15) and (today.month, today.day) <= ((9,15) if region == 'akdeniz' else (8,31)))
        if closed:
            text += f'🔴 <b>{today.strftime("%d.%m.%Y")}: seçilen deniz bölgesi için gırgır kapalı dönemindesiniz.</b>\n'
        else:
            text += f'🟢 {today.strftime("%d.%m.%Y")}: genel gırgır kapalı dönemine denk gelmiyor; yer/derinlik ve diğer şartlar devam eder.\n'
        text += '\n'
    if activity == 'commercial' and gear == 'dip trolü' and region != 'inland':
        text += 'Kontrol başlıkları: tamamen yasak saha, kapalı dönem, kıyı mesafesi, ağ gözü/torba şartları ve yasak yerde ağ bulundurma. Bölgeye göre ayrıntı 6/1 Md.9–10’dan doğrulanmalıdır.\n\n'
    if activity == 'commercial' and gear == 'algarna':
        if region in {'ege','akdeniz'}:
            text += '🔴 <b>6/1 Md.14: Ege ve Akdeniz’de algarna kullanımı yasaktır.</b>\n\n'
        elif region == 'karadeniz':
            text += '⚠️ Karadeniz’de algarna yalnız deniz salyangozu avcılığı kapsamındaki özel şartlarla değerlendirilebilir.\n\n'
        elif region == 'marmara':
            text += '⚠️ Marmara’da algarna yalnız Tebliğdeki karides avcılığı şartları yönünden değerlendirilmelidir.\n\n'
    if activity == 'amateur' and gear in {'parakete'}:
        text += '🔴 <b>6/2 Md.16: denizlerde amatör avcılıkta parakete kullanılamaz.</b>\n\n'
    if activity == 'commercial' and gear in {'algarna','manyat','dreç','dalma'}:
        effective=datetime(2026,9,1,tzinfo=TZ).date()
        if today >= effective:
            text += '⚠️ <b>6/1 Md.50/15:</b> Bu faaliyet için 1 Eylül 2026 itibarıyla Bakanlıkça istenen gemi izleme ve kayıt cihazı işler/çalışır durumda olmalıdır.\n\n'
        else:
            text += 'ℹ️ <b>Yaklaşan yükümlülük:</b> 6/1 Md.50/15 uyarınca bu faaliyet için gemi izleme/kayıt cihazı şartı 1 Eylül 2026’da başlar.\n\n'
    primary = {
        'gırgır': [12],
        'dip trolü': [9,10],
        'ortasu trolü': [9,11],
        'algarna': [14,29],
        'manyat': [14,27],
        'dreç': [28],
        'uzatma ağı': [14],
        'parakete': [15] if activity == 'commercial' else [16],
        'ışık': [13] if activity == 'commercial' else [8],
        'dalma': [49] if activity == 'commercial' else [16],
    }.get(gear, [])
    ordered=[]
    seen=set()
    for art in primary:
        row=db.get_article(source,art)
        if row and (row['source'],row['article']) not in seen:
            ordered.append(row); seen.add((row['source'],row['article']))
    for row in results:
        if (row['source'],row['article']) not in seen:
            ordered.append(row); seen.add((row['source'],row['article']))
    rows = []
    for row in ordered[:8]:
        rows.append([(f'{SRC_LABEL[row["source"]]} Md.{row["article"]} — {row["title"][:23]}', f'art:{row["source"]}:{row["article"]}')])
    rows.append([('⚖️ Bu Denetimi Değerlendir', 'ai:audit')])
    rows.append([('🚨 Kontrole Dön','audit:hub'),('⚖️ Yaptırım Ara', 'mode:penalty')])
    rows.append([('🏠 Ana Menü', 'menu')])
    q.edit_message_text(text + '📚 İlgili kaynak maddeleri:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def text_handler(update, context):
    uid = update.effective_user.id
    text = update.effective_message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'ai_analysis':
        context.user_data.pop('mode', None)

        def show_first(body, **kwargs):
            return send_or_edit(update, context, body, **kwargs)

        ai_run(context, update.effective_chat.id, uid, text, show_first)
        return

    if mode == 'guide_measure':
        g = guide_current(context)
        if not g:
            context.user_data.pop('mode', None)
            return send_or_edit(update, context, 'Aktif kontrol föyü bulunamadı.', reply_markup=kb([[('📋 Tekne Türü Kılavuzları', 'guide:menu')]]))
        idx = int(context.user_data.get('guide_measure_idx', 0))
        fields = g.get('measure_fields') or []
        if idx >= len(fields):
            context.user_data.pop('mode', None)
            return send_or_edit(update, context, 'Ölçüm alanları tamamlandı.', reply_markup=kb([[('📊 Sonucu Aç', 'guide:result')]]))
        field = fields[idx]
        context.user_data.setdefault('guide_measurements', {})[field] = text
        idx += 1
        context.user_data['guide_measure_idx'] = idx
        if idx >= len(fields):
            context.user_data.pop('mode', None)
            return send_or_edit(update, context, 
                '📐 <b>Ölçüm/kayıt alanları kaydedildi.</b>',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('📊 Kontrol Sonucunu Aç', 'guide:result'), ('↩️ Föye Dön', f'guide:open:{g["key"]}')]])
            )
        next_field = fields[idx]
        return send_or_edit(update, context, 
            f'📐 {idx+1}/{len(fields)} — <b>{esc(next_field)}</b>\n\nDeğeri yazın.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('⏭️ Kontrol Edilmedi / Atla', 'guide:measure:skip')], [('📊 Sonuca Dön', 'guide:result')]])
        )

    if mode == 'penalty_length':
        try:
            length=float(text.replace(',','.'))
            if length<0: raise ValueError
        except ValueError:
            return send_or_edit(update, context, 'Gemi boyunu sayı olarak yazın. Örnek: 17.4')
        pid=context.user_data.get('penalty_pid')
        context.user_data['audit_length']=length
        context.user_data.pop('mode',None)
        return send_or_edit(update, context, f'🚤 Gemi boyu <b>{length:g} m</b> olarak kaydedildi. Ceza kartında Exceldeki uygun boy satırı öne çıkarılacak.',parse_mode=ParseMode.HTML,reply_markup=kb([[('⚖️ Ceza Kartını Aç',f'pen:{pid}')],[('🏠 Ana Menü','menu')]]))

    if mode == 'audit_location':
        context.user_data['audit_location'] = text[:160]
        context.user_data.pop('mode', None)
        return send_or_edit(
            update, context,
            f'🏞️ İçsu konumu <b>{esc(context.user_data["audit_location"])}</b> olarak kaydedildi.\n\nKontrol edilen faaliyet hangi kapsamda?',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [('🚤 Ticari avcılık', 'audit:activity:commercial'), ('🎣 Amatör avcılık', 'audit:activity:amateur')],
                [('↩️ Alanı Değiştir', 'audit:start'), ('🏠 Ana Menü', 'menu')],
            ]),
        )

    if mode == 'audit_length_exact':
        try:
            length = float(text.replace(',', '.'))
            if length < 0:
                raise ValueError
        except ValueError:
            return send_or_edit(update, context, 'Gemi boyunu metre olarak sayı biçiminde yazın. Örnek: 17.4')
        context.user_data['audit_length_exact'] = length
        context.user_data['audit_length'] = length
        if length == 0:
            context.user_data['audit_length_band'] = 'none'
        elif length < 12:
            context.user_data['audit_length_band'] = 'lt12'
        elif length < 22:
            context.user_data['audit_length_band'] = '12to22'
        else:
            context.user_data['audit_length_band'] = 'ge22'
        context.user_data.pop('mode', None)
        return send_or_edit(update, context, 
            f'🚤 Tam boy <b>{length:g} m</b> olarak kaydedildi.\n\n4. adım: olay/kontrol tarihini seçin.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📅 Bugün', 'audit:date:today'), ('🗓 Başka tarih', 'audit:date:other')], [('🏠 Ana Menü', 'menu')]])
        )

    if mode == 'audit_date':
        parsed = None
        for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d', '%d.%m.%y', '%d/%m/%y'):
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                pass
        if parsed is None:
            return send_or_edit(update, context, 'Tarihi GG.AA.YYYY biçiminde yazın. Örnek: 20.05.2026')
        context.user_data['audit_date'] = parsed.isoformat()
        context.user_data.pop('mode', None)
        activity = context.user_data.get('audit_activity')
        if activity in {'processing', 'aquaculture'}:
            rows = [
                [('🏭 Tesis İzin / Şartları', 'audit:subject:facility'), ('🧪 Sağlık / Kalite', 'audit:subject:health')],
                [('📦 Ambalaj / Nakliye', 'audit:subject:transport'), ('🌱 Atık / Çevre', 'audit:subject:environment')],
            ]
        else:
            rows = [
                [('🎣 Avcılık faaliyeti', 'audit:subject:fishing'), ('🐟 Ürün / Tür', 'audit:subject:species')],
                [('📦 Nakil / Satış', 'audit:subject:transport')],
            ]
            if activity == 'commercial' and audit_rule_length(context) > 0:
                rows[1].append(('🚤 Gemi / Ruhsat / Donanım', 'audit:subject:vessel'))
            elif activity == 'amateur':
                rows[1].append(('🔎 Ticari Nitelik Kontrolü', 'classify:start'))
        rows.append([('🏠 Ana Menü', 'menu')])
        return send_or_edit(update, context, 
            f'📅 Tarih <b>{parsed.strftime("%d.%m.%Y")}</b> olarak kaydedildi.\n\n5. adım: denetimin ana konusunu seçin.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb(rows)
        )

    if mode in {'species_search', 'audit_species_search'}:
        kind = context.user_data.get('species_kind', 'commercial')
        if kind == 'prohibited':
            activity = context.user_data.get('prohibited_activity')
            results = db.search_prohibited(text, LIMIT, activity)
            rows = [[(r['name'][:45], f'art:{r["source"]}:{r["article"]}')] for r in results]
            scope_label = ACTIVITY_SCOPE_LABEL.get(activity, 'Tüm faaliyetler')
            msg = f'🚫 <b>{esc(scope_label)} — tamamen yasak tür araması</b>\n\n' + ('Eşleşme bulundu.' if results else 'Eşleşme bulunamadı. Türkçe tür adını değiştirerek deneyin.')
        else:
            scope = context.user_data.get('species_scope')
            results = db.search_species(text, kind, LIMIT, scope)
            rows = [[(r['name'][:45], f'sp:{kind}:{r["id"]}')] for r in results]
            water = {'sea':'Deniz', 'inland':'İçsu'}.get(scope, 'Tüm sular')
            msg = f'🐟 <b>{esc(text)}</b> — {water} · {len(results)} sonuç'
        if mode == 'audit_species_search' and context.user_data.get('guided_active'):
            rows.append([('➡️ Tür belirtmeden devam', 'audit:guided:check'), ('🏠 Ana Menü', 'menu')])
        else:
            rows.append([('↩️ Ana Menü', 'menu')])
        db.log(uid, 'species_search', text)
        return send_or_edit(update, context, msg, parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if mode == 'source_search':
        source = context.user_data.get('source')
        if text.isdigit() and db.get_article(source, int(text)):
            return send_or_edit(update, context, 
                f'📚 {SRC_LABEL.get(source, source)} Madde {text}',
                reply_markup=kb([[('Maddeyi Aç', f'art:{source}:{text}')], [('↩️ Ana Menü', 'menu')]]),
            )
        results = db.search_articles(text, LIMIT, source=source)
        rows = [[(f'Md.{r["article"]} {r["title"][:35]}', f'art:{source}:{r["article"]}')] for r in results]
        rows.append([('↩️ Ana Menü', 'menu')])
        db.log(uid, 'source_search', text)
        return send_or_edit(update, context, f'📚 <b>{esc(text)}</b> — {len(results)} madde', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if mode == 'penalty':
        results = db.search_penalties(text, LIMIT)
        rows = []
        for r in results:
            label = r["violation"][:31]
            if r["option_text"]:
                label += ' / ' + r["option_text"][:13]
            rows.append([(f'⚖️ {label}', f'pen:{r["id"]}')])
        if not rows:
            for r in db.search_raw(text, 4):
                rows.append([(f'📊 Excel satır {r["source_row"]}', f'raw:{r["source_row"]}')])
        rows.append([('📚 Mevzuatta da Ara', 'mode:lawsearch'), ('↩️ Ana Menü', 'menu')])
        db.log(uid, 'penalty_search', text)
        return send_or_edit(update, context, 
            f'⚖️ <b>{esc(text)}</b> — {len(results)} yapılandırılmış yaptırım sonucu\n\n<i>Deniz, içsu ve tesis kapsamındaki ceza kayıtları birlikte aranır. Sonuç bulunmazsa Excel ham satır araması gösterilir.</i>',
            parse_mode=ParseMode.HTML,
            reply_markup=kb(rows),
        )

    if mode in {'gear', 'place', 'lawsearch'}:
        articles = db.search_articles(text, LIMIT)
        rules = db.search_rules(text, limit=4)
        rows = [[(f'🛡️ {r["title"][:43]}', f'rule:{r["id"]}')] for r in rules]
        for r in articles[:LIMIT]:
            rows.append([(f'📚 {SRC_LABEL.get(r["source"], r["source"])} Md.{r["article"]} {r["title"][:22]}', f'art:{r["source"]}:{r["article"]}')])
        rows.append([('↩️ Ana Menü', 'menu')])
        db.log(uid, 'legal_search', text)
        return send_or_edit(update, context, f'🔎 <b>{esc(text)}</b> — tüm kaynaklardaki eşleşmeler', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if mode is None:
        # Doğal Dil / Genel Arama
        # Honour the configured RESULT_LIMIT instead of fixed counts, while
        # keeping each category small enough that the list stays scannable.
        per = max(2, LIMIT // 2)
        results_species_com = db.search_species(text, 'commercial', per)
        results_species_ama = db.search_species(text, 'amateur', per)
        results_penalties = db.search_penalties(text, per)
        results_articles = db.search_articles(text, per)
        
        rows = []
        # Türleri ekle
        for r in results_species_com:
            rows.append([(f'🐟 (Ticari) {r["name"][:35]}', f'sp:commercial:{r["id"]}')])
        for r in results_species_ama:
            rows.append([(f'🎣 (Amatör) {r["name"][:35]}', f'sp:amateur:{r["id"]}')])
            
        # Cezaları ekle
        for r in results_penalties:
            label = r["violation"][:31]
            if r["option_text"]:
                label += ' / ' + r["option_text"][:13]
            rows.append([(f'⚖️ {label}', f'pen:{r["id"]}')])
            
        # Mevzuat maddelerini ekle
        for r in results_articles:
            rows.append([(f'📚 {SRC_LABEL.get(r["source"], r["source"])} Md.{r["article"]} {r["title"][:22]}', f'art:{r["source"]}:{r["article"]}')])
            
        if rows:
            rows.append([('🏠 Ana Menü', 'menu')])
            db.log(uid, 'general_search', text)
            counts = []
            n_species = len(results_species_com) + len(results_species_ama)
            if n_species:
                counts.append(f'🐟 Tür {n_species}')
            if results_penalties:
                counts.append(f'⚖️ Ceza {len(results_penalties)}')
            if results_articles:
                counts.append(f'📚 Mevzuat {len(results_articles)}')
            body = header('🔍', f'“{text}”', 'Karma arama sonuçları')
            body += '\n' + HR + '\n' + '  ·  '.join(counts)
            return send_or_edit(update, context,
                body,
                parse_mode=ParseMode.HTML,
                reply_markup=kb(rows)
            )
        else:
            body = header('🔍', f'“{text}”', 'Sonuç bulunamadı')
            body += (
                '\n' + HR + '\n'
                'Tür, ceza veya mevzuat kayıtlarında eşleşme yok.\n\n'
                '<b>Deneyebilecekleriniz</b>\n'
                '• Kelimenin kökünü yazın — <code>ruhsat</code>, <code>ağ</code>\n'
                '• Tür adını tek başına yazın — <code>lüfer</code>\n'
                '• Aşağıdaki menülerden ilerleyin'
            )
            return send_or_edit(update, context,
                body,
                parse_mode=ParseMode.HTML,
                reply_markup=kb([
                    [('📖 Ceza Rehberi', 'ceza:menu'), ('📖 Tür Çizelgesi', 'turcizelge:menu')],
                    [('🏠 Ana Menü', 'menu')],
                ])
            )

    send_or_edit(update, context, 'Bir işlem seçin:', reply_markup=kb(MAIN))


ACTIVITY_LABELS = {
    'setup': 'İlk yönetici hesabını oluşturdu',
    'login': 'Giriş yaptı',
    'logout': 'Çıkış yaptı',
    'button': 'Düğmeye bastı',
    'text': 'Metin gönderdi',
    'password_change': 'Kendi şifresini değiştirdi',
    'person_create': 'Kişi oluşturdu',
    'person_update': 'Kişi bilgilerini değiştirdi',
    'registration': 'Üyelik başvurusu yaptı',
    'password_reset_request': 'Şifre yenileme talebi oluşturdu',
    'issue_report': 'Sorun bildirdi',
    'issue_resolve': 'Sorun bildirimini kapattı',
}


def activity_label(action):
    return esc(ACTIVITY_LABELS.get(action, action))


def show_admin_issues(q):
    if q.from_user.id not in ADMIN_IDS:
        return q.answer('Yönetici yetkisi gerekli.', show_alert=True)
    reports = db.admin_issue_reports()
    text = '🛠 <b>AÇIK SORUN BİLDİRİMLERİ</b>\n\n'
    rows = []
    if not reports:
        text += '<i>Açık sorun bildirimi yok.</i>\n'
    for report in reports:
        created = report['created_at'].replace('T', ' ')[:16]
        username = f' (@{report["username"]})' if report['username'] else ''
        text += (
            f'<b>#{report["id"]} · {esc(report["display_name"])}{esc(username)}</b>\n'
            f'<code>{created}</code>\n{esc(report["message"])}\n\n'
        )
        rows.append([('✅ Çözüldü olarak işaretle', f'admin:issue:resolve:{report["id"]}')])
    rows.append([('↩️ Yönetici Paneli', 'admin:panel'), ('🏠 Ana Menü', 'menu')])
    return q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def show_admin_panel(q, section='main'):
    if q.from_user.id not in ADMIN_IDS:
        return q.answer('Yönetici yetkisi gerekli.', show_alert=True)
    
    if section == 'main':
        users = len(accounts.list_accounts())
        count = db.activity_count()
        issue_count = db.open_issue_count()
        rows = db.admin_activity(8)
        text = (
            f'🔐 <b>YÖNETİCİ VE DENETİM PANELİ</b>\n\n'
            f'👥 <b>Kayıtlı Kullanıcı Sayısı:</b> {users}\n'
            f'⚡ <b>Toplam Kullanıcı İşlemi:</b> {count}\n\n'
            f'<b>Son Yapılan İşlemler:</b>\n'
        )
        for r in rows:
            dname = r['display_name']
            time_str = r['created_at'].split('T')[-1] if 'T' in str(r['created_at']) else str(r['created_at'])
            label = activity_label(r['action'])
            detail = f': {esc(r["detail"])}' if r['detail'] else ''
            text += f'• <code>{time_str[:8]}</code> <b>{esc(dname)}</b> · {label}{detail}\n'
        
        rows_kb = [
            [('📊 Denetim & Arama Dağılımı', 'admin:stats:vessels')],
            [('👥 Personel Faaliyetleri', 'admin:stats:users'), ('📋 İşlem Kayıtları', 'admin:stats:logs')],
            [(f'🛠 Sorun Bildirimleri ({issue_count})', 'admin:issues')],
            [('👤 Kişiler / Şifreler', 'web:people')],
            [('🏠 Ana Menü', 'menu')]
        ]
        return q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))

    elif section == 'vessels':
        trend = db.admin_daily_trend(7)
        scale = max(1, max(max(d, a) for _, d, a in trend))
        trend_table = (
            '<table><thead><tr><th>Tarih</th><th>Denetim</th><th>Arama</th></tr></thead><tbody>'
            + ''.join(
                f'<tr><td>{day[8:10]}.{day[5:7]}</td>'
                f'<td><code>{esc(trend_bar(d, scale, width=5))}</code></td>'
                f'<td><code>{esc(trend_bar(a, scale, width=5))}</code></td></tr>'
                for day, d, a in trend
            )
            + '</tbody></table>'
        )
        guides, searches = db.admin_audit_activity()
        text = '📊 <b>DENETİM VE SORGULAMA DAĞILIMI</b>\n\n'
        text += '📈 <b>Son 7 Gün:</b>\n' + trend_table + '\n\n'
        text += '🚢 <b>En Çok Başlatılan Denetim / Kılavuzlar:</b>\n'
        if guides:
            for g in guides[:8]:
                text += f'• <b>{esc(g["query"] or "Genel Denetim")}:</b> {g["count"]} kez\n'
        else:
            text += '• <i>Henüz denetim kaydı bulunmuyor.</i>\n'
        
        text += '\n🔍 <b>En Çok Aranan Kelimeler:</b>\n'
        if searches:
            for s in searches[:8]:
                text += f'• «<code>{esc(s["query"])}</code>»: {s["count"]} sorgu\n'
        else:
            text += '• <i>Henüz arama kaydı bulunmuyor.</i>\n'
            
        rows_kb = [[('↩️ Yönetici Paneli', 'admin:panel'), ('🏠 Ana Menü', 'menu')]]
        return q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))

    elif section == 'users':
        user_rows = db.admin_user_activity()
        text = '👥 <b>PERSONEL / KULLANICI FAALİYETLERİ</b>\n\n'
        for u in user_rows:
            uid = u['user_id']
            dname = USER_NAMES.get(uid, u['first_name'] or u['username'] or str(uid))
            uname = f'(@{u["username"]})' if u['username'] else ''
            last_seen = u['last_seen'].replace('T', ' ')[:16] if u['last_seen'] else '—'
            text += f'👤 <b>{esc(dname)}</b> {esc(uname)}\n'
            text += f'   🆔 <code>{uid}</code> | ⚡ Toplam İşlem: <b>{u["query_count"]}</b>\n'
            text += f'   🕒 Son Görülme: <i>{last_seen}</i>\n\n'
            
        rows_kb = [[('↩️ Yönetici Paneli', 'admin:panel'), ('🏠 Ana Menü', 'menu')]]
        return q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))

    elif section == 'logs':
        rows = db.admin_activity(30)
        text = '📋 <b>SON 30 KULLANICI İŞLEMİ</b>\n\n'
        for r in rows:
            dname = r['display_name']
            time_str = r['created_at'].replace('T', ' ')[5:19] if r['created_at'] else ''
            detail = f' — <i>{esc(r["detail"])}</i>' if r['detail'] else ''
            text += f'• <code>{time_str}</code> <b>{esc(dname)}</b> → {activity_label(r["action"])}{detail}\n'
        if not rows:
            text += '<i>Henüz kullanıcı işlemi kaydedilmedi.</i>\n'
            
        rows_kb = [[('↩️ Yönetici Paneli', 'admin:panel'), ('🏠 Ana Menü', 'menu')]]
        return q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))
