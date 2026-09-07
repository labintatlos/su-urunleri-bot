import html
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

import db

import json
from pathlib import Path
import os
ASSET_DIR = Path('/app/data') if os.path.exists('/app/data') else Path(__file__).parent / 'data'
with open(ASSET_DIR / 'ceza_rehberi_v2.json', 'r', encoding='utf-8') as f:
    CEZA_REHBERI = json.load(f)

with open(ASSET_DIR / 'tur_cizelgesi.json', 'r', encoding='utf-8') as f:
    TUR_CIZELGESI = json.load(f)




USER_NAMES = {}


def parse_ids(value):
    if value is None:
        return set()
    raw = str(value).strip()
    if not raw:
        return set()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, (int, str)):
            parsed = [parsed]
        if isinstance(parsed, list):
            return {int(str(x).split(':', 1)[0]) for x in parsed if str(x).strip()}
    except Exception:
        pass
    out = set()
    for part in re.split(r'[,;\s]+', raw.strip('[]')):
        part = part.strip().strip('"\'')
        if not part:
            continue
        try:
            out.add(int(part.split(':', 1)[0]))
        except ValueError:
            pass
    return out


def parse_allowed_users(raw_value):
    user_ids = set()
    if not raw_value:
        return user_ids
    entries = []
    if isinstance(raw_value, list):
        entries = raw_value
    elif isinstance(raw_value, str):
        raw_str = raw_value.strip()
        try:
            parsed = json.loads(raw_str)
            if isinstance(parsed, list):
                entries = parsed
            else:
                entries = [raw_str]
        except Exception:
            entries = [x.strip() for x in re.split(r'[,;\n]+', raw_str) if x.strip()]

    for entry in entries:
        entry_str = str(entry).strip()
        if not entry_str:
            continue
        if ':' in entry_str:
            parts = entry_str.split(':', 1)
            uid_str = parts[0].strip()
            name_str = parts[1].strip()
            try:
                uid = int(uid_str)
                user_ids.add(uid)
                if name_str:
                    USER_NAMES[uid] = name_str
            except ValueError:
                pass
        else:
            try:
                uid = int(entry_str)
                user_ids.add(uid)
            except ValueError:
                pass
    return user_ids


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

TOKEN = os.environ.get('TELEGRAM_TOKEN') or options.get('bot_token', '')
ADMIN_IDS = parse_ids(os.environ.get('ADMIN_IDS') or options.get('admin_id', ''))
ALLOWED_IDS = parse_allowed_users(os.environ.get('ALLOWED_USER_IDS') or options.get('allowed_users', ''))
TZ = ZoneInfo(os.environ.get('TZ') or 'Europe/Istanbul')
try:
    LIMIT = int(os.environ.get('RESULT_LIMIT') or options.get('result_limit', 8))
except ValueError:
    LIMIT = 8

SRC_LABEL = {
    'law': '1380 Kanun',
    'reg': 'Yönetmelik',
    '61': '6/1 Ticari Tebliğ',
    '62': '6/2 Amatör Tebliğ',
    'bagis': 'BAGİS Tebliği',
    'excel': 'Ceza Excel',
    'kilavuz': 'Saha Kılavuzu',
}


REGION_LABEL = {
    'karadeniz': 'Karadeniz',
    'marmara': 'Marmara Denizi',
    'istanbul': 'İstanbul Boğazı',
    'canakkale': 'Çanakkale Boğazı',
    'ege': 'Ege Denizi',
    'akdeniz': 'Akdeniz',
    'international': 'Uluslararası / MEB',
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
}


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
    return InlineKeyboardMarkup([[InlineKeyboardButton(title, callback_data=data) for title, data in row] for row in rows])


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


def tally(answers):
    """Running counts for a checklist: '✅ 3 · ❌ 1 · ⚪ 2 · ⋯ 6'."""
    ok = sum(1 for a in answers if a == 'ok')
    bad = sum(1 for a in answers if a == 'bad')
    skip = sum(1 for a in answers if a == 'skip')
    left = sum(1 for a in answers if a is None)
    return f'✅ {ok}  ·  ❌ {bad}  ·  ⚪ {skip}  ·  ⋯ {left}'





async def send_or_edit(update, context, text, force_new=False, **kwargs):
    try:
        await update.effective_message.delete()
    except Exception:
        pass

    last_id = context.user_data.get('last_bot_msg_id')
    chat_id = update.effective_chat.id

    if last_id:
        if force_new:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=last_id)
            except Exception:
                pass
        else:
            try:
                kwargs_edit = kwargs.copy()
                if 'reply_markup' not in kwargs_edit: kwargs_edit['reply_markup'] = None
                if 'parse_mode' not in kwargs_edit: kwargs_edit['parse_mode'] = None
                new_msg = await context.bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=last_id,
                    **kwargs_edit
                )
                return new_msg
            except Exception:
                pass
    
    new_msg = await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    context.user_data['last_bot_msg_id'] = new_msg.message_id
    return new_msg

def allowed(user_id):
    return user_id in ADMIN_IDS or user_id in ALLOWED_IDS


async def guard(update):
    user = update.effective_user
    if not user:
        return False
    if not allowed(user.id):
        unauth_msg = (
            "⛔ <b>Bu botu kullanmaya yetkiniz bulunmamaktadır.</b>\n\n"
            "Yetki talep etmek için sistem yöneticisine aşağıdaki kimlik numaranızı iletin:\n"
            f"🆔 <b>Sizin Telegram ID'niz:</b> <code>{user.id}</code>"
        )
        if update.callback_query:
            await update.callback_query.answer(f'Yetkiniz yok! ID: {user.id}', show_alert=True)
            try:
                await send_or_edit(update, context, unauth_msg, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await send_or_edit(update, context, unauth_msg, parse_mode=ParseMode.HTML)

        # Notify Admin(s)
        now = datetime.now(TZ).strftime("%d.%m.%Y %H:%M:%S")
        uname = f"@{user.username}" if user.username else "Yok"
        admin_alert = (
            "⚠️ <b>Yetkisiz Erişim Denemesi!</b>\n\n"
            f"👤 <b>Ad Soyad:</b> {esc(user.full_name)}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"📛 <b>Kullanıcı Adı:</b> {esc(uname)}\n"
            f"🕐 <b>Zaman:</b> {now}"
        )
        bot_app = update.get_bot() if hasattr(update, 'get_bot') else None
        if bot_app:
            for admin_id in ADMIN_IDS:
                try:
                    await bot_app.send_message(chat_id=admin_id, text=admin_alert, parse_mode=ParseMode.HTML)
                except Exception:
                    pass
        return False

    disp_name = USER_NAMES.get(user.id, user.first_name)
    db.touch_user(user, custom_name=disp_name)
    return True


# Users whose legacy reply keyboard has been cleared during this run.
_REPLY_KB_CLEARED = set()

MAIN = [
    [('📋 Tekne Türü Kılavuzları', 'guide:menu'), ('🚨 Denetime Başla', 'audit:start')],
    [('📖 Pratik Ceza Rehberi', 'ceza:menu'), ('📖 Pratik Tür Çizelgesi', 'turcizelge:menu')],
    [('🚢 Gemi / Ruhsat / BAGİS', 'vessel:menu')],
    [('🧾 Kolluk İşlem Rehberi', 'field:Kolluk İşlemi')],
    [('🧮 Hesaplayıcılar', 'calc:menu'), ('⭐ Favoriler', 'fav:list')],
    [('🕘 Son Sorgular', 'history'), ('❓ Yardım', 'help')],
    [('ℹ️ Sürüm', 'about')],
]


async def send_menu(target, user_id=None, edit=False, update=None, context=None, force_new=False):
    text = (
        '<b>⚓ SU ÜRÜNLERİ KOLLUK ASİSTANI</b>\n\n'
        '🌊 <b>Deniz görev alanı</b>\n\n'
        'Su ürünleri denetimlerinde mevzuat hükümlerinin değerlendirilmesi, ihlallerin tespiti '
        've uygulanacak işlemlerin belirlenmesine yardımcı olur.\n\n'
        '📋 <b>Tekne Türü Kılavuzları</b> ile çıkacağınız tekneye özel kontrol föyünü açabilir, '
        'her maddeyi Uygun / Uygunsuz / Kontrol Edilmedi olarak işaretleyebilirsiniz.\n\n'
        '🚨 <b>Denetime Başla</b> ise bölgeden başlayıp faaliyet, gemi boyu, tarih, av aracı ve türe doğru adım adım ilerleyen yönlendirilmiş kontrolü başlatır.\n\n'
        '💬 <b>Aramak için doğrudan yazın.</b> Tür, ceza veya mevzuat kelimesi yazmanız yeterli — '
        'örn. <code>hamsi</code>, <code>ruhsatsız</code>, <code>BAGİS</code>.'
    )
    rows = list(MAIN)
    if user_id in ADMIN_IDS:
        rows = rows + [[('🔐 Yönetici Paneli', 'admin:panel')]]
    if edit:
        await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
    else:
        if update and context:
            await send_or_edit(update, context, text, force_new=force_new, parse_mode=ParseMode.HTML, reply_markup=kb(rows))
        else:
            await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    context.user_data.clear()
    uid = update.effective_user.id
    db.log(uid, 'start')

    # Older versions sent a persistent reply keyboard; nothing does any more.
    # Clearing it needs a throwaway message, so only do it once per user per
    # run instead of flashing it on every /start.
    if uid not in _REPLY_KB_CLEARED:
        _REPLY_KB_CLEARED.add(uid)
        try:
            tmp = await send_or_edit(update, context, '⚓', reply_markup=ReplyKeyboardRemove())
            await tmp.delete()
        except Exception:
            pass

    await send_menu(update.effective_message, update.effective_user.id, update=update, context=context, force_new=True)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    q = update.callback_query
    await q.answer()
    context.user_data['last_bot_msg_id'] = q.message.message_id
    data = q.data
    uid = q.from_user.id

    if data == 'menu':
        context.user_data.clear()
        return await send_menu(q, uid, edit=True)


    if data == 'guide:menu':
        return await guide_menu(q, context)
    if data == 'guide:fromgear':
        return await guide_from_gear(q, context)
    if data.startswith('guide:open:'):
        return await guide_open(q, context, data.split(':', 2)[2])
    if data.startswith('guide:view:'):
        _, _, key, page = data.split(':', 3)
        return await guide_view(q, context, key, int(page))
    if data.startswith('guide:refs:'):
        return await guide_refs(q, context, data.split(':', 2)[2])
    if data.startswith('guide:start:'):
        return await guide_start(q, context, data.split(':', 2)[2])
    if data.startswith('guide:go:'):
        return await guide_render(q, context, int(data.rsplit(':', 1)[1]))
    if data.startswith('guide:ans:'):
        _, _, idx, ans = data.split(':', 3)
        return await guide_answer(q, context, int(idx), ans)
    if data == 'guide:finish' or data == 'guide:result':
        return await guide_finish(q, context)
    if data == 'guide:badmenu':
        return await guide_bad_menu(q, context)
    if data.startswith('guide:pen:'):
        return await guide_penalty_search(q, context, int(data.rsplit(':', 1)[1]))
    if data == 'guide:measure:start':
        return await guide_measure_start(q, context)
    if data == 'guide:measure:skip':
        return await guide_measure_skip(q, context)



    if data == 'ceza:menu':
        rows = []
        for c in CEZA_REHBERI:
            rows.append([(f"{c['title']}", f"ceza:view:{c['id']}")])
        rows.append([('🔎 Kelimeyle Ceza Ara', 'mode:penalty')])
        rows.append([('🏠 Ana Menü', 'menu')])
        return await q.edit_message_text('<b>📖 PRATİK CEZA REHBERİ</b>\n\nİncelemek istediğiniz başlığı seçin:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if data.startswith('ceza:view:'):
        cid = data.split(':', 2)[2]
        c_main = next((c for c in CEZA_REHBERI if c['id'] == cid), None)
        if c_main:
            rows = []
            if c_main.get('sub'):
                for s in c_main['sub']:
                    rows.append([(f"{s['title']}", f"ceza:sub:{c_main['id']}:{s['id']}")])
            if c_main.get('items'):
                for it in c_main['items']:
                    rows.append([(f"{it['title']}", f"ceza:item:{c_main['id']}:none:{it['id']}")])
            
            if rows:
                rows.append([('🔙 Ceza Rehberi', 'ceza:menu')])
                rows.append([('🏠 Ana Menü', 'menu')])
                return await q.edit_message_text(f"<b>{esc(c_main['title'])}</b>\n\nLütfen bir seçenek belirleyin:", parse_mode=ParseMode.HTML, reply_markup=kb(rows))
            else:
                out = f"<b>{esc(c_main['title'])}</b>\n\n{c_main.get('content', '')}"
                if len(out) > 4000: out = out[:4000] + "...(Devamı kesildi)"
                return await q.edit_message_text(out, parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Ceza Rehberi', 'ceza:menu')], [('🏠 Ana Menü', 'menu')]]))

    if data.startswith('ceza:sub:'):
        _, _, cid, sid = data.split(':')
        c_main = next((c for c in CEZA_REHBERI if c['id'] == cid), None)
        if c_main:
            s_sub = next((s for s in c_main['sub'] if s['id'] == sid), None)
            if s_sub:
                rows = []
                if s_sub.get('items'):
                    for it in s_sub['items']:
                        rows.append([(f"{it['title']}", f"ceza:item:{cid}:{sid}:{it['id']}")])
                if rows:
                    rows.append([('🔙 Üst Başlık', f"ceza:view:{cid}")])
                    rows.append([('🏠 Ana Menü', 'menu')])
                    return await q.edit_message_text(f"<b>{esc(s_sub['title'])}</b>\n\nLütfen bir ihlal türü seçin:", parse_mode=ParseMode.HTML, reply_markup=kb(rows))
                else:
                    out = f"<b>{esc(s_sub['title'])}</b>\n\n{s_sub.get('content', '')}"
                    if len(out) > 4000: out = out[:4000] + "...(Devamı kesildi)"
                    return await q.edit_message_text(out, parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Üst Başlık', f"ceza:view:{cid}")], [('🏠 Ana Menü', 'menu')]]))

    if data.startswith('ceza:item:'):
        _, _, cid, sid, iid = data.split(':')
        c_main = next((c for c in CEZA_REHBERI if c['id'] == cid), None)
        if c_main:
            it = None
            back_data = f"ceza:view:{cid}"
            if sid != 'none':
                s_sub = next((s for s in c_main['sub'] if s['id'] == sid), None)
                if s_sub:
                    it = next((i for i in s_sub['items'] if i['id'] == iid), None)
                    back_data = f"ceza:sub:{cid}:{sid}"
            else:
                it = next((i for i in c_main['items'] if i['id'] == iid), None)
                
            if it:
                out = f"<b>{esc(it['title'])}</b>\n"
                out += "➖" * 15 + "\n"
                for k, v in it['details'].items():
                    if k.lower() != 'ihlal':
                        out += f"▪️ <b>{esc(k)}:</b> {esc(v).replace('*', '')}\n"
                
                return await q.edit_message_text(out, parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Geri', back_data)], [('🏠 Ana Menü', 'menu')]]))

    if data.startswith('mode:'):
        mode = data.split(':', 1)[1]
        context.user_data['mode'] = mode
        prompts = {
            'penalty': '⚖️ İhlali/olayı yazın. Örnek: <code>BAGİS arızası</code>, <code>kalkan parakete</code>, <code>ruhsatsız gemi</code>, <code>nakil belgesi</code>.',
            'gear': '🎣 Av aracını veya yöntemi yazın. Örnek: <code>gırgır</code>, <code>dip trolü</code>, <code>algarna</code>, <code>ışık</code>.',
            'place': '📍 Yer, il, koy, burun veya saha adını yazın. Koordinatla tarif edilen alanlarda bot kaynak hükmünü gösterir; geometrik sınırdan emin olmadığı yerde kendiliğinden ihlal kararı vermez.',
            'lawsearch': '📚 Aranacak mevzuat kelimesini veya konuyu yazın. Örnek: <code>el koyma</code>, <code>ruhsat geri alma</code>, <code>gırgır</code>.',
        }
        return await q.edit_message_text(prompts[mode], parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Ana Menü', 'menu')]]))

    if data == 'sources':
        return await show_sources(q)
    if data.startswith('src:'):
        key = data.split(':', 1)[1]
        if key == 'excel':
            context.user_data['mode'] = 'penalty'
            return await q.edit_message_text('📊 <b>Ceza Excel tablosunda ara</b>\n\nİhlal, madde veya anahtar kelime yazın.', parse_mode=ParseMode.HTML, reply_markup=kb([[('🏠 Ana Menü', 'menu')]]))
        context.user_data.update(mode='source_search', source=key)
        return await q.edit_message_text(
            f'📚 <b>{esc(SRC_LABEL.get(key, key))}</b>\n\nMadde numarası yazabilir (örn. <code>36</code>) veya konu arayabilirsiniz. İçsuya özgü maddeler varsayılan olarak gösterilmez.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📑 Maddeleri Listele', f'srclist:{key}:0')], [('🏠 Menü', 'menu')]]),
        )
    if data.startswith('srclist:'):
        _, source, page = data.split(':')
        return await show_source_list(q, source, int(page))
    if data.startswith('artp:'):
        _, source, article, page = data.split(':')
        return await show_article(q, source, int(article), int(page))
    if data.startswith('art:'):
        _, source, article = data.split(':')
        return await show_article(q, source, int(article), 0)


    if data.startswith('rule:'):
        return await show_rule(q, data.split(':', 1)[1])
    if data.startswith('field:'):
        return await show_field(q, data.split(':', 1)[1])

    if data == 'vessel:menu':
        return await q.edit_message_text(
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
        return await show_admin_panel(q, section)

    if data == 'gear:vis:menu':
        return await show_gear_visual_menu(q)
    if data.startswith('gear:vis:item:'):
        return await show_gear_visual_item(q, data.split(':', 3)[3])

    if data == 'species:vis:menu':
        return await show_species_visual_menu(q)
    if data.startswith('species:vis:item:'):
        return await show_species_visual_item(q, data.split(':', 3)[3])


    if data == 'turcizelge:menu':
        rows = []
        for c in TUR_CIZELGESI:
            rows.append([(f"{c['title']}", f"turcizelge:view:{c['id']}")])
        rows.append([('🔎 Detaylı Tür Arama / Görsel Rehber', 'species:menu')])
        rows.append([('🏠 Ana Menü', 'menu')])
        return await q.edit_message_text('<b>📖 PRATİK TÜR ÇİZELGESİ</b>\n\nİncelemek istediğiniz başlığı seçin:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if data.startswith('turcizelge:view:'):
        cid = data.split(':', 2)[2]
        c_main = next((c for c in TUR_CIZELGESI if c['id'] == cid), None)
        if c_main:
            rows = []
            if c_main.get('sub'):
                for s in c_main['sub']:
                    rows.append([(f"{s['title']}", f"turcizelge:sub:{c_main['id']}:{s['id']}")])
            
            if rows:
                # If there are subcategories, show them as buttons. If there are items too, we should theoretically show them as text above or below, but we don't have such cases.
                rows.append([('🔙 Çizelge Menüsü', 'turcizelge:menu')])
                rows.append([('🏠 Ana Menü', 'menu')])
                return await q.edit_message_text(f"<b>{esc(c_main['title'])}</b>\n\nLütfen bir seçenek belirleyin:", parse_mode=ParseMode.HTML, reply_markup=kb(rows))
            else:
                out = f"<b>{esc(c_main['title'])}</b>\n\n{c_main.get('content', '')}\n"
                if c_main.get('items'):
                    for it in c_main['items']:
                        d = it.get('details', {})
                        t_adi = d.get('Türkçe Adı', '')
                        l_adi = d.get('Latince Adı', '')
                        line = f"▪️ <b>{esc(t_adi)}</b> ({esc(l_adi).replace('*', '')})"
                        for k, v in d.items():
                            if k not in ('Türkçe Adı', 'Latince Adı', 'Tür', 'Türü'):
                                line += f" - <b>{esc(k)}:</b> {esc(v)}"
                        out += line + "\n"

                if len(out) > 4000:
                    lines = out.split('\n')
                    chunks = []
                    curr = ""
                    for line in lines:
                        if len(curr) + len(line) > 3900:
                            chunks.append(curr)
                            curr = line + '\n'
                        else:
                            curr += line + '\n'
                    if curr: chunks.append(curr)
                    
                    await q.edit_message_text(chunks[0], parse_mode=ParseMode.HTML)
                    for chunk in chunks[1:-1]:
                        await q.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                    return await q.message.reply_text(chunks[-1], parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Çizelge Menüsü', 'turcizelge:menu')], [('🏠 Ana Menü', 'menu')]]))
                else:
                    return await q.edit_message_text(out, parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Çizelge Menüsü', 'turcizelge:menu')], [('🏠 Ana Menü', 'menu')]]))

    if data.startswith('turcizelge:sub:'):
        _, _, cid, sid = data.split(':')
        c_main = next((c for c in TUR_CIZELGESI if c['id'] == cid), None)
        if c_main:
            s_sub = next((s for s in c_main['sub'] if s['id'] == sid), None)
            if s_sub:
                out = f"<b>{esc(s_sub['title'])}</b>\n\n{s_sub.get('content', '')}\n"
                if s_sub.get('items'):
                    for it in s_sub['items']:
                        d = it.get('details', {})
                        t_adi = d.get('Türkçe Adı', '')
                        l_adi = d.get('Latince Adı', '')
                        line = f"▪️ <b>{esc(t_adi)}</b> ({esc(l_adi).replace('*', '')})"
                        for k, v in d.items():
                            if k not in ('Türkçe Adı', 'Latince Adı', 'Tür', 'Türü'):
                                line += f" - <b>{esc(k)}:</b> {esc(v)}"
                        out += line + "\n"
                
                # Split output if too long
                if len(out) > 4000:
                    lines = out.split('\n')
                    chunks = []
                    curr = ""
                    for line in lines:
                        if len(curr) + len(line) > 3900:
                            chunks.append(curr)
                            curr = line + '\n'
                        else:
                            curr += line + '\n'
                    if curr: chunks.append(curr)
                    
                    await q.edit_message_text(chunks[0], parse_mode=ParseMode.HTML)
                    for chunk in chunks[1:-1]:
                        await q.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                    return await q.message.reply_text(chunks[-1], parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Üst Başlık', f"turcizelge:view:{cid}")], [('🏠 Ana Menü', 'menu')]]))
                else:
                    return await q.edit_message_text(out, parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 Üst Başlık', f"turcizelge:view:{cid}")], [('🏠 Ana Menü', 'menu')]]))

    if data == 'species:menu':
        return await q.edit_message_text(
            '🐟 <b>TÜR / BOY / ZAMAN</b>\n\nHangi faaliyet?',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([
                [('🎣 Ticari (6/1)', 'species:kind:commercial'), ('🎣 Amatör (6/2)', 'species:kind:amateur')],
                [('🎣 Tamamen yasak tür', 'species:kind:prohibited')],
                [('🔎 Görsel Balık Teşhis Rehberi', 'species:vis:menu')],
                [('🔙 Geri', 'turcizelge:menu')],
                [('🏠 Ana Menü', 'menu')],
            ]),
        )
    if data.startswith('species:kind:'):
        kind = data.rsplit(':', 1)[1]
        context.user_data.update(mode='species_search', species_kind=kind)
        return await q.edit_message_text('Tür adını yazın. Örnek: <code>kalkan</code>, <code>mavi yengeç</code>, <code>palamut</code>.', parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Tür Menüsü', 'species:menu')]]))
    if data.startswith('sp:'):
        _, kind, sid = data.split(':')
        return await show_species(q, kind, int(sid), context)

    if data.startswith('pen:length:'):
        pid=int(data.rsplit(':',1)[1])
        context.user_data.update(mode='penalty_length',penalty_pid=pid)
        return await q.edit_message_text('🚤 Gemi tam boyunu metre olarak yazın. Örnek: <code>17.4</code>',parse_mode=ParseMode.HTML,reply_markup=kb([[('↩️ Ceza Kartı',f'pen:{pid}')]]))
    if data.startswith('pen:'):
        return await show_penalty(q, int(data.split(':', 1)[1]), context)
    if data.startswith('raw:'):
        row = db.raw_row(int(data.split(':', 1)[1]))
        if not row:
            return await q.answer('Excel satırı bulunamadı.', show_alert=True)
        return await q.edit_message_text(
            f'📊 <b>Excel satır {row["source_row"]}</b>\n\n<code>{esc(row["raw_text"])}</code>\n\n<i>Değerler yüklediğiniz Excel kaynağındaki haliyle gösterilir.</i>',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('↩️ Ana Menü', 'menu')]]),
        )

    if data == 'audit:start':
        return await audit_start(q, context)
    if data.startswith('audit:region:'):
        context.user_data['audit_region'] = data.rsplit(':', 1)[1]
        return await audit_choose_activity(q, context)
    if data.startswith('audit:activity:'):
        context.user_data['audit_activity'] = data.rsplit(':', 1)[1]
        return await audit_choose_length(q, context)
    if data.startswith('audit:length:'):
        choice = data.rsplit(':', 1)[1]
        if choice == 'exact':
            context.user_data['mode'] = 'audit_length_exact'
            return await q.edit_message_text(
                '🚤 <b>GEMİ / TEKNE TAM BOYU</b>\n\nTam boyu metre olarak yazın. Örnek: <code>17.4</code>',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('🏠 Ana Menü', 'menu')]])
            )
        _, rule_value = LENGTH_BANDS[choice]
        context.user_data['audit_length_band'] = choice
        context.user_data['audit_length'] = rule_value
        context.user_data.pop('audit_length_exact', None)
        return await audit_choose_date(q, context)
    if data == 'audit:datemenu':
        return await audit_choose_date(q, context)
    if data == 'audit:subjectmenu':
        return await audit_choose_subject(q, context)
    if data == 'audit:gearmenu':
        return await audit_choose_gear(q, context)
    if data == 'audit:date:today':
        context.user_data['audit_date'] = datetime.now(TZ).date().isoformat()
        return await audit_choose_subject(q, context)
    if data == 'audit:date:other':
        context.user_data['mode'] = 'audit_date'
        return await q.edit_message_text(
            '📅 <b>OLAY / KONTROL TARİHİ</b>\n\nTarihi <code>GG.AA.YYYY</code> biçiminde yazın. Örnek: <code>20.05.2026</code>.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📅 Bugünü Kullan', 'audit:date:today')], [('↩️ Tarih Seçimine Dön', 'audit:datemenu'), ('🏠 Ana Menü', 'menu')]])
        )
    if data.startswith('audit:subject:'):
        subject = data.rsplit(':', 1)[1]
        context.user_data['audit_subject'] = subject
        if subject == 'fishing':
            return await audit_choose_gear(q, context)
        if subject == 'species':
            context.user_data.update(mode='audit_species_search', species_kind=context.user_data.get('audit_activity','commercial'), guided_species=True)
            return await q.edit_message_text(
                '🐟 <b>ÜRÜN / TÜR</b>\n\nKontrol edilen türün adını yazın. Örnek: <code>kalkan</code>, <code>palamut</code>, <code>hamsi</code>.',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('➡️ Tür belirtmeden devam', 'audit:guided:check')], [('🏠 Ana Menü', 'menu')]])
            )
        return await audit_quick_start(q, context)
    if data.startswith('audit:gear:'):
        context.user_data['audit_gear'] = data.split(':', 2)[2]
        if context.user_data.get('guided_active'):
            return await audit_after_gear(q, context)
        return await audit_gear_result(q, context)
    if data == 'audit:guided:species':
        context.user_data.update(mode='audit_species_search', species_kind=context.user_data.get('audit_activity','commercial'), guided_species=True)
        return await q.edit_message_text(
            '🐟 <b>TÜRÜ YAZIN</b>\n\nTür adını yazın. Tür bilinmiyorsa tür belirtmeden devam edebilirsiniz.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('➡️ Tür belirtmeden devam', 'audit:guided:check')], [('🏠 Ana Menü', 'menu')]])
        )
    if data == 'audit:guided:check':
        context.user_data.pop('mode', None)
        return await audit_quick_start(q, context)
    if data == 'audit:hub':
        return await audit_hub_edit(q, context)
        return await amateur_classification_start(q, context)
    if data.startswith('classify:ans:'):
        _, _, idx, ans = data.split(':', 3)
        return await amateur_classification_answer(q, context, int(idx), ans)
    if data == 'audit:quick:start':
        return await audit_quick_start(q, context)
    if data.startswith('audit:quick:ans:'):
        _, _, _, idx, ans = data.split(':', 4)
        return await audit_quick_answer(q, context, int(idx), ans)

    if data == 'calc:menu':
        return await calc_menu(q)
    if data == 'calc:tuna':
        context.user_data.update(mode='tuna_total')
        return await q.edit_message_text('🧮 <b>Mavi yüzgeçli orkinos %5 adet toleransı</b>\n\nKontrol edilen toplam mavi yüzgeçli orkinos adedini yazın.\n\n<i>6/1 Md.18: 8–30 kg veya 75–115 cm aralığındaki bireyler için sayı bazında %5 tolerans hükmü esas alınır.</i>',parse_mode=ParseMode.HTML,reply_markup=kb([[('📚 6/1 Md.18','art:61:18')],[('↩️ Hesaplayıcılar','calc:menu')]]))
    if data.startswith('calc:tol:'):
        species = data.rsplit(':', 1)[1]
        context.user_data.update(mode='tol_total', tol_species=species)
        limit = 15 if species in {'hamsi', 'sardalya', 'istavrit'} else 5
        return await q.edit_message_text(f'🧮 <b>Ticari küçük boy toleransı — %{limit}</b>\n\nToplam av ağırlığını kg olarak yazın.', parse_mode=ParseMode.HTML, reply_markup=kb([[('🔙 İptal', 'calc:menu')]]))

    if data == 'fav:list':
        return await show_favorites(q, uid)
    if data == 'history':
        return await show_history(q, uid)
    if data == 'about':
        return await show_about(q)
    if data == 'help':
        db.log(uid, 'help')
        return await q.edit_message_text(
            HELP_TEXT, parse_mode=ParseMode.HTML,
            reply_markup=kb([[('🏠 Ana Menü', 'menu')]]),
        )
    if data.startswith('fav:add:'):
        _, _, item_type, item_id = data.split(':', 3)
        db.add_fav(uid, item_type, item_id)
        return await q.answer('Favorilere eklendi.')


async def show_sources(q):
    rows = []
    for source in db.list_sources():
        rows.append([(f'{source["type"]}: {source["title"][:29]}', f'src:{source["key"]}')])
    rows.append([('↩️ Ana Menü', 'menu')])
    await q.edit_message_text(
        '📚 <b>MEVZUAT KAYNAKLARI</b>\n\nDeniz görev alanındaki denetimlerde kullanılan mevzuat ve yaptırım kaynaklarını buradan inceleyebilirsiniz. İçsuya özgü hükümler normal görev akışında gösterilmez.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


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


async def show_source_list(q, source, page=0):
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
    await q.edit_message_text(
        f'📑 <b>{esc(SRC_LABEL.get(source,source))} — DENİZ/GENEL MADDELER</b>\n\nSayfa {page+1}/{pages}. İçsuya özgü maddeler bu listede gösterilmez.',
        parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def show_article(q, source, article, page=0, context=None):
    row = db.get_article(source, article)
    if not row:
        return await q.answer('Madde bulunamadı.', show_alert=True)
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
    rows.append([('⭐ Favoriye Ekle', f'fav:add:article:{source}-{article}'), ('📑 Madde Listesi', f'srclist:{source}:0')])
    if context and context.user_data.get('guide_key'):
        rows.append([('🔙 Uygunsuzluk Listesine Dön', 'guide:badmenu')])
    rows.append([('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def show_field(q, category):
    rules = db.search_rules(cat=category, limit=20)
    rows = [[(r['title'][:45], f'rule:{r["id"]}')] for r in rules]
    rows.append([('↩️ Ana Menü', 'menu')])
    await q.edit_message_text(f'🛡️ <b>{esc(category)}</b>\n\nKontrol kartını seçin:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def show_rule(q, rule_id):
    row = db.get_rule(rule_id)
    if not row:
        return await q.answer('Kontrol kartı bulunamadı.', show_alert=True)
    refs = json.loads(row['refs'])
    buttons, ref_text = [], []
    for ref in refs:
        label = SRC_LABEL.get(ref['s'], ref['s'])
        ref_text.append(f'{label} Md. {ref["a"]}')
        buttons.append((f'📚 {label} {ref["a"]}', f'art:{ref["s"]}:{ref["a"]}'))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([('🔙 Geri', f"field:{row['cat']}"), ('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(
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


async def show_species_visual_menu(q):
    rows = []
    for key, item in SPECIES_VISUAL_GUIDE.items():
        rows.append([(f'🐟 {item["title"]}', f'species:vis:item:{key}')])
    rows.append([('↩️ Tür Menüsü', 'species:menu'), ('🏠 Ana Menü', 'menu')])
    text = (
        '🖼️ <b>GÖRSEL BALIK TEŞHİS VE AYRIM REHBERİ</b>\n\n'
        'Sahada sıkça karıştırılan türleri ve kritik boy kademelerini görsel tanı kriterleriyle inceleyin:\n'
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def show_species_visual_item(q, key):
    item = SPECIES_VISUAL_GUIDE.get(key)
    if not item:
        return await q.answer('Görsel kart bulunamadı.', show_alert=True)
    text = f'🖼️ <b>{esc(item["title"])}</b>\n'
    text += f'<b>Tür(ler):</b> {esc(item["species"])}\n'
    text += f'📏 <b>Ölçü Kriteri:</b> {esc(item["min_cm"])}\n\n'
    text += '<b>Ayırt Edici Tanı Kriterleri:</b>\n'
    for pt in item['key_points']:
        text += f'• {pt}\n'
    if item.get('photo_url'):
        text += f'\n<a href="{item["photo_url"]}">&#8205;</a><i>(Fotoğraf önizlemesi yukarıda görüntülenmektedir)</i>\n'
    rows = [[('↩️ Görsel Rehber', 'species:vis:menu'), ('🐟 Tür Menüsü', 'species:menu')]]
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def show_gear_visual_menu(q):
    rows = []
    for key, item in GEAR_VISUAL_GUIDE.items():
        rows.append([(f'{item["title"][:40]}', f'gear:vis:item:{key}')])
    rows.append([('🔙 Gemi / Donanım Menüsü', 'vessel:menu'), ('🏠 Ana Menü', 'menu')])
    text = (
        '🚫 <b>YASAK AV ARAÇLARI GÖRSEL TESPİT REHBERİ</b>\n\n'
        'Sahada şüpheli veya yasaklı av donanımlarını tespit etmek için kılavuz kartlarını seçin:\n'
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def show_gear_visual_item(q, key):
    item = GEAR_VISUAL_GUIDE.get(key)
    if not item:
        return await q.answer('Donanım kartı bulunamadı.', show_alert=True)
    text = f'🚫 <b>{esc(item["title"])}</b>\n'
    text += f'⚠️ <b>Durum:</b> {esc(item["status"])}\n\n'
    text += f'{item["description"]}\n'
    rows = [[('↩️ Yasak Araçlar Listesi', 'gear:vis:menu'), ('🏠 Ana Menü', 'menu')]]
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def in_date_range(today, span):
    start, end = span.split('/')
    sm, sd = map(int, start.split('-'))
    em, ed = map(int, end.split('-'))
    x, lo, hi = (today.month, today.day), (sm, sd), (em, ed)
    return lo <= x <= hi if lo <= hi else (x >= lo or x <= hi)


async def show_species(q, kind, sid, context=None):
    row = db.get_species(kind, sid)
    if not row:
        return await q.answer('Tür bulunamadı.', show_alert=True)
    bans = json.loads(row['time_bans'])
    today = audit_date(context) if context is not None and context.user_data.get('guided_active') else datetime.now(TZ).date()
    closed = any(in_date_range(today, span) for span in bans)
    title = 'Ticari — 6/1' if kind == 'commercial' else 'Amatör — 6/2'
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

    source = '61' if kind == 'commercial' else '62'
    article = 17 if kind == 'commercial' else 15
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
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


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


async def show_penalty(q, pid, context):
    row = db.get_penalty(pid)
    if not row:
        return await q.answer('Ceza kaydı bulunamadı.', show_alert=True)
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
        'Bot farklı katsayıları kendiliğinden üst üste çarpmaz. Somut olayın maddi unsurları ve asli mevzuat maddesi ayrıca kontrol edilmelidir.</i>'
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
    rows.append([('⭐ Favoriye Ekle', f'fav:add:penalty:{pid}'), ('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


def guide_ref_label(ref):
    source, article = ref
    return f'{SRC_LABEL.get(source, source)} Md.{article}'


def guide_current(context):
    key = context.user_data.get('guide_key')
    return GUIDES.get(key)


def guide_short(text, n=82):
    s = str(text or '').strip()
    return s if len(s) <= n else s[:n-1].rstrip() + '…'


async def guide_menu(q, context):
    db.log(q.from_user.id, 'guide_menu')
    rows = []
    for i in range(0, len(GUIDE_LIST), 2):
        line = []
        for g in GUIDE_LIST[i:i+2]:
            line.append((f'🚤 {g["short_title"][:28]}', f'guide:open:{g["key"]}'))
        rows.append(line)
    rows.append([('🚨 Yönlendirilmiş Denetim', 'audit:start'), ('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(
        '📋 <b>TEKNE TÜRÜNE GÖRE SAHA KILAVUZU</b>\n\n'
        'Kontrol edeceğiniz tekne/av yöntemi türünü seçin. Her föy yalnız o faaliyette sahada bakılması gereken '
        'belge, donanım, av aracı, yer-zaman ve ürün kontrollerini açar.\n\n'
        '<i>İçsulara özgü kontroller bu menüye alınmamıştır.</i>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


async def guide_open(q, context, key):
    g = GUIDES.get(key)
    if not g:
        return await q.answer('Kontrol föyü bulunamadı.', show_alert=True)
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
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def guide_view(q, context, key, page=0):
    g = GUIDES.get(key)
    if not g:
        return await q.answer('Kontrol föyü bulunamadı.', show_alert=True)
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
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def guide_refs(q, context, key):
    g = GUIDES.get(key)
    if not g:
        return await q.answer('Kontrol föyü bulunamadı.', show_alert=True)
    rows = []
    buttons = []
    for source, article in g.get('refs') or []:
        if db.get_article(source, int(article)):
            buttons.append((guide_ref_label((source, article)), f'art:{source}:{article}'))
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i+2])
    rows.append([('↩️ Föye Dön', f'guide:open:{key}'), ('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(
        f'📚 <b>{esc(g["short_title"])} — KAYNAK MADDELER</b>\n\n'
        'Föydeki kontrollerin dayandığı kaynak maddeler aşağıdadır. Somut uygunsuzlukta ilgili maddenin tam metni ve ceza tablosu birlikte doğrulanmalıdır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


async def guide_start(q, context, key):
    g = GUIDES.get(key)
    if not g:
        return await q.answer('Kontrol föyü bulunamadı.', show_alert=True)
    context.user_data['guide_key'] = key
    context.user_data['guide_answers'] = [None] * len(g['rows'])
    context.user_data['guide_measurements'] = {}
    context.user_data.pop('mode', None)
    db.log(q.from_user.id, 'guide_start', g['short_title'])
    return await guide_render(q, context, 0)


async def guide_render(q, context, idx):
    g = guide_current(context)
    if not g:
        return await q.answer('Aktif kontrol föyü bulunamadı.', show_alert=True)
    if idx < 0:
        idx = 0
    if idx >= len(g['rows']):
        return await guide_finish(q, context)
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
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def guide_answer(q, context, idx, ans):
    g = guide_current(context)
    if not g or ans not in {'ok','bad','skip'}:
        return await q.answer('Kontrol oturumu bulunamadı.', show_alert=True)
    answers = context.user_data.setdefault('guide_answers', [None] * len(g['rows']))
    while len(answers) < len(g['rows']):
        answers.append(None)
    if 0 <= idx < len(answers):
        answers[idx] = ans
    next_idx = idx + 1
    if next_idx >= len(g['rows']):
        return await guide_finish(q, context)
    return await guide_render(q, context, next_idx)


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


async def guide_finish(q, context):
    g, ok, bad, unchecked = guide_result_parts(context)
    if not g:
        return await q.answer('Aktif kontrol föyü bulunamadı.', show_alert=True)
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
    rows.append([('🔄 Aynı Föyü Yenile', f'guide:start:{g["key"]}')])
    if context.user_data.get('guided_active'):
        rows.append([('🚨 Denetime Dön', 'audit:hub'), ('🏠 Ana Menü', 'menu')])
    else:
        rows.append([('↩️ Föye Dön', f'guide:open:{g["key"]}'), ('🏠 Ana Menü', 'menu')])
    db.log(q.from_user.id, 'guide_finish', f'{g["short_title"]}: bad={len(bad)}, unchecked={len(unchecked)}')
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def guide_bad_menu(q, context):
    g, _, bad, _ = guide_result_parts(context)
    if not g:
        return await q.answer('Aktif kontrol föyü bulunamadı.', show_alert=True)
    if not bad:
        return await q.answer('Uygunsuz işaretlenmiş kontrol yok.', show_alert=True)
    rows = []
    for idx, item in bad:
        rows.append([(f'⚖️ {idx+1}. {guide_short(item["text"], 38)}', f'guide:pen:{idx}')])
    rows.append([('↩️ Sonuca Dön', 'guide:result'), ('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(
        f'⚖️ <b>{esc(g["short_title"])} — UYGUNSUZLUKLAR</b>\n\n'
        'Ceza/yaptırım tablosunda kontrol etmek istediğiniz uygunsuzluğu seçin.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


async def guide_penalty_search(q, context, idx):
    g, _, _, _ = guide_result_parts(context)
    if not g or idx < 0 or idx >= len(g['rows']):
        return await q.answer('Kontrol maddesi bulunamadı.', show_alert=True)
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
    await q.edit_message_text(
        f'⚖️ <b>YAPTIRIM ARAMASI</b>\n\n'
        f'Kontrol maddesi: {esc(guide_short(item["text"], 150))}\n\n'
        f'Arama anahtarı: <code>{esc(query)}</code>\n'
        f'Yapılandırılmış sonuç: <b>{len(results)}</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


async def guide_measure_start(q, context):
    g = guide_current(context)
    if not g:
        return await q.answer('Önce bir tekne kontrol föyü seçin.', show_alert=True)
    context.user_data.setdefault('guide_measurements', {})
    context.user_data['guide_measure_idx'] = 0
    context.user_data['mode'] = 'guide_measure'
    return await guide_measure_prompt_q(q, context)


async def guide_measure_prompt_q(q, context):
    g = guide_current(context)
    idx = int(context.user_data.get('guide_measure_idx', 0))
    fields = g.get('measure_fields') if g else []
    if not g or idx >= len(fields):
        context.user_data.pop('mode', None)
        return await q.edit_message_text(
            '📐 Ölçüm/kayıt alanları tamamlandı.',
            reply_markup=kb([[('📊 Kontrol Sonucunu Aç', 'guide:result'), ('↩️ Föye Dön', f'guide:open:{g["key"]}')]])
        )
    field = fields[idx]
    old = (context.user_data.get('guide_measurements') or {}).get(field)
    extra = f'\nMevcut değer: <b>{esc(old)}</b>' if old else ''
    await q.edit_message_text(
        f'📐 <b>{esc(g["short_title"])} — ÖLÇÜM/KAYIT</b>\n\n'
        f'{idx+1}/{len(fields)} — <b>{esc(field)}</b>{extra}\n\n'
        'Değeri mesaj olarak yazın. Birim alan adında belirtilmemişse kısa açıklama da yazabilirsiniz.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([[('⏭️ Kontrol Edilmedi / Atla', 'guide:measure:skip')], [('📊 Sonuca Dön', 'guide:result')]]),
    )


async def guide_measure_skip(q, context):
    g = guide_current(context)
    if not g:
        return await q.answer('Aktif föy bulunamadı.', show_alert=True)
    idx = int(context.user_data.get('guide_measure_idx', 0))
    fields = g.get('measure_fields') or []
    if idx < len(fields):
        context.user_data.setdefault('guide_measurements', {})[fields[idx]] = 'Kontrol edilmedi'
    context.user_data['guide_measure_idx'] = idx + 1
    return await guide_measure_prompt_q(q, context)


async def guide_from_gear(q, context):
    if context.user_data.get('audit_activity') == 'amateur':
        return await guide_open(q, context, '14_Amator_Tekne')
    gear = context.user_data.get('audit_gear')
    keys = GUIDE_GEAR_MAP.get(gear, [])
    if not keys:
        return await guide_menu(q, context)
    if len(keys) == 1:
        return await guide_open(q, context, keys[0])
    rows = [[(f'🚤 {GUIDES[k]["short_title"][:35]}', f'guide:open:{k}')] for k in keys]
    rows.append([('↩️ Av Aracı Seçimine Dön', 'audit:gearmenu'), ('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(
        f'📋 <b>{esc(str(gear).title())} — HANGİ FAALİYET?</b>\n\n'
        'Bu av aracı birden fazla özel faaliyette kullanılabildiği için uygun kontrol föyünü seçin.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


async def audit_start(q, context):
    context.user_data.clear()
    context.user_data['guided_active'] = True
    db.log(q.from_user.id, 'audit_start')
    await q.edit_message_text(
        '🚨 <b>YENİ DENETİM — 1. ADIM</b>\n\n'
        'Önce <b>deniz bölgesini</b> seçin. Sonraki sorular seçtiğiniz bölgeye göre daraltılacaktır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('🌊 Karadeniz', 'audit:region:karadeniz'), ('🌊 Marmara', 'audit:region:marmara')],
            [('🌉 İstanbul Boğazı', 'audit:region:istanbul'), ('🌉 Çanakkale Boğazı', 'audit:region:canakkale')],
            [('🌊 Ege', 'audit:region:ege'), ('🌊 Akdeniz', 'audit:region:akdeniz')],
            [('🧭 Uluslararası / MEB', 'audit:region:international')],
            [('↩️ Ana Menü', 'menu')],
        ]),
    )


async def audit_choose_activity(q, context):
    region = REGION_LABEL.get(context.user_data.get('audit_region'), context.user_data.get('audit_region'))
    await q.edit_message_text(
        '🚨 <b>YENİ DENETİM — 2. ADIM</b>\n\n'
        f'Bölge: <b>{esc(region)}</b>\n\n'
        'Kontrol edilen faaliyet hangi kapsamda?',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('🚤 Ticari avcılık', 'audit:activity:commercial'), ('🎣 Amatör avcılık', 'audit:activity:amateur')],
            [('↩️ Bölgeyi Değiştir', 'audit:start'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


async def audit_choose_length(q, context):
    activity = context.user_data.get('audit_activity')
    await q.edit_message_text(
        '🚨 <b>YENİ DENETİM — 3. ADIM</b>\n\n'
        f'Faaliyet: <b>{"Ticari" if activity == "commercial" else "Amatör"}</b>\n\n'
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


async def audit_choose_date(q, context):
    await q.edit_message_text(
        '🚨 <b>YENİ DENETİM — 4. ADIM</b>\n\n'
        f'Bölge: <b>{esc(REGION_LABEL.get(context.user_data.get("audit_region"), "—"))}</b>\n'
        f'Faaliyet: <b>{"Ticari" if context.user_data.get("audit_activity") == "commercial" else "Amatör"}</b>\n'
        f'Gemi/Tekne: <b>{esc(audit_length_label(context))}</b>\n\n'
        'Olay veya kontrol tarihi nedir? Tarih; kapalı dönem ve tür zaman yasaklarının değerlendirilmesinde kullanılır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('📅 Bugün', 'audit:date:today'), ('🗓 Başka tarih', 'audit:date:other')],
            [('↩️ Gemi Boyunu Değiştir', f'audit:activity:{context.user_data.get("audit_activity")}'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


async def audit_choose_subject(q, context):
    activity = context.user_data.get('audit_activity')
    d = audit_date(context)
    text = (
        '🚨 <b>YENİ DENETİM — 5. ADIM</b>\n\n'
        f'🌊 {esc(REGION_LABEL.get(context.user_data.get("audit_region"), "—"))}\n'
        f'⚓ {"Ticari" if activity == "commercial" else "Amatör"} · {esc(audit_length_label(context))}\n'
        f'📅 {d.strftime("%d.%m.%Y")}\n\n'
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
    else:
        rows = [
            [('🎣 Avcılık faaliyeti', 'audit:subject:fishing'), ('🐟 Ürün / Tür', 'audit:subject:species')],
            [('📦 Satış / Nakil', 'audit:subject:transport'), ('🔎 Ticari Nitelik Kontrolü', 'classify:start')],
        ]
    rows += [[('↩️ Tarihi Değiştir', 'audit:datemenu'), ('🏠 Ana Menü', 'menu')]]
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def audit_choose_gear(q, context):
    activity = context.user_data.get('audit_activity')
    if activity == 'commercial':
        rows = [
            [('Gırgır', 'audit:gear:gırgır'), ('Dip trolü', 'audit:gear:dip trolü')],
            [('Ortasu trolü', 'audit:gear:ortasu trolü'), ('Algarna', 'audit:gear:algarna')],
            [('Manyat', 'audit:gear:manyat'), ('Dreç', 'audit:gear:dreç')],
            [('Uzatma ağı', 'audit:gear:uzatma ağı'), ('Parakete', 'audit:gear:parakete')],
            [('Işıkla avcılık', 'audit:gear:ışık'), ('Dalma / Sualtı', 'audit:gear:dalma')],
            [('Deniz Patlıcanı', 'audit:gear:deniz patlıcanı'), ('Sünger / Kestane', 'audit:gear:denizkestanesi')],
            [('Monofilament', 'audit:gear:monofilament'), ('Olta / Çapari / Diğer', 'audit:gear:diğer')],
        ]
    else:
        rows = [
            [('Olta / Çapari', 'audit:gear:olta'), ('Yemlik uzatma ağı', 'audit:gear:yemlik uzatma ağı')],
            [('Sualtı tüfeği / Dalma', 'audit:gear:dalma'), ('Parakete', 'audit:gear:parakete')],
            [('Turizm (Ek-9)', 'audit:gear:turizm'), ('Tırıvırı / Paraşüt', 'audit:gear:tırıvırı')],
            [('Diğer', 'audit:gear:diğer')],
        ]
    rows += [[('↩️ Konuyu Değiştir', 'audit:subjectmenu'), ('🏠 Ana Menü', 'menu')]]
    await q.edit_message_text(
        '🚨 <b>YENİ DENETİM — 6. ADIM</b>\n\n'
        'Kullanılan veya kontrol edilen <b>av aracı / yöntemi</b> seçin.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb(rows),
    )


async def audit_after_gear(q, context):
    gear = context.user_data.get('audit_gear')
    flags = build_context_flags(context)
    warning = ''
    if flags:
        warning = '\n\n' + '\n'.join(f'🔴 {esc(x["tag"])}' for x in flags[:3])
    await q.edit_message_text(
        '🚨 <b>YENİ DENETİM — 7. ADIM</b>\n\n'
        f'Av aracı/yöntem: <b>{esc(gear)}</b>{warning}\n\n'
        'Kontrol edilen ürün/tür belli mi?',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('🐟 Türü seç / yaz', 'audit:guided:species')],
            [('➡️ Tür belirtmeden devam', 'audit:guided:check')],
            [('📋 Bu Av Aracının Kontrol Föyü', 'guide:fromgear')],
            [('↩️ Av Aracını Değiştir', 'audit:gearmenu'), ('🏠 Ana Menü', 'menu')],
        ]),
    )


async def audit_hub_edit(q, context):
    activity = context.user_data.get('audit_activity')
    gear = context.user_data.get('audit_gear')
    species = context.user_data.get('audit_species_name')
    subject = context.user_data.get('audit_subject')
    text = (
        '🚨 <b>DENETİM BAĞLAMI</b>\n\n'
        f'🌊 Bölge: <b>{esc(REGION_LABEL.get(context.user_data.get("audit_region"), "—"))}</b>\n'
        f'⚓ Faaliyet: <b>{"Ticari" if activity == "commercial" else "Amatör"}</b>\n'
        f'🚤 Gemi/Tekne: <b>{esc(audit_length_label(context))}</b>\n'
        f'📅 Tarih: <b>{audit_date(context).strftime("%d.%m.%Y")}</b>\n'
    )
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
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


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
        if gear == 'parakete':
            add('Denizlerde amatör avcılıkta parakete kullanımı', ('62', 16), 'amatör avcılık kurallarının ihlali')
        if gear == 'tırıvırı':
            add('Tırıvırı / paraşüt kullanımı', ('62', 8), 'amatör avcılık kurallarının ihlali')

    sid = context.user_data.get('audit_species_id')
    skind = context.user_data.get('audit_species_kind')
    if sid and skind in {'commercial', 'amateur'}:
        row = db.get_species(skind, int(sid))
        if row:
            bans = json.loads(row['time_bans'] or '[]')
            if bans and any(in_date_range(day, span) for span in bans):
                ref = ('61', int(row['article_time'] or 17)) if skind == 'commercial' else ('62', 15)
                pq = 'yasak zamanda avcılık' if skind == 'commercial' else 'amatör avcılık kurallarının ihlali'
                add(f'{row["name"]}: seçilen tarih zaman yasağına denk geliyor', ref, pq)
    return flags


def build_quick_questions(context):
    activity = context.user_data.get('audit_activity')
    subject = context.user_data.get('audit_subject') or 'fishing'
    length = audit_rule_length(context)
    gear = context.user_data.get('audit_gear')
    day = audit_date(context)
    qs = []

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
            qs += [
                _q('Seçilen av aracının yer, saha, mesafe, derinlik ve saat şartlarının tamamı uygun mu?', 'yes', ('61', 50), 'Yer / saha / mesafe / derinlik'),
                _q('Yasak dönem nedeniyle gemide veya istihsal yerinde bulundurulması yasak bir av aracı bulunmuyor mu?', 'yes', ('61', 50), 'Yasak av aracı bulundurma'),
            ]
            if gear == 'gırgır':
                qs += [
                    _q('Gırgır için asgari su derinliği ve ağ derinliği şartları uygun mu?', 'yes', ('61', 12), 'Gırgır derinlik şartları', penalty_query='gırgır'),
                    _q('Gırgır ağı için gerekli Ağ Ölçüm Belgesi mevcut ve geçerli mi?', 'yes', ('61', 12), 'Ağ Ölçüm Belgesi', penalty_query='gırgır ağı ölçüm belgesi'),
                ]
            elif gear in {'dip trolü', 'ortasu trolü'}:
                qs.append(_q('Trol faaliyeti saha, zaman, kıyı mesafesi/derinlik, ağ gözü ve diğer teknik şartlara uygun mu?', 'yes', ('61', 10 if gear == 'dip trolü' else 11), 'Trol teknik/saha şartları', penalty_query='trol'))
            elif gear == 'ışık':
                qs.append(_q('Işıkla avcılık izin, güç, derinlik, yetiştiricilik tesisi mesafesi ve diğer özel şartlara uygun mu?', 'yes', ('61', 13), 'Işıkla avcılık şartları', penalty_query='ışık ile avcılık'))
            elif gear == 'algarna':
                qs.append(_q('Algarna faaliyeti hedef tür, izin, saat, saha ve teknik ölçü şartlarına uygun mu?', 'yes', ('61', 14), 'Algarna şartları', penalty_query='algarna'))
            elif gear == 'parakete':
                qs.append(_q('Parakete işaretleme ve iğne şartları uygun mu; hedef tür kalkan ise parakete kullanılmıyor mu?', 'yes', ('61', 15), 'Parakete şartları', penalty_query='parakete'))
            if gear in {'algarna', 'manyat', 'dreç', 'dalma'} and day >= datetime(2026, 9, 1, tzinfo=TZ).date():
                qs.append(_q('Bu faaliyet için 1 Eylül 2026 itibarıyla istenen gemi izleme/kayıt cihazı işler ve çalışır durumda mı?', 'yes', ('61', 50), 'İzleme / kayıt cihazı'))
        else:
            qs += [
                _q('Kullanılan av aracı/yöntem denizlerde amatör avcılık için izin verilen araç ve yöntemlere uygun mu?', 'yes', ('62', 16), 'Amatör av aracı', penalty_query='amatör avcılık kurallarının ihlali'),
                _q('Avcılık yapılan saha; yüzme alanı, yetiştiricilik tesisi ve diğer yer sınırlamalarına uygun mu?', 'yes', ('62', 17), 'Amatör yer yasağı', penalty_query='amatör avcılık kurallarının ihlali'),
            ]

    if subject in {'fishing', 'species'}:
        if activity == 'commercial':
            qs += [
                _q('Avlanan/tespit edilen ürünün asgari boy veya ağırlık şartı uygun mu?', 'yes', ('61', 17), 'Ürün boy / ağırlık', penalty_query='yasak boyda su ürünü'),
                _q('Türün kota, tolerans, izin ve varsa özel avcılık şartları uygun mu?', 'yes', ('61', 18), 'Kota / tolerans / özel izin'),
            ]
        else:
            qs += [
                _q('Avlanan/tespit edilen ürünün asgari boy şartı uygun mu?', 'yes', ('62', 15), 'Amatör asgari boy', penalty_query='amatör avcılık kurallarının ihlali'),
                _q('Alıkonulan ürün miktarı adet/kg sınırları içinde mi?', 'yes', ('62', 15), 'Amatör alıkonulabilir miktar', penalty_query='amatör avcılık kurallarının ihlali'),
            ]

    if subject == 'transport':
        if activity == 'commercial':
            qs += [
                _q('Nakil/Menşe veya somut sevk için gerekli diğer belge mevcut ve uygun mu?', 'yes', ('61', 46), 'Nakil / Menşe belgesi', penalty_query='nakil belgesi'),
                _q('Ürün yasak tür, yasak boy, yasak zaman veya mevzuata aykırı avcılıktan elde edilmiş ürün niteliğinde değil mi?', 'yes', ('law', 25), 'Yasak ürünün nakli / satışı', penalty_query='nakleden satan'),
                _q('Ürün Bakanlıkça belirlenen karaya çıkış noktası zorunluluğuna tabi ise uygun noktadan boşaltıldı mı?', 'yes', ('law', 36), 'Karaya çıkış noktası', penalty_query='karaya çıkış noktası'),
            ]
        else:
            qs.append(_q('Amatör avcılıkla elde edilen ürün satılmıyor, canlı nakledilmiyor ve başka kaynağa bırakılmıyor mu?', 'yes', ('62', 8), 'Amatör ürün satışı / canlı nakli', penalty_query='amatör avcılık kurallarının ihlali'))

    qs.append(_q('Tespit açısından mümkün olan fotoğraf, video, konum/koordinat, ölçüm veya diğer teknik deliller kayda alındı mı?', 'yes', ('reg', 37), 'Delillendirme', procedure=True))
    return qs


async def audit_quick_start(q, context):
    questions = build_quick_questions(context)
    context.user_data['quick_questions'] = questions
    context.user_data['quick_answers'] = []
    context.user_data['context_flags'] = build_context_flags(context)
    return await audit_quick_render(q, context, 0)


async def audit_quick_render(q, context, idx):
    qs = context.user_data.get('quick_questions') or []
    if idx >= len(qs):
        return await audit_quick_finish(q, context)
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
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb([
        [('✅ Evet', f'audit:quick:ans:{idx}:yes'), ('❌ Hayır', f'audit:quick:ans:{idx}:no')],
        [('❔ Bilinmiyor / Kontrol Edilmedi', f'audit:quick:ans:{idx}:unknown')],
        [('📚 İlgili Madde', f'art:{item["ref"][0]}:{item["ref"][1]}'), ('🏠 Ana Menü', 'menu')],
    ]))


async def audit_quick_answer(q, context, idx, ans):
    qs = context.user_data.get('quick_questions') or []
    if idx >= len(qs):
        return await q.answer('Kontrol oturumu bulunamadı.', show_alert=True)
    answers = context.user_data.setdefault('quick_answers', [])
    while len(answers) <= idx:
        answers.append(None)
    answers[idx] = ans
    return await audit_quick_render(q, context, idx + 1)


async def audit_quick_finish(q, context):
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

    activity = context.user_data.get('audit_activity')
    region = REGION_LABEL.get(context.user_data.get('audit_region'), context.user_data.get('audit_region'))
    d = audit_date(context)
    gear = context.user_data.get('audit_gear')
    species = context.user_data.get('audit_species_name')
    subject = context.user_data.get('audit_subject')
    text = (
        '🛡️ <b>DENETİM SONUCU</b>\n\n'
        f'🌊 Bölge: <b>{esc(region)}</b>\n'
        f'⚓ Faaliyet: <b>{"Ticari" if activity == "commercial" else "Amatör"}</b>\n'
        f'🚤 Gemi/Tekne: <b>{esc(audit_length_label(context))}</b>\n'
        f'📅 Tarih: <b>{d.strftime("%d.%m.%Y")}</b>\n'
        f'🎯 Konu: <b>{esc(SUBJECT_LABEL.get(subject, subject or "—"))}</b>\n'
    )
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
    rows.append([('🔄 Yeni Denetim', 'audit:start'), ('🏠 Ana Menü', 'menu')])
    db.log(q.from_user.id, 'guided_audit', ', '.join([x['tag'] for x in flags + possible]))
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows))


CLASSIFICATION_QUESTIONS = [
    'Amatör avcılıkta alıkonulabilir miktara izin verilen ürün miktarının 3 katı veya daha fazlası tespit edildi mi?',
    'Avlanması tamamen yasak türlerden, tür veya sayı bazında birden fazla ürün tespit edildi mi?',
    'Zaman yasağındaki türlerden, amatör avcılıkta izin verilen miktarın 2 katı veya daha fazlası tespit edildi mi?',
    'İzin verilen av aracı sayısının (iğne sayısı hariç) 2 katı veya daha fazla av aracı tespit edildi mi?',
    'Yemlik uzatma ağı hariç germe/uzatma/sürütme/çevirme ağı veya ticari avcılıkta kullanımına izin verilen başka bir av aracı tespit edildi mi?',
    'Amatör avcılıkta kullanımı yasaklanmış birden fazla av aracı tespit edildi mi?',
    'Patlayıcı, öldürücü, bayıltıcı, uyuşturucu/uyutucu/uyarıcı madde, karpit, sönmemiş kireç, balık otu, elektroşok veya benzeri yöntem kullanıldığı tespit edildi mi?',
]


async def amateur_classification_start(q, context):
    if context.user_data.get('audit_activity') != 'amateur':
        return await q.answer('Bu kontrol 6/2 Tebliğ kapsamındaki amatör faaliyet için kullanılır.', show_alert=True)
    context.user_data['classify_answers'] = []
    return await amateur_classification_render(q, context, 0)


async def amateur_classification_render(q, context, idx):
    if idx >= len(CLASSIFICATION_QUESTIONS):
        return await amateur_classification_finish(q, context)
    await q.edit_message_text(
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


async def amateur_classification_answer(q, context, idx, ans):
    answers=context.user_data.setdefault('classify_answers',[])
    while len(answers)<=idx:
        answers.append(None)
    answers[idx]=ans
    return await amateur_classification_render(q, context, idx+1)


async def amateur_classification_finish(q, context):
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
    await q.edit_message_text(text,parse_mode=ParseMode.HTML,reply_markup=kb([
        [('📚 6/2 Md.19','art:62:19'),('⚖️ Yaptırım Ara','mode:penalty')],
        [('🚨 Kontrole Dön','audit:hub'),('🏠 Ana Menü','menu')],
    ]))


async def audit_gear_result(q, context):
    gear = context.user_data['audit_gear']
    region = context.user_data.get('audit_region')
    activity = context.user_data.get('audit_activity')
    length = context.user_data.get('audit_length', 0)
    source = '61' if activity == 'commercial' else '62'
    results = db.search_articles(gear, 6, source=source)
    text = f'🎣 <b>{esc(gear.title())} — KONTROL</b>\n\nBölge: {esc(region)} | Gemi: {length:g} m\n\n'
    if activity == 'commercial' and gear == 'ışık' and region in {'karadeniz', 'marmara', 'istanbul', 'canakkale'}:
        text += '🔴 <b>6/1 Md.13: seçilen bölgede ışıkla avcılık yasaktır.</b>\n\n'
    today = datetime.now(TZ).date()
    if activity == 'commercial' and gear == 'gırgır':
        text += 'Kontrol başlıkları: yer yasağı, kapalı dönem, su derinliği, ağ derinliği ve Ağ Ölçüm Belgesi.\n'
        # 6/1 Md.12: Akdeniz 15 Nisan–15 Eylül; diğer denizler 15 Nisan–31 Ağustos.
        closed = ((today.month, today.day) >= (4,15) and (today.month, today.day) <= ((9,15) if region == 'akdeniz' else (8,31)))
        if closed:
            text += f'🔴 <b>{today.strftime("%d.%m.%Y")}: seçilen deniz bölgesi için gırgır kapalı dönemindesiniz.</b>\n'
        else:
            text += f'🟢 {today.strftime("%d.%m.%Y")}: genel gırgır kapalı dönemine denk gelmiyor; yer/derinlik ve diğer şartlar devam eder.\n'
        text += '\n'
    if activity == 'commercial' and gear == 'dip trolü':
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
    rows.append([('🚨 Kontrole Dön','audit:hub'),('⚖️ Yaptırım Ara', 'mode:penalty')])
    rows.append([('🏠 Ana Menü', 'menu')])
    await q.edit_message_text(text + '📚 İlgili kaynak maddeleri:', parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def calc_menu(q):
    await q.edit_message_text(
        '🧮 <b>HESAPLAYICILAR</b>\n\nExcel satırı zaten tekne boyuna göre ayrı tutar veriyorsa ayrıca tekrar 2x/3x boy katsayısı uygulanmamalıdır.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb([
            [('Hamsi %15', 'calc:tol:hamsi'), ('Sardalya %15', 'calc:tol:sardalya')],
            [('İstavrit %15', 'calc:tol:istavrit'), ('Diğer Tür %5', 'calc:tol:diger')],
            [('Mavi yüzgeçli orkinos %5 (adet)', 'calc:tuna')],
            [('↩️ Ana Menü', 'menu')],
        ]),
    )


async def show_favorites(q, uid):
    rows = db.favs(uid)
    text = '⭐ <b>FAVORİLER</b>\n\n'
    if not rows:
        text += 'Henüz favori yok.'
    else:
        text += ''.join(f'• {esc(r["item_type"])} — {esc(r["item_id"])}\n' for r in rows)
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Ana Menü', 'menu')]]))


async def show_history(q, uid):
    rows = db.history(uid)
    text = '🕘 <b>SON İŞLEMLER</b>\n\n'
    text += ''.join(f'• {esc(r["action"])} — {esc(r["query"] or "")}\n' for r in rows) if rows else 'Henüz işlem yok.'
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Ana Menü', 'menu')]]))


async def show_about(q):
    text = (
        '<b>ℹ️ SU ÜRÜNLERİ KOLLUK ASİSTANI v4.1.0</b>\n\n'
        '📋 19 ayrı tekne/av yöntemi için sahaya özel interaktif kontrol föyleri içerir.\n'
        '🚨 Bölgeden başlayarak faaliyet, gemi/tekne durumu, tarih, denetim konusu, av aracı ve türe doğru ilerleyen yönlendirilmiş denetim akışı kullanır.\n'
        '🌊 Normal görev akışı deniz sahasına odaklanır.\n'
        '⚖️ Föyde uygunsuz işaretlenen maddelerden doğrudan yaptırım aramasına ve ilgili kaynak maddesine geçilebilir.'
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb([[('↩️ Ana Menü', 'menu')]]))


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    uid = update.effective_user.id
    text = update.effective_message.text.strip()
    mode = context.user_data.get('mode')


    if mode == 'guide_measure':
        g = guide_current(context)
        if not g:
            context.user_data.pop('mode', None)
            return await send_or_edit(update, context, 'Aktif kontrol föyü bulunamadı.', reply_markup=kb([[('📋 Tekne Türü Kılavuzları', 'guide:menu')]]))
        idx = int(context.user_data.get('guide_measure_idx', 0))
        fields = g.get('measure_fields') or []
        if idx >= len(fields):
            context.user_data.pop('mode', None)
            return await send_or_edit(update, context, 'Ölçüm alanları tamamlandı.', reply_markup=kb([[('📊 Sonucu Aç', 'guide:result')]]))
        field = fields[idx]
        context.user_data.setdefault('guide_measurements', {})[field] = text
        idx += 1
        context.user_data['guide_measure_idx'] = idx
        if idx >= len(fields):
            context.user_data.pop('mode', None)
            return await send_or_edit(update, context, 
                '📐 <b>Ölçüm/kayıt alanları kaydedildi.</b>',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('📊 Kontrol Sonucunu Aç', 'guide:result'), ('↩️ Föye Dön', f'guide:open:{g["key"]}')]])
            )
        next_field = fields[idx]
        return await send_or_edit(update, context, 
            f'📐 {idx+1}/{len(fields)} — <b>{esc(next_field)}</b>\n\nDeğeri yazın.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('⏭️ Kontrol Edilmedi / Atla', 'guide:measure:skip')], [('📊 Sonuca Dön', 'guide:result')]])
        )

    if mode == 'penalty_length':
        try:
            length=float(text.replace(',','.'))
            if length<0: raise ValueError
        except ValueError:
            return await send_or_edit(update, context, 'Gemi boyunu sayı olarak yazın. Örnek: 17.4')
        pid=context.user_data.get('penalty_pid')
        context.user_data['audit_length']=length
        context.user_data.pop('mode',None)
        return await send_or_edit(update, context, f'🚤 Gemi boyu <b>{length:g} m</b> olarak kaydedildi. Ceza kartında Exceldeki uygun boy satırı öne çıkarılacak.',parse_mode=ParseMode.HTML,reply_markup=kb([[('⚖️ Ceza Kartını Aç',f'pen:{pid}')],[('🏠 Ana Menü','menu')]]))

    if mode == 'audit_length_exact':
        try:
            length = float(text.replace(',', '.'))
            if length < 0:
                raise ValueError
        except ValueError:
            return await send_or_edit(update, context, 'Gemi boyunu metre olarak sayı biçiminde yazın. Örnek: 17.4')
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
        return await send_or_edit(update, context, 
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
            return await send_or_edit(update, context, 'Tarihi GG.AA.YYYY biçiminde yazın. Örnek: 20.05.2026')
        context.user_data['audit_date'] = parsed.isoformat()
        context.user_data.pop('mode', None)
        activity = context.user_data.get('audit_activity')
        rows = [
            [('🎣 Avcılık faaliyeti', 'audit:subject:fishing'), ('🐟 Ürün / Tür', 'audit:subject:species')],
            [('📦 Nakil / Satış', 'audit:subject:transport')],
        ]
        if activity == 'commercial' and audit_rule_length(context) > 0:
            rows[1].append(('🚤 Gemi / Ruhsat / Donanım', 'audit:subject:vessel'))
        elif activity == 'amateur':
            rows[1].append(('🔎 Ticari Nitelik Kontrolü', 'classify:start'))
        rows.append([('🏠 Ana Menü', 'menu')])
        return await send_or_edit(update, context, 
            f'📅 Tarih <b>{parsed.strftime("%d.%m.%Y")}</b> olarak kaydedildi.\n\n5. adım: denetimin ana konusunu seçin.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb(rows)
        )

    if mode in {'species_search', 'audit_species_search'}:
        kind = context.user_data.get('species_kind', 'commercial')
        if kind == 'prohibited':
            results = db.search_prohibited(text, LIMIT)
            rows = [[(r['name'][:45], 'art:61:16')] for r in results]
            msg = '🚫 <b>Tamamen yasak tür araması</b>\n\n' + ('Eşleşme bulundu.' if results else 'Eşleşme bulunamadı. Türkçe tür adını değiştirerek deneyin.')
        else:
            results = db.search_species(text, kind, LIMIT)
            rows = [[(r['name'][:45], f'sp:{kind}:{r["id"]}')] for r in results]
            msg = f'🐟 <b>{esc(text)}</b> — {len(results)} sonuç'
        if mode == 'audit_species_search' and context.user_data.get('guided_active'):
            rows.append([('➡️ Tür belirtmeden devam', 'audit:guided:check'), ('🏠 Ana Menü', 'menu')])
        else:
            rows.append([('↩️ Ana Menü', 'menu')])
        db.log(uid, 'species_search', text)
        return await send_or_edit(update, context, msg, parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if mode == 'source_search':
        source = context.user_data.get('source')
        if text.isdigit() and db.get_article(source, int(text)):
            return await send_or_edit(update, context, 
                f'📚 {SRC_LABEL.get(source, source)} Madde {text}',
                reply_markup=kb([[('Maddeyi Aç', f'art:{source}:{text}')], [('↩️ Ana Menü', 'menu')]]),
            )
        results = db.search_articles(text, LIMIT, source=source)
        rows = [[(f'Md.{r["article"]} {r["title"][:35]}', f'art:{source}:{r["article"]}')] for r in results]
        rows.append([('↩️ Ana Menü', 'menu')])
        db.log(uid, 'source_search', text)
        return await send_or_edit(update, context, f'📚 <b>{esc(text)}</b> — {len(results)} madde', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

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
        return await send_or_edit(update, context, 
            f'⚖️ <b>{esc(text)}</b> — {len(results)} yapılandırılmış yaptırım sonucu\n\n<i>İçsuya özgü ceza kayıtları filtrelenmiştir. Sonuç bulunmazsa Excel ham satır araması gösterilir.</i>',
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
        return await send_or_edit(update, context, f'🔎 <b>{esc(text)}</b> — deniz/genel kaynak eşleşmeleri', parse_mode=ParseMode.HTML, reply_markup=kb(rows))

    if mode == 'tuna_total':
        try:
            total=int(text)
            if total <= 0:
                raise ValueError
        except ValueError:
            return await send_or_edit(update, context, 'Toplam adedi pozitif tam sayı olarak yazın.')
        context.user_data.update(mode='tuna_band', tuna_total=total)
        return await send_or_edit(update, context, '8–30 kg veya 75–115 cm aralığında tespit edilen birey sayısını yazın.')

    if mode == 'tuna_band':
        try:
            band=int(text)
            total=context.user_data['tuna_total']
            if band < 0 or band > total:
                raise ValueError
        except ValueError:
            return await send_or_edit(update, context, 'Adedi 0 ile toplam birey sayısı arasında tam sayı olarak yazın.')
        ratio=band/total*100
        context.user_data.clear()
        result='🔴 %5 adet toleransı aşılmış görünüyor.' if ratio>5 else '🟢 %5 adet toleransı içinde görünüyor.'
        return await send_or_edit(update, context, 
            f'🧮 İstisna bandındaki birey oranı: <b>%{ratio:.2f}</b> ({band}/{total})\nKaynak sınır: <b>%5 (adet)</b>\n{result}\n\n<i>Kaynak: 6/1 Tebliğ Madde 18. Mavi yüzgeçli orkinosun kota/izin, alan ve diğer özel hükümleri ayrıca kontrol edilmelidir.</i>',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📚 6/1 Md.18','art:61:18'),('📚 6/1 Md.22','art:61:22')],[('🏠 Ana Menü','menu')]])
        )

    if mode == 'tol_total':
        try:
            total = float(text.replace(',', '.'))
            if total <= 0:
                raise ValueError
        except ValueError:
            return await send_or_edit(update, context, 'Toplam kg değerini sayı olarak yazın.')
        context.user_data.update(mode='tol_small', tol_total=total)
        return await send_or_edit(update, context, 'Asgari boyun altındaki ürünün toplam ağırlığını kg olarak yazın.')

    if mode == 'tol_small':
        try:
            small = float(text.replace(',', '.'))
            if small < 0:
                raise ValueError
        except ValueError:
            return await send_or_edit(update, context, 'Küçük boy kg değerini sayı olarak yazın.')
        total = context.user_data['tol_total']
        species = context.user_data['tol_species']
        limit = 15 if species in {'hamsi', 'sardalya', 'istavrit'} else 5
        ratio = small / total * 100
        context.user_data.clear()
        result = '🔴 Tolerans aşılmış görünüyor.' if ratio > limit else '🟢 Tolerans içinde görünüyor.'
        return await send_or_edit(update, context, 
            f'🧮 Küçük boy oranı: <b>%{ratio:.2f}</b>\nKaynak tolerans: <b>%{limit}</b>\n{result}\n\nKaynak: 6/1 Tebliğ Madde 18. Tür özel hükümlerini ayrıca kontrol edin.',
            parse_mode=ParseMode.HTML,
            reply_markup=kb([[('📚 6/1 Md.18', 'art:61:18'), ('🏠 Ana Menü', 'menu')]]),
        )

    if mode is None:
        # Doğal Dil / Genel Arama
        results_species_com = db.search_species(text, 'commercial', 2)
        results_species_ama = db.search_species(text, 'amateur', 2)
        results_penalties = db.search_penalties(text, 3)
        results_articles = db.search_articles(text, 3)
        
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
            return await send_or_edit(update, context, 
                f'🔍 <b>"{esc(text)}"</b> için karma arama sonuçları:',
                parse_mode=ParseMode.HTML,
                reply_markup=kb(rows)
            )
        else:
            return await send_or_edit(update, context, 
                f'🔍 <b>"{esc(text)}"</b> ile eşleşen tür, ceza veya mevzuat bulunamadı.\n\nFarklı bir kelime deneyin veya alt kısımdaki sabit butonları kullanın.',
                parse_mode=ParseMode.HTML,
                reply_markup=kb([[('🏠 Ana Menü', 'menu')]])
            )

    await send_or_edit(update, context, 'Bir işlem seçin:', reply_markup=kb(MAIN))


async def show_admin_panel(q, section='main'):
    if q.from_user.id not in ADMIN_IDS:
        return await q.answer('Yönetici yetkisi gerekli.', show_alert=True)
    
    if section == 'main':
        users, count, rows = db.admin_stats()
        text = (
            f'🔐 <b>YÖNETİCİ VE DENETİM PANELİ</b>\n\n'
            f'👥 <b>Kayıtlı Kullanıcı Sayısı:</b> {users}\n'
            f'⚡ <b>Toplam İşlem & Sorgu:</b> {count}\n\n'
            f'<b>Son Yapılan İşlemler:</b>\n'
        )
        for r in rows[:8]:
            dname = USER_NAMES.get(r['user_id'], r['first_name'] or r['username'] or str(r['user_id']))
            time_str = r['created_at'].split('T')[-1] if 'T' in str(r['created_at']) else str(r['created_at'])
            text += f'• <code>{time_str[:8]}</code> <b>{esc(dname)}</b>: {esc(r["action"])} {esc(r["query"] or "")[:25]}\n'
        
        rows_kb = [
            [('📊 Denetim & Arama Dağılımı', 'admin:stats:vessels')],
            [('👥 Personel Faaliyetleri', 'admin:stats:users'), ('📋 Son 30 Log', 'admin:stats:logs')],
            [('🏠 Ana Menü', 'menu')]
        ]
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))

    elif section == 'vessels':
        guides, searches = db.admin_audit_activity()
        text = '📊 <b>DENETİM VE SORGULAMA DAĞILIMI</b>\n\n'
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
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))

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
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))

    elif section == 'logs':
        _, _, rows = db.admin_stats()
        text = '📋 <b>SON 30 İŞLEM KAYDI (LOGLAR)</b>\n\n'
        for r in rows:
            dname = USER_NAMES.get(r['user_id'], r['first_name'] or r['username'] or str(r['user_id']))
            time_str = r['created_at'].replace('T', ' ')[5:19] if r['created_at'] else ''
            q_info = f' — <i>{esc(r["query"][:30])}</i>' if r['query'] else ''
            text += f'• <code>{time_str}</code> <b>{esc(dname)}</b> → {esc(r["action"])}{q_info}\n'
            
        rows_kb = [[('↩️ Yönetici Paneli', 'admin:panel'), ('🏠 Ana Menü', 'menu')]]
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb(rows_kb))


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    if update.effective_user.id not in ADMIN_IDS:
        return await send_or_edit(update, context, 'Yönetici yetkisi gerekli.')
    users, count, rows = db.admin_stats()
    text = (
        f'🔐 <b>YÖNETİCİ VE DENETİM PANELİ</b>\n\n'
        f'👥 <b>Kayıtlı Kullanıcı Sayısı:</b> {users}\n'
        f'⚡ <b>Toplam İşlem & Sorgu:</b> {count}\n\n'
        f'Detaylı istatistikleri ve logları görüntülemek için aşağıdaki menüyü kullanabilirsiniz:'
    )
    rows_kb = [
        [InlineKeyboardButton('📊 Denetim & Arama Dağılımı', callback_data='admin:stats:vessels')],
        [InlineKeyboardButton('👥 Personel Faaliyetleri', callback_data='admin:stats:users'), InlineKeyboardButton('📋 Son Loglar', callback_data='admin:stats:logs')],
        [InlineKeyboardButton('🏠 Ana Menü', callback_data='menu')]
    ]
    await send_or_edit(update, context, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows_kb))


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Deliberately available even before whitelisting so an operator can send their own Telegram ID to the administrator.
    await send_or_edit(update, context, f'🆔 Telegram kullanıcı ID’niz: <code>{update.effective_user.id}</code>', parse_mode=ParseMode.HTML)


HELP_TEXT = (
    '<b>❓ YARDIM</b>\n\n'
    '<b>💬 Doğrudan yazarak arama</b>\n'
    'Menüde gezmeden, aklınıza gelen kelimeyi yazmanız yeterli. Tür adı, ceza '
    'konusu veya mevzuat kelimesi yazdığınızda tür, ceza ve madde sonuçları '
    'birlikte listelenir.\n'
    '<i>Örnek:</i> <code>hamsi</code> · <code>ruhsatsız</code> · <code>BAGİS</code>\n\n'
    '<b>📋 Tekne Türü Kılavuzları</b>\n'
    'Çıkacağınız tekneye özel kontrol föyünü açar. Her maddeyi Uygun / Uygunsuz / '
    'Kontrol Edilmedi olarak işaretleyip sonunda özet alırsınız.\n\n'
    '<b>🚨 Denetime Başla</b>\n'
    'Bölge, faaliyet, gemi boyu, tarih, av aracı ve tür sırasıyla ilerleyen '
    'yönlendirilmiş denetim akışıdır.\n\n'
    '<b>⌨️ Komutlar</b>\n'
    '/start · /menu — Ana menüyü açar\n'
    '/help — Bu yardım ekranı\n'
    '/id — Telegram kullanıcı ID’nizi gösterir\n\n'
    '<b>⭐ Favoriler ve 🕘 Son Sorgular</b>\n'
    'Sık kullandığınız tür, ceza ve maddeleri favorilere ekleyip ana menüden '
    'hızlıca açabilirsiniz.'
)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    db.log(update.effective_user.id, 'help')
    await send_or_edit(
        update, context, HELP_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=kb([[('🏠 Ana Menü', 'menu')]]),
    )


async def post_init(application):
    """Populate Telegram's "/" command menu so the commands are discoverable."""
    await application.bot.set_my_commands([
        BotCommand('start', 'Ana menüyü aç'),
        BotCommand('menu', 'Ana menüyü aç'),
        BotCommand('help', 'Yardım ve kullanım'),
        BotCommand('id', 'Telegram ID’mi göster'),
    ])



async def error_handler(update, context):
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Hata yakalandı: %s", context.error)
    logger.error(traceback.format_exc())
    try:
        if update and update.effective_message:
            await send_or_edit(update, context, 
                '⚠️ Bir hata oluştu. Lütfen tekrar deneyin veya /menu ile ana menüye dönün.',
            )
    except Exception:
        pass

def main():
    db.init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('menu', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(CommandHandler('istatistik', admin_cmd))
    app.add_handler(CommandHandler('id', id_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
