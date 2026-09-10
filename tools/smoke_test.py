"""Uçtan uca duman testi: web.py'yi gerçekten başlatır ve ulaşılabilen her düğmeye basar.

    python tools/smoke_test.py

Geçici bir klasörde boş veritabanıyla çalışır (canlı veriye dokunmaz), kurulum
koduyla ilk yöneticiyi oluşturur, giriş yapar, ana menüden başlayarak her
düğmeyi dener ve metin bekleyen ekranlara örnek metin yazar. Hata ekranı veya
HTTP hatası görülürse listeler ve 1 ile çıkar.
"""
import http.cookiejar
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ADDON = Path(__file__).resolve().parent.parent / 'su_urunleri_bot'
WEB_PORT, INGRESS_PORT = 18101, 18099
BASE = f'http://127.0.0.1:{WEB_PORT}'
MAX_DEPTH, MAX_PRESSES = 5, 4000
ERROR_MARKERS = ('Bir hata oluştu', 'Sunucuda beklenmeyen')
SAMPLE_TEXTS = ('levrek', '12')

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


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
    work = Path(tempfile.mkdtemp(prefix='suurunleri_smoke_'))
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

        def replay(path):
            nonlocal presses
            status, view = 200, call('/api/action', {'data': 'menu'})[1]
            for data in path:
                status, view = call('/api/action', {'data': data})
                presses += 1
                if status != 200:
                    break
            return status, view

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
