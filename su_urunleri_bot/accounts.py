"""Web sitesi hesapları.

Giriş, Aile Bütçe sitesindekiyle aynı sistemdir: kullanıcı adı ve şifre, eklenti
günlüğüne yazılan tek kullanımlık kurulum koduyla oluşturulan ilk yönetici ve
kişileri siteden ekleyip şifre veren yöneticiler.

Şifre standart kütüphanedeki scrypt ile tuzlu özet olarak saklanır; Alpine
imajında derlenecek bir bağımlılık yoktur. Oturum çerezi imzalı ve süreli bir
belirteçtir; içindeki parmak izi şifre özetinden türetildiği için şifre
değişince o kişinin açık oturumları kendiliğinden kapanır.

Kayıtlarda (users, query_log, inspections) web kişileri eski Telegram
kimlikleriyle çakışmasın diye negatif numara taşır: hesap 3 → kullanıcı -3.
Eski Telegram geçmişi yönetici panelinde görünmeye devam eder.
"""

import base64
import hashlib
import hmac
import logging
import re
import secrets
import threading
import time
from collections import deque
from datetime import datetime
from functools import lru_cache

import db

logger = logging.getLogger(__name__)

COOKIE_NAME = 'suurunleri_oturum'
REMEMBER_SECONDS = 30 * 24 * 3600
SHORT_SECONDS = 12 * 3600
USERNAME_RE = re.compile(r'^[a-z0-9._]{3,32}$')
MIN_PASSWORD_LENGTH = 8

# Yalnız hatalı denemeler sayılır; doğru şifreyle giren kişi hiç yavaşlatılmaz.
FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1


class AccountError(ValueError):
    """Kullanıcıya olduğu gibi gösterilebilecek hesap hatası."""


def _now():
    return datetime.now().isoformat(timespec='seconds')


def init():
    c = db.con()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS web_accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        ha_user TEXT,
        created_at TEXT,
        last_login TEXT
    );
    CREATE TABLE IF NOT EXISTS web_state(user_id INTEGER PRIMARY KEY, data TEXT, screen TEXT, updated_at TEXT);
    ''')
    c.commit()
    c.close()


# ── Şifre ────────────────────────────────────────────────────────────────

def _b64(raw):
    return base64.b64encode(raw).decode('ascii')


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=_SCRYPT_N,
                            r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return f'scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}'


def verify_password(password, stored):
    if not stored:
        return False
    try:
        scheme, n, r, p, salt, digest = stored.split('$')
        if scheme != 'scrypt':
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode('utf-8'), salt=base64.b64decode(salt),
                                n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


@lru_cache(maxsize=1)
def _dummy_hash():
    return hash_password(secrets.token_hex(16))


# ── Hesaplar ─────────────────────────────────────────────────────────────

def uid_of(account):
    return -int(account['id'])


def public(account):
    return {
        'id': account['id'],
        'username': account['username'],
        'display_name': account['display_name'],
        'is_admin': bool(account['is_admin']),
        'is_active': bool(account['is_active']),
        'ha_linked': bool(account['ha_user']),
        'last_login': account['last_login'],
    }


def get(account_id):
    c = db.con()
    row = c.execute('SELECT * FROM web_accounts WHERE id=?', (int(account_id),)).fetchone()
    c.close()
    return row


def list_accounts():
    c = db.con()
    rows = c.execute('SELECT * FROM web_accounts ORDER BY is_active DESC, display_name COLLATE NOCASE').fetchall()
    c.close()
    return rows


def is_admin_uid(uid):
    if not isinstance(uid, int) or uid >= 0:
        return False
    row = get(-uid)
    return bool(row and row['is_admin'] and row['is_active'])


def setup_required():
    c = db.con()
    row = c.execute('SELECT 1 FROM web_accounts WHERE is_admin=1 AND is_active=1 LIMIT 1').fetchone()
    c.close()
    return row is None


def _clean_username(username):
    username = str(username or '').strip().lower()
    if not USERNAME_RE.match(username):
        raise AccountError('Kullanıcı adı 3-32 karakter olmalı; yalnız küçük harf, rakam, nokta ve alt çizgi kullanılabilir.')
    return username


def _clean_display_name(name):
    name = ' '.join(str(name or '').split())
    if not 1 <= len(name) <= 60:
        raise AccountError('Ad soyad 1-60 karakter olmalı.')
    return name


def _check_password(password):
    if len(password or '') < MIN_PASSWORD_LENGTH:
        raise AccountError(f'Şifre en az {MIN_PASSWORD_LENGTH} karakter olmalı.')
    return password


def create_account(username, display_name, password, is_admin=False):
    username = _clean_username(username)
    display_name = _clean_display_name(display_name)
    password_hash = hash_password(_check_password(password))
    c = db.con()
    try:
        if c.execute('SELECT 1 FROM web_accounts WHERE username=?', (username,)).fetchone():
            raise AccountError('Bu kullanıcı adı zaten kullanılıyor.')
        cur = c.execute(
            'INSERT INTO web_accounts(username,display_name,password_hash,is_admin,is_active,created_at) VALUES(?,?,?,?,1,?)',
            (username, display_name, password_hash, 1 if is_admin else 0, _now()))
        c.commit()
        account_id = cur.lastrowid
    finally:
        c.close()
    return get(account_id)


def update_account(account_id, acting, *, display_name=None, is_admin=None, is_active=None, password=None):
    """Yöneticinin bir kişide yaptığı değişiklik. Son yöneticinin yetkisi alınamaz."""
    row = get(account_id)
    if not row:
        raise AccountError('Kişi bulunamadı.')
    fields = {}
    if display_name is not None:
        fields['display_name'] = _clean_display_name(display_name)
    if password:
        fields['password_hash'] = hash_password(_check_password(password))
    if is_admin is not None:
        fields['is_admin'] = 1 if is_admin else 0
    if is_active is not None:
        fields['is_active'] = 1 if is_active else 0
    loses_admin = row['is_admin'] and row['is_active'] and (
        fields.get('is_admin', 1) == 0 or fields.get('is_active', 1) == 0)
    if loses_admin:
        if row['id'] == acting['id']:
            raise AccountError('Kendi yöneticiliğinizi kaldıramaz veya kendinizi pasif yapamazsınız.')
        c = db.con()
        admins = c.execute('SELECT COUNT(*) FROM web_accounts WHERE is_admin=1 AND is_active=1').fetchone()[0]
        c.close()
        if admins <= 1:
            raise AccountError('En az bir etkin yönetici kalmalı.')
    if fields:
        c = db.con()
        c.execute('UPDATE web_accounts SET ' + ','.join(f'{k}=?' for k in fields) + ' WHERE id=?',
                  (*fields.values(), row['id']))
        c.commit()
        c.close()
    return get(row['id'])


def change_own_password(account, current, new):
    if not verify_password(current or '', account['password_hash']):
        raise AccountError('Mevcut şifre yanlış.')
    return update_account(account['id'], account, password=_check_password(new))


def authenticate(username, password):
    """Doğru bilgilerle etkin hesabı, aksi halde None döndürür."""
    username = str(username or '').strip().lower()
    c = db.con()
    row = c.execute('SELECT * FROM web_accounts WHERE username=?', (username,)).fetchone()
    c.close()
    if not row:
        # Yanıt süresinden hangi kullanıcı adlarının kayıtlı olduğu anlaşılmasın.
        verify_password(password or '', _dummy_hash())
        return None
    if not verify_password(password or '', row['password_hash']) or not row['is_active']:
        return None
    return row


def mark_login(account, ha_user=None):
    c = db.con()
    c.execute('UPDATE web_accounts SET last_login=? WHERE id=?', (_now(), account['id']))
    if ha_user:
        # Home Assistant panelinden bir kez şifreyle giren kişi, orada bir daha şifre görmez.
        c.execute('UPDATE web_accounts SET ha_user=NULL WHERE ha_user=?', (ha_user,))
        c.execute('UPDATE web_accounts SET ha_user=? WHERE id=?', (ha_user, account['id']))
    c.commit()
    c.close()


def find_by_ha_user(ha_user):
    if not ha_user:
        return None
    c = db.con()
    row = c.execute('SELECT * FROM web_accounts WHERE ha_user=? AND is_active=1', (ha_user,)).fetchone()
    c.close()
    return row


# ── Oturum çerezi ────────────────────────────────────────────────────────

_secret_lock = threading.Lock()
_secret_value = None


def _secret():
    global _secret_value
    with _secret_lock:
        if _secret_value is None:
            path = db.DB_PATH.parent / 'session_secret'
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(secrets.token_hex(32), encoding='ascii')
                try:
                    path.chmod(0o600)
                except OSError:
                    pass
            _secret_value = path.read_text(encoding='ascii').strip()
        return _secret_value


def _fingerprint(password_hash):
    return hashlib.sha256(password_hash.encode('utf-8')).hexdigest()[:16]


def _sign(payload):
    digest = hmac.new(_secret().encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')


def issue_token(account, remember):
    lifetime = REMEMBER_SECONDS if remember else SHORT_SECONDS
    payload = f'{account["id"]}.{int(time.time() + lifetime)}.{_fingerprint(account["password_hash"])}'
    return f'{payload}.{_sign(payload)}', (lifetime if remember else None)


def account_from_token(token):
    try:
        payload, signature = str(token).rsplit('.', 1)
        account_id, expires, fingerprint = payload.split('.')
        account_id, expires = int(account_id), int(expires)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(payload)) or expires < time.time():
        return None
    row = get(account_id)
    if not row or not row['is_active'] or not hmac.compare_digest(fingerprint, _fingerprint(row['password_hash'])):
        return None
    return row


# ── İlk kurulum kodu ─────────────────────────────────────────────────────

def _setup_code_path():
    return db.DB_PATH.parent / 'setup_code'


def announce_setup_code():
    """Etkin yönetici yoksa kurulum kodunu üretir ve her açılışta günlüğe yazar."""
    if not setup_required():
        _setup_code_path().unlink(missing_ok=True)
        return
    path = _setup_code_path()
    if not path.exists():
        digits = f'{secrets.randbelow(10 ** 8):08d}'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{digits[:4]}-{digits[4:]}', encoding='ascii')
    logger.warning('İlk yönetici henüz oluşturulmadı. Siteyi açın ve şu kurulum kodunu girin: %s',
                   path.read_text(encoding='ascii').strip())


def check_setup_code(code):
    path = _setup_code_path()
    if not path.exists():
        return False
    expected = ''.join(ch for ch in path.read_text(encoding='ascii') if ch.isdigit())
    given = ''.join(ch for ch in str(code or '') if ch.isdigit())
    return bool(expected) and hmac.compare_digest(given, expected)


def clear_setup_code():
    _setup_code_path().unlink(missing_ok=True)


# ── Hatalı giriş sınırı ──────────────────────────────────────────────────

class LoginThrottle:
    def __init__(self):
        self._failures = {}
        self._lock = threading.Lock()

    def _recent(self, key, now):
        attempts = self._failures.setdefault(key, deque())
        while attempts and now - attempts[0] > FAILED_LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        return attempts

    def is_blocked(self, key):
        with self._lock:
            return len(self._recent(key, time.monotonic())) >= FAILED_LOGIN_LIMIT

    def record_failure(self, key):
        with self._lock:
            now = time.monotonic()
            self._recent(key, now).append(now)

    def clear(self, key):
        with self._lock:
            self._failures.pop(key, None)
