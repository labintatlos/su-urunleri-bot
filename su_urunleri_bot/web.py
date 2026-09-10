"""Su Ürünleri Kolluk Asistanı — web sunucusu.

İki dinleyici açılır:

- 8099 (Ingress): Home Assistant yan menüsündeki panel. `X-Remote-User-Name`
  başlığına yalnızca Supervisor'ın adresinden gelen istekte güvenilir. Bu
  panelden bir kez site şifresiyle giren kişi orada bir daha şifre görmez.
- 8101 (web sitesi): ev ağı ve KeenDNS. Kimlik yalnızca kullanıcı adı ve
  şifreyle verilen oturum çerezinden gelir; başlıklara hiç bakılmaz.

Ekranların kendisi screens.py'dedir. Bir düğmeye basılması `callback`, arama
kutusuna yazılan metin `text_handler` olarak çalıştırılır; kişinin akış durumu
(eski Telegram `user_data`) ve son ekranı veritabanında durur, böylece sayfa
yenilense veya eklenti yeniden başlasa da kalınan yerden devam edilir.

Yalnızca standart kütüphane kullanılır.
"""

import json
import logging
import os
import re
import threading
from collections import defaultdict
from datetime import datetime
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import accounts
import db
import screens

logger = logging.getLogger('web')

STATIC_DIR = Path(__file__).parent / 'static'
STATIC_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
}
SUPERVISOR_IP = os.environ.get('INGRESS_TRUSTED_IP', '172.30.32.2')
MAX_BODY_BYTES = 64 * 1024
MAX_TEXT_LENGTH = 4000
ERROR_TEXT = '⚠️ Bir hata oluştu. Lütfen tekrar deneyin veya Ana Menü ile başa dönün.'

throttle = accounts.LoginThrottle()
_user_locks = defaultdict(threading.Lock)
_user_locks_guard = threading.Lock()


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ── Kişi başı akış durumu ────────────────────────────────────────────────

def _user_lock(uid):
    with _user_locks_guard:
        return _user_locks[uid]


def load_state(uid):
    c = db.con()
    row = c.execute('SELECT data, screen FROM web_state WHERE user_id=?', (uid,)).fetchone()
    c.close()
    data, view = {}, None
    if row:
        try:
            data = json.loads(row['data'] or '{}')
        except ValueError:
            data = {}
        try:
            view = json.loads(row['screen']) if row['screen'] else None
        except ValueError:
            view = None
    return (data if isinstance(data, dict) else {}), view


def save_state(uid, data, view):
    c = db.con()
    c.execute('''INSERT INTO web_state(user_id,data,screen,updated_at) VALUES(?,?,?,?)
                 ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, screen=excluded.screen, updated_at=excluded.updated_at''',
              (uid, json.dumps(data, ensure_ascii=False, default=str), json.dumps(view, ensure_ascii=False),
               datetime.now().isoformat(timespec='seconds')))
    c.commit()
    c.close()


def run_screen(account, handler, reuse_last=False):
    """Kişinin durumunu yükler, ekran fonksiyonunu çalıştırır, sonucu kaydeder."""
    uid = accounts.uid_of(account)
    screens.USER_NAMES[uid] = account['display_name']
    with _user_lock(uid):
        data, last = load_state(uid)
        if reuse_last and last:
            return dict(last, mode=data.get('mode'), alert=None)
        screen = screens.Screen()
        context = screens.WebContext(data, screen)
        try:
            db.touch_user(SimpleNamespace(id=uid, username=account['username'], first_name=account['display_name']),
                          custom_name=account['display_name'])
            handler(screen, context, uid)
        except Exception:
            logger.exception('Ekran oluşturulurken hata')
            screen.replace(ERROR_TEXT, screens.kb([[('🏠 Ana Menü', 'menu')]]))
        if screen.touched:
            view = {'blocks': screen.blocks, 'buttons': screen.buttons}
        else:
            view = last or {'blocks': [], 'buttons': []}
        save_state(uid, context.user_data, view)
        return dict(view, mode=context.user_data.get('mode'), alert=screen.alert)


def press(data):
    return lambda screen, context, uid: screens.callback(screens.WebQuery(screen, uid, data), context)


def type_text(text):
    return lambda screen, context, uid: screens.text_handler(screens.WebUpdate(uid, text), context)


def _button_label(uid, data):
    """Kayıtta iç callback kodu yerine kullanıcının gördüğü düğme metnini kullanır."""
    _, view = load_state(uid)
    for row in (view or {}).get('buttons', []):
        for button in row:
            if button.get('data') == data:
                return button.get('text') or data
    return 'Ana Menü' if data == 'menu' else data


TEXT_ACTIONS = {
    'ai_analysis': 'Hukuki değerlendirme',
    'penalty': 'Ceza araması',
    'species_search': 'Tür araması',
    'audit_species_search': 'Denetimde tür araması',
    'source_search': 'Mevzuat araması',
    'gear': 'Av aracı araması',
    'place': 'Yer bilgisi',
    'lawsearch': 'Kanun araması',
    'audit_length_exact': 'Gemi boyu',
    'penalty_length': 'Gemi boyu',
    'audit_date': 'Denetim tarihi',
    'guide_measure': 'Ölçüm değeri',
}


def _text_detail(uid, text):
    data, _ = load_state(uid)
    label = TEXT_ACTIONS.get(data.get('mode'), 'Genel arama')
    return f'{label}: {text}'


# ── HTTP ─────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = 'SuUrunleri'
    sys_version = ''
    protocol_version = 'HTTP/1.1'
    ingress = False

    def log_message(self, fmt, *args):
        pass

    # Kimlik
    def client_ip(self):
        return self.client_address[0]

    def ha_user(self):
        if not self.ingress or self.client_ip() != SUPERVISOR_IP:
            return None
        return (self.headers.get('X-Remote-User-Name') or '').strip() or None

    def cookie(self, name):
        try:
            jar = SimpleCookie(self.headers.get('Cookie') or '')
        except CookieError:
            return None
        return jar[name].value if name in jar else None

    def identity(self):
        linked = accounts.find_by_ha_user(self.ha_user())
        if linked:
            return linked, 'ingress'
        token = self.cookie(accounts.COOKIE_NAME)
        account = accounts.account_from_token(token) if token else None
        return (account, 'cookie') if account else (None, None)

    def require_account(self, admin=False):
        account, _ = self.identity()
        if not account:
            raise ApiError(401, 'Oturum açmanız gerekiyor.')
        if admin and not account['is_admin']:
            raise ApiError(403, 'Bu işlem için yönetici yetkisi gerekiyor.')
        return account

    # Yanıtlar
    def security_headers(self):
        csp = ("default-src 'self'; img-src 'self' data: https://upload.wikimedia.org; "
               "base-uri 'none'; form-action 'self'; object-src 'none'")
        if not self.ingress:
            csp += "; frame-ancestors 'none'"
            # Tarayıcı bunu yalnızca HTTPS'te dikkate alır (IP adreslerinde hiç
            # uygulamaz): KeenDNS adresi bir kez https ile açılınca bir daha
            # düz http ile açılmaz.
            self.send_header('Strict-Transport-Security', 'max-age=31536000')
        self.send_header('Content-Security-Policy', csp)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')

    def send_body(self, status, body, content_type, cookies=(), cache='no-store'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        for cookie in cookies:
            self.send_header('Set-Cookie', cookie)
        self.security_headers()
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def send_json(self, status, payload, cookies=()):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_body(status, body, 'application/json; charset=utf-8', cookies)

    def session_cookie(self, account, remember):
        token, max_age = accounts.issue_token(account, remember)
        parts = [f'{accounts.COOKIE_NAME}={token}', 'Path=/', 'HttpOnly', 'SameSite=Lax']
        if max_age:
            parts.append(f'Max-Age={max_age}')
        if (self.headers.get('X-Forwarded-Proto') or '').lower() == 'https':
            parts.append('Secure')
        return '; '.join(parts)

    def read_json(self):
        # Başka bir sitenin tarayıcı üzerinden istek atmasını (CSRF) engeller:
        # bu başlık ancak aynı kökenden çalışan betik tarafından eklenebilir.
        if self.headers.get('X-Requested-With') != 'SuUrunleri':
            raise ApiError(403, 'Geçersiz istek.')
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_BODY_BYTES:
            raise ApiError(413, 'İstek çok büyük.')
        try:
            data = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            raise ApiError(400, 'Geçersiz istek.')
        if not isinstance(data, dict):
            raise ApiError(400, 'Geçersiz istek.')
        return data

    # Yönlendirme
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self.dispatch(self.route_get)

    def do_POST(self):
        self.dispatch(self.route_post)

    def dispatch(self, route):
        path = urlsplit(self.path).path
        try:
            route(path)
        except ApiError as e:
            self.send_json(e.status, {'error': e.message})
        except accounts.AccountError as e:
            self.send_json(400, {'error': str(e)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            logger.exception('İstek işlenemedi: %s %s', self.command, path)
            try:
                self.send_json(500, {'error': 'Sunucuda beklenmeyen bir hata oluştu.'})
            except Exception:
                pass

    def route_get(self, path):
        if path in ('/', '/index.html'):
            return self.send_static('index.html')
        if path.startswith('/static/'):
            return self.send_static(path[len('/static/'):])
        if path == '/health':
            return self.send_json(200, {'status': 'ok'})
        if path == '/api/session':
            account, via = self.identity()
            return self.send_json(200, {
                'setup_required': accounts.setup_required(),
                'ingress': bool(self.ha_user()),
                'user': dict(accounts.public(account), via=via) if account else None,
            })
        if path == '/api/screen':
            account = self.require_account()
            return self.send_json(200, run_screen(account, press('menu'), reuse_last=True))
        if path == '/api/people':
            self.require_account(admin=True)
            return self.send_json(200, {'people': [accounts.public(r) for r in accounts.list_accounts()]})
        raise ApiError(404, 'Sayfa bulunamadı.')

    def route_post(self, path):
        data = self.read_json()
        if path == '/api/login':
            return self.login(data)
        if path == '/api/setup':
            return self.setup_admin(data)
        if path == '/api/logout':
            account = self.require_account()
            db.log_activity(accounts.uid_of(account), 'logout')
            return self.send_json(200, {'ok': True}, cookies=[
                f'{accounts.COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'])
        account = self.require_account()
        uid = accounts.uid_of(account)
        if path == '/api/action':
            value = data.get('data')
            if not isinstance(value, str) or not value or len(value) > 256:
                raise ApiError(400, 'Geçersiz düğme.')
            db.log_activity(uid, 'button', _button_label(uid, value))
            return self.send_json(200, run_screen(account, press(value)))
        if path == '/api/text':
            text = str(data.get('text') or '').strip()
            if not text:
                raise ApiError(400, 'Bir şey yazın.')
            db.log_activity(uid, 'text', _text_detail(uid, text[:MAX_TEXT_LENGTH]))
            return self.send_json(200, run_screen(account, type_text(text[:MAX_TEXT_LENGTH])))
        if path == '/api/password':
            updated = accounts.change_own_password(account, data.get('current'), data.get('new'))
            db.log_activity(uid, 'password_change')
            return self.send_json(200, {'ok': True}, cookies=[self.session_cookie(updated, True)])
        if path == '/api/people':
            self.require_account(admin=True)
            created = accounts.create_account(data.get('username'), data.get('display_name'),
                                              data.get('password'), bool(data.get('is_admin')))
            role = 'yönetici' if created['is_admin'] else 'kullanıcı'
            db.log_activity(uid, 'person_create', f'{created["display_name"]} (@{created["username"]}) · {role}')
            return self.send_json(200, {'person': accounts.public(created)})
        match = re.fullmatch(r'/api/people/(\d+)', path)
        if match:
            acting = self.require_account(admin=True)
            flag = lambda key: bool(data[key]) if key in data else None
            updated = accounts.update_account(int(match.group(1)), acting,
                                              display_name=data.get('display_name'),
                                              is_admin=flag('is_admin'), is_active=flag('is_active'),
                                              password=data.get('password') or None)
            changes = []
            if 'display_name' in data: changes.append('adını değiştirdi')
            if 'is_admin' in data:
                changes.append('yönetici yaptı' if data['is_admin'] else 'yöneticiliğini kaldırdı')
            if 'is_active' in data:
                changes.append('etkinleştirdi' if data['is_active'] else 'pasif yaptı')
            if data.get('password'): changes.append('şifresini yeniledi')
            detail = f'{updated["display_name"]} (@{updated["username"]}): ' + ', '.join(changes)
            db.log_activity(uid, 'person_update', detail)
            return self.send_json(200, {'person': accounts.public(updated)})
        raise ApiError(404, 'Sayfa bulunamadı.')

    def login(self, data):
        username = str(data.get('username') or '').strip().lower()
        key = f'{self.client_ip()}|{username}'
        if throttle.is_blocked(key):
            raise ApiError(429, 'Çok fazla hatalı deneme yapıldı. Lütfen 15 dakika sonra tekrar deneyin.')
        account = accounts.authenticate(username, data.get('password'))
        if not account:
            throttle.record_failure(key)
            logger.warning('Başarısız giriş denemesi: kullanıcı=%s adres=%s', username[:40], self.client_ip())
            raise ApiError(401, 'Kullanıcı adı veya şifre hatalı.')
        throttle.clear(key)
        accounts.mark_login(account, ha_user=self.ha_user())
        db.log(accounts.uid_of(account), 'login')
        db.log_activity(accounts.uid_of(account), 'login')
        self.send_json(200, {'ok': True}, cookies=[self.session_cookie(account, bool(data.get('remember')))])

    def setup_admin(self, data):
        key = f'{self.client_ip()}|kurulum'
        if not accounts.setup_required():
            raise ApiError(409, 'Kurulum zaten tamamlandı. Giriş yapın.')
        if throttle.is_blocked(key):
            raise ApiError(429, 'Çok fazla hatalı deneme yapıldı. Lütfen 15 dakika sonra tekrar deneyin.')
        if not accounts.check_setup_code(data.get('code')):
            throttle.record_failure(key)
            raise ApiError(400, 'Kurulum kodu hatalı. Kodu eklentinin Günlük sekmesinden kontrol edin.')
        account = accounts.create_account(data.get('username'), data.get('display_name'),
                                          data.get('password'), is_admin=True)
        accounts.clear_setup_code()
        throttle.clear(key)
        accounts.mark_login(account, ha_user=self.ha_user())
        db.log_activity(accounts.uid_of(account), 'setup')
        logger.info('İlk yönetici oluşturuldu: %s', account['username'])
        self.send_json(200, {'ok': True}, cookies=[self.session_cookie(account, True)])

    def send_static(self, name):
        path = (STATIC_DIR / name).resolve()
        if path.parent != STATIC_DIR.resolve() or path.suffix not in STATIC_TYPES or not path.is_file():
            raise ApiError(404, 'Sayfa bulunamadı.')
        cache = 'no-cache' if path.suffix == '.html' else 'public, max-age=300'
        self.send_body(200, path.read_bytes(), STATIC_TYPES[path.suffix], cache=cache)


class IngressHandler(Handler):
    ingress = True


class PublicHandler(Handler):
    ingress = False


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    db.init_db()
    accounts.init()
    accounts.announce_setup_code()
    ingress_port = int(os.environ.get('INGRESS_PORT', '8099'))
    web_port = int(os.environ.get('WEB_PORT', '8101'))
    ingress = ThreadingHTTPServer(('0.0.0.0', ingress_port), IngressHandler)
    public = ThreadingHTTPServer(('0.0.0.0', web_port), PublicHandler)
    threading.Thread(target=ingress.serve_forever, name='ingress', daemon=True).start()
    logger.info('Web sitesi hazır: port %s (site), %s (Home Assistant paneli)', web_port, ingress_port)
    public.serve_forever()


if __name__ == '__main__':
    main()
