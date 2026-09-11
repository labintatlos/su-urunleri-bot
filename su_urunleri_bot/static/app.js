'use strict';

(() => {
  // KeenDNS bulut tüneli http:// isteğini de siteye iletir ve sunucuya hangi
  // şemayla gelindiğini bildirmez; bu yüzden yönlendirmeyi tarayıcı yapar.
  // Ev ağındaki IP/.local adresleri ve Home Assistant paneli (çerçeve) hariç.
  const host = location.hostname;
  const localHost = host === 'localhost' || host.endsWith('.local') || !host.includes('.') || /^[\d.]+$|:/.test(host);
  if (location.protocol === 'http:' && window.top === window.self && !localHost) {
    location.replace(`https://${location.host}${location.pathname}${location.search}${location.hash}`);
    return;
  }

  const $ = (selector, root = document) => root.querySelector(selector);
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const ui = {
    boot: $('#boot'), auth: $('#auth'), app: $('#app'),
    authTabs: $('#auth-tabs'), loginForm: $('#login-form'), registerForm: $('#register-form'),
    resetForm: $('#reset-form'), setupForm: $('#setup-form'), ingressNote: $('#ingress-note'),
    screen: $('#screen'), buttons: $('#buttons'), topSlot: $('#top-slot'), inlineSlot: $('#inline-slot'),
    composer: $('#composer'), input: $('#composer-input'),
    accountBtn: $('#account-btn'), accountMenu: $('#account-menu'),
    busy: $('#busy'), busyText: $('#busy-text'), toast: $('#toast'),
    passwordDialog: $('#password-dialog'), passwordForm: $('#password-form'),
    issueDialog: $('#issue-dialog'), issueForm: $('#issue-form'),
    peopleDialog: $('#people-dialog'), peopleList: $('#people-list'), personForm: $('#person-form'),
  };

  let session = null;
  let current = null;
  let busy = false;

  // ── Sunucu ─────────────────────────────────────────────────────────────
  // Adresler göreli yazılır: site hem kök dizinde (KeenDNS) hem de Home
  // Assistant panelinin /api/hassio_ingress/... önekinin altında açılır.
  async function api(method, path, body) {
    const response = await fetch(path, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'SuUrunleri' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data = null;
    try { data = await response.json(); } catch (_) { /* boş yanıt */ }
    if (!response.ok) {
      const error = new Error((data && data.error) || `Sunucuya ulaşılamadı (${response.status}).`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  // ── Ekran metni ────────────────────────────────────────────────────────
  // Ekran metinleri sunucuda kaçışlanmış, yalnızca birkaç biçim etiketi
  // taşıyan HTML'dir. Yine de tarayıcıya yalnızca izin verilen etiketler
  // geçer; bağlantılar yeni sekmede açılır, boş fotoğraf bağlantısı resim olur.
  const ALLOWED_TAGS = new Set([
    'B', 'STRONG', 'I', 'EM', 'U', 'S', 'CODE', 'PRE', 'A', 'BR',
    'TABLE', 'THEAD', 'TBODY', 'TR', 'TH', 'TD',
  ]);

  function sanitize(html) {
    const template = document.createElement('template');
    template.innerHTML = html;
    const walk = (node) => {
      for (const child of [...node.childNodes]) {
        if (child.nodeType === Node.TEXT_NODE) continue;
        if (child.nodeType !== Node.ELEMENT_NODE || !ALLOWED_TAGS.has(child.tagName)) {
          if (child.nodeType === Node.ELEMENT_NODE) { walk(child); child.replaceWith(...child.childNodes); }
          else child.remove();
          continue;
        }
        const href = child.tagName === 'A' ? (child.getAttribute('href') || '') : '';
        for (const attr of [...child.attributes]) child.removeAttribute(attr.name);
        if (child.tagName === 'A') {
          if (!/^https?:\/\//i.test(href)) { walk(child); child.replaceWith(...child.childNodes); continue; }
          if (!child.textContent.replace(/[‍\s]/g, '') && /\.(jpe?g|png|webp|gif)$/i.test(href)) {
            const img = el('img', 'photo');
            img.src = href; img.alt = ''; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer';
            img.addEventListener('error', () => img.remove());
            child.replaceWith(img);
            continue;
          }
          child.href = href; child.target = '_blank'; child.rel = 'noopener noreferrer';
        }
        walk(child);
      }
    };
    walk(template.content);
    return template.content;
  }

  function tone(text) {
    if (/^(🚨|⚖️ Değerlendirmeyi|⚖️ Bu Denetimi|↩️ Yarıda)/u.test(text)) return 'accent';
    if (/^(🏠|↩️|🔙|⬅️|◀️|➡️ Sonraki|Sonraki|⏭️)/u.test(text)) return 'nav';
    if (/^✅/u.test(text)) return 'ok';
    if (/^❌/u.test(text)) return 'bad';
    if (/^(⚪|❔)/u.test(text)) return 'neutral';
    return '';
  }

  // ── Yazma kutusu ───────────────────────────────────────────────────────
  // Ekran bir cevap beklediğinde (tür adı, gemi boyu, tarih, olay metni…)
  // kutu ekranın içine taşınır; aksi halde üst çubukta genel arama kutusudur.
  const SEARCH_PLACEHOLDER = 'Tür, ceza veya mevzuat ara… (örn. hamsi, ruhsatsız)';
  // Dar ekranda uzun ipucu iki satıra kırılıp üst çubuğu büyütüyordu.
  const SHORT_SEARCH_PLACEHOLDER = 'Ara…';
  const narrowScreen = window.matchMedia('(max-width: 640px)');
  const searchPlaceholder = () => (narrowScreen.matches ? SHORT_SEARCH_PLACEHOLDER : SEARCH_PLACEHOLDER);
  const MODE_PLACEHOLDER = {
    ai_analysis: 'Olayı ayrıntılı yazın…',
    penalty: 'İhlali veya olayı yazın…',
    species_search: 'Tür adını yazın…',
    audit_species_search: 'Tür adını yazın…',
    source_search: 'Madde numarası veya konu yazın…',
    gear: 'Av aracını veya yöntemi yazın…',
    place: 'Yer, il, koy veya saha adını yazın…',
    lawsearch: 'Aranacak kelimeyi yazın…',
    audit_length_exact: 'Gemi boyu (metre) — örn. 17.4',
    penalty_length: 'Gemi boyu (metre) — örn. 17.4',
    audit_date: 'GG.AA.YYYY — örn. 20.05.2026',
    guide_measure: 'Değeri yazın…',
  };

  function placeComposer(mode, focus) {
    const inline = Boolean(mode && MODE_PLACEHOLDER[mode]);
    ui.composer.classList.toggle('inline', inline);
    ui.composer.classList.toggle('multiline', mode === 'ai_analysis');
    (inline ? ui.inlineSlot : ui.topSlot).append(ui.composer);
    ui.input.placeholder = inline ? MODE_PLACEHOLDER[mode] : searchPlaceholder();
    ui.input.inputMode = /length/.test(mode || '') ? 'decimal' : 'text';
    ui.input.rows = mode === 'ai_analysis' ? 6 : 1;
    ui.input.value = '';
    autosize();
    if (inline && focus) setTimeout(() => ui.input.focus({ preventScroll: true }), 30);
  }

  function autosize() {
    if (ui.composer.classList.contains('multiline')) { ui.input.style.height = ''; return; }
    // Boş kutuda scrollHeight ipucu metnini de sayar; tek satır kalsın.
    if (!ui.input.value) { ui.input.style.height = ''; return; }
    ui.input.style.height = 'auto';
    ui.input.style.height = `${Math.min(ui.input.scrollHeight, 160)}px`;
  }

  // ── Ekranı çiz ─────────────────────────────────────────────────────────
  const viewKey = (view) => JSON.stringify([view.blocks, view.buttons, view.mode || null]);

  const HOME_TOOLS = {
    'guide:menu': ['Kontrol föyleri', 'Tekne türüne özel maddeleri adım adım kontrol edin.', 'ship'],
    'audit:start': ['Yönlendirilmiş kontrol', 'Bölge, faaliyet ve av bilgileriyle denetiminizi başlatın.', 'compass'],
    'ceza:menu': ['İhlaller ve yaptırımlar', 'Ceza tutarlarına, işlemlere ve dayanak maddelerine ulaşın.', 'book'],
    'turcizelge:menu': ['Tür bilgileri', 'Asgari boy, miktar ve zaman yasaklarını inceleyin.', 'fish'],
    'vessel:menu': ['Gemi ve donanım', 'Ruhsat, belge ve izleme sistemi kontrollerini açın.', 'ship'],
    'field:Kolluk İşlemi': ['Saha rehberi', 'Denetimde uygulanacak kolluk işlemlerini inceleyin.', 'clipboard'],
    'ai:start': ['Olay değerlendirmesi', 'Olayı anlatın; ilgili mevzuatla birlikte değerlendirin.', 'scales'],
    'admin:panel': ['Yönetim', 'Kullanıcılar, işlem kayıtları ve sorun bildirimleri.', 'shield'],
  };
  const ICON_PATHS = {
    ship: 'M4 14l8 5 8-5-2 6H6l-2-6Zm3 1V8h10v7M10 8V4h4v4M2 22h20',
    compass: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM16 8l-3 5-5 3 3-5 5-3Z',
    book: 'M12 5v16M12 5C9 3 5 3 2 4v15c4-1 7 0 10 2 3-2 6-3 10-2V4c-3-1-7-1-10 1Z',
    fish: 'M3 12c4-7 10-7 14-2l4-4v12l-4-4c-4 5-10 5-14-2ZM7 11v2',
    clipboard: 'M9 5H5v17h14V5h-4M9 3h6v5H9V3Zm-1 9h8m-8 5h6',
    scales: 'M12 3v18M7 21h10M3 7h18M6 7l-4 8h8L6 7Zm12 0-4 8h8l-4-8Z',
    shield: 'M12 2l8 4v7c0 5-8 9-8 9s-8-4-8-9V6l8-4Zm-4 10 3 3 5-6',
    // Ekran başlıklarında ve düğmelerde emoji yerine kullanılan ek simgeler
    // (bkz. EMOJI_ICON / iconFor) — işletim sistemine göre değişmeyen tutarlı
    // bir görünüm için; dış servise ihtiyaç duymaz.
    home: 'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',
    back: 'M19 12H5M11 18l-6-6 6-6',
    arrowRight: 'M5 12h14M13 6l6 6-6 6',
    check: 'M20 6 9 17l-5-5',
    close: 'M18 6 6 18M6 6l12 12',
    circle: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z',
    rod: 'M4 20 18 6M17 5l2 2M9 15a3 3 0 1 1-4.24 4.24',
    alert: 'M12 3 2 20h20L12 3ZM12 9v5M12 17h.01',
    search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM21 21l-4.3-4.3',
    barChart: 'M4 20V10M10 20V4M16 20v-6M2 20h20',
    waves: 'M2 12c2-2.5 4-2.5 6 0s4 2.5 6 0 4-2.5 6 0M2 18c2-2.5 4-2.5 6 0s4 2.5 6 0 4-2.5 6 0',
    package: 'M21 8 12 3 3 8v8l9 5 9-5ZM3 8l9 5 9-5M12 13v8',
    calendar: 'M4 8h16M6 4v4M18 4v4M4 8v11a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V8a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1Z',
    lock: 'M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4',
    repeat: 'M17 2l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3',
    users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
    user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
    receipt: 'M6 2h9l3 3v17H6ZM15 2v3h3M9 8h3M9 12h6M9 16h6',
  };
  function toolIcon(name) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', ICON_PATHS[name]);
    svg.append(path);
    return svg;
  }

  // Ekranların ve düğmelerin başındaki emoji, tanınıyorsa yukarıdaki SVG
  // simgeyle değiştirilir (metnin geri kalanı aynen kalır). Bir emoji burada
  // yoksa dokunulmadan görünmeye devam eder — bu yüzden bütün emoji setini
  // kapsamak zorunda değil, yalnızca en sık kullanılanları yeterli.
  const EMOJI_ICON = {
    '🏠': 'home', '↩️': 'back', '🔙': 'back', '⬅️': 'back', '◀️': 'back',
    '➡️': 'arrowRight', '⏭️': 'arrowRight',
    '✅': 'check', '❌': 'close', '⚪': 'circle',
    '⚖️': 'scales', '🎣': 'rod', '🚨': 'alert', '🔎': 'search', '🔍': 'search',
    '📊': 'barChart', '🐟': 'fish', '📋': 'clipboard',
    '📖': 'book', '📚': 'book',
    '🌊': 'waves',
    '🚤': 'ship', '🚢': 'ship', '🛳': 'ship', '🧭': 'compass',
    '📦': 'package', '📅': 'calendar', '🗓': 'calendar',
    '🔐': 'lock', '🔁': 'repeat', '🔄': 'repeat',
    '👥': 'users', '👤': 'user', '🧾': 'receipt',
  };
  function iconFor(text) {
    for (const glyph of Object.keys(EMOJI_ICON)) {
      if (text.startsWith(glyph)) {
        return { name: EMOJI_ICON[glyph], rest: text.slice(glyph.length).replace(/^\s+/, '') };
      }
    }
    return null;
  }

  // Sunucu metnindeki ━━━ ayırıcıları sabit uzunlukta olduğu için dar ekranda
  // alt satıra taşıyordu; ekran genişliğine uyan bir çizgiye çevrilir.
  function drawRules(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) if (/━{6,}/.test(walker.currentNode.nodeValue)) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const fragment = document.createDocumentFragment();
      node.nodeValue.split(/━{6,}/).forEach((part, index) => {
        if (index) fragment.append(el('span', 'rule'));
        if (part) fragment.append(part);
      });
      node.replaceWith(fragment);
    }
  }

  // Ceza ve tür çizelgesi ekranları büyük kategorileri artık düz metin
  // yerine bir <table> olarak gönderir. Satır sayısı fazlaysa tablonun
  // üstüne satırları metinle süzen bir arama kutusu eklenir.
  const TABLE_FILTER_MIN_ROWS = 8;

  function attachTableFilters(root) {
    for (const table of [...root.querySelectorAll('table')]) {
      if (!table.tBodies[0]) continue;
      const rows = [...table.tBodies[0].rows];
      const wrap = el('div', 'table-wrap');
      const scroll = el('div', 'table-scroll');
      table.replaceWith(wrap);
      scroll.append(table);
      if (rows.length >= TABLE_FILTER_MIN_ROWS) {
        const filter = el('input', 'table-filter');
        filter.type = 'search';
        filter.placeholder = `${rows.length} satırda ara…`;
        filter.addEventListener('input', () => {
          const needle = filter.value.toLocaleLowerCase('tr').trim();
          for (const row of rows) {
            row.hidden = needle !== '' && !row.textContent.toLocaleLowerCase('tr').includes(needle);
          }
        });
        wrap.append(filter);
      }
      wrap.append(scroll);
    }
  }

  // Bir bloğun en baştaki metnini (kalın başlığın içinde veya dışında olsun)
  // tanınan bir emoji ile başlıyorsa SVG simgeyle değiştirir. Yalnızca bloğun
  // İLK metin düğümüne bakar; içerideki madde işaretleri (✅/❌ vb.) etkilenmez.
  function swapHeadingIcon(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const first = walker.nextNode();
    if (!first || !first.nodeValue) return;
    const match = iconFor(first.nodeValue);
    if (!match) return;
    const icon = el('span', 'heading-icon');
    icon.append(toolIcon(match.name));
    first.nodeValue = match.rest;
    first.parentNode.insertBefore(icon, first);
  }

  function render(view, { push = true, focus = true } = {}) {
    const changed = !current || viewKey(current) !== viewKey(view);
    current = { blocks: view.blocks || [], buttons: view.buttons || [], mode: view.mode || null };
    const isHome = current.buttons.flat().some(button => button.data === 'audit:start')
      && current.buttons.flat().some(button => button.data === 'ceza:menu');
    $('.stage').classList.toggle('home-stage', isHome);
    $('#tools-title').hidden = !isHome;
    $('#page-context').textContent = isHome ? 'Ana sayfa' : 'Denetim çalışma alanı';

    ui.screen.replaceChildren();
    for (const block of current.blocks) {
      const div = el('div', 'block');
      div.append(sanitize(block));
      drawRules(div);
      attachTableFilters(div);
      swapHeadingIcon(div);
      ui.screen.append(div);
    }
    ui.screen.hidden = current.blocks.length === 0;

    ui.buttons.replaceChildren();
    for (const row of current.buttons) {
      const line = el('div', 'row');
      line.dataset.count = String(row.length);
      for (const button of row) {
        const node = el('button', `btn ${tone(button.text)}`.trim(), button.text);
        node.dataset.action = button.data;
        const tool = isHome && HOME_TOOLS[button.data];
        if (tool) {
          node.classList.add('tool-card');
          if (button.data === 'audit:start') node.classList.add('featured');
          const icon = el('span', 'tool-icon');
          icon.append(toolIcon(tool[2]));
          const copy = el('span', 'tool-copy');
          copy.append(el('small', 'tool-category', tool[0]),
            el('span', 'tool-name', button.text.replace(/^[^\p{L}\p{N}]+/u, '')),
            el('span', 'tool-description', tool[1]));
          const arrow = el('span', 'tool-arrow', '↗');
          arrow.setAttribute('aria-hidden', 'true');
          node.replaceChildren(icon, copy, arrow);
        } else {
          const match = iconFor(button.text);
          if (match) {
            const icon = el('span', 'btn-icon');
            icon.append(toolIcon(match.name));
            node.replaceChildren(icon, document.createTextNode(match.rest));
          }
        }
        node.type = 'button';
        node.addEventListener('click', () => press(button.data));
        line.append(node);
      }
      ui.buttons.append(line);
    }

    placeComposer(current.mode, focus);
    if (push && changed) history.pushState({ view: current }, '');
    else history.replaceState({ view: current }, '');
    if (changed) window.scrollTo({ top: 0 });
  }

  // ── İstekler ───────────────────────────────────────────────────────────
  let busyTimer = null;

  function setBusy(on, long) {
    busy = on;
    document.body.classList.toggle('is-busy', on);
    clearTimeout(busyTimer);
    if (on) {
      ui.busyText.textContent = long
        ? 'Mevzuat belgeleri taranıyor… Bu işlem 20-45 saniye sürebilir.'
        : 'Yükleniyor…';
      busyTimer = setTimeout(() => { ui.busy.hidden = false; }, long ? 0 : 350);
    } else {
      ui.busy.hidden = true;
    }
  }

  async function request(call, long) {
    if (busy) return;
    setBusy(true, long);
    try {
      const view = await call();
      render(view);
      if (view.alert) toast(view.alert);
    } catch (error) {
      if (error.status === 401) { await start(); return; }
      toast(error.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  function press(data) {
    if (data === 'web:people') { openPeople(); return; }
    request(() => api('POST', 'api/action', { data }), data === 'ai:audit:run');
  }

  function sendText() {
    const text = ui.input.value.trim();
    if (!text || busy) return;
    const long = Boolean(current && current.mode === 'ai_analysis');
    ui.input.blur();
    request(() => api('POST', 'api/text', { text }), long);
  }

  // ── Bildirim ───────────────────────────────────────────────────────────
  let toastTimer = null;

  function toast(message, kind) {
    ui.toast.textContent = message;
    ui.toast.className = `toast ${kind || ''}`.trim();
    ui.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { ui.toast.hidden = true; }, Math.max(3500, message.length * 60));
  }

  // ── Giriş ──────────────────────────────────────────────────────────────
  function formError(form, message) {
    const node = $('.form-error', form);
    node.textContent = message || '';
    node.hidden = !message;
  }

  function formData(form) {
    const data = {};
    for (const field of form.elements) {
      if (!field.name) continue;
      data[field.name] = field.type === 'checkbox' ? field.checked : field.value;
    }
    return data;
  }

  async function submitForm(form, path, after) {
    const submit = $('button[type=submit]', form);
    formError(form, '');
    submit.disabled = true;
    try {
      await api('POST', path, formData(form));
      await after();
    } catch (error) {
      formError(form, error.message);
    } finally {
      submit.disabled = false;
    }
  }

  function showAuthView(view) {
    ui.loginForm.hidden = view !== 'login';
    ui.registerForm.hidden = view !== 'register';
    ui.resetForm.hidden = view !== 'reset';
    for (const tab of ui.authTabs.querySelectorAll('[data-auth-view]')) {
      const active = tab.dataset.authView === view;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
    }
    ui.ingressNote.hidden = view !== 'login' || !session.ingress;
    const first = $('input', view === 'login' ? ui.loginForm : view === 'register' ? ui.registerForm : ui.resetForm);
    setTimeout(() => first.focus(), 30);
  }

  function showAuth() {
    ui.app.hidden = true;
    ui.auth.hidden = false;
    ui.setupForm.hidden = !session.setup_required;
    ui.authTabs.hidden = session.setup_required;
    if (session.setup_required) {
      ui.loginForm.hidden = true;
      ui.registerForm.hidden = true;
      ui.resetForm.hidden = true;
      setTimeout(() => $('input', ui.setupForm).focus(), 30);
    } else {
      showAuthView('login');
    }
  }

  async function showApp() {
    const user = session.user;
    ui.auth.hidden = true;
    ui.app.hidden = false;
    $('#account-name').textContent = user.display_name;
    $('#account-username').textContent = `@${user.username}${user.is_admin ? ' · yönetici' : ''}`;
    $('#account-initial').textContent = (user.display_name.trim()[0] || '•').toLocaleUpperCase('tr');
    $('[data-cmd=people]', ui.accountMenu).hidden = !user.is_admin;
    $('[data-cmd=logout]', ui.accountMenu).hidden = user.via === 'ingress';
    const view = await api('GET', 'api/screen');
    render(view, { push: false, focus: false });
  }

  async function start() {
    try {
      session = await api('GET', 'api/session');
    } catch (error) {
      ui.boot.textContent = 'Sunucuya ulaşılamadı. Sayfayı yenileyin.';
      return;
    }
    ui.boot.hidden = true;
    if (session.user) {
      try { await showApp(); } catch (error) { toast(error.message, 'error'); }
    } else {
      showAuth();
    }
  }

  // ── Hesap menüsü ───────────────────────────────────────────────────────
  function toggleMenu(open) {
    ui.accountMenu.hidden = !open;
    ui.accountBtn.setAttribute('aria-expanded', String(open));
  }

  async function logout() {
    try { await api('POST', 'api/logout', {}); } catch (_) { /* yine de çık */ }
    current = null;
    await start();
  }

  // ── Kişiler ────────────────────────────────────────────────────────────
  function personAction(label, handler, className) {
    const button = el('button', `btn small ${className || ''}`.trim(), label);
    button.type = 'button';
    button.addEventListener('click', handler);
    return button;
  }

  async function updatePerson(id, changes, message) {
    try {
      await api('POST', `api/people/${id}`, changes);
      toast(message);
      await loadPeople();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  function personRow(person) {
    const item = el('li', `person${person.approval_status === 'rejected' ? ' inactive' : ''}`);
    const head = el('div', 'person-head');
    const name = el('div', 'person-name');
    name.append(el('b', '', person.display_name), el('small', '', `@${person.username}`));
    const badges = el('div', 'badges');
    if (person.is_admin) badges.append(el('span', 'badge', 'Yönetici'));
    if (person.approval_status === 'pending') badges.append(el('span', 'badge warning', 'Onay bekliyor'));
    if (person.approval_status === 'rejected') badges.append(el('span', 'badge muted', 'Reddedildi'));
    if (person.approval_status === 'approved' && !person.is_active) badges.append(el('span', 'badge muted', 'Pasif'));
    if (person.reset_pending) badges.append(el('span', 'badge warning', 'Şifre talebi'));
    if (person.ha_linked) badges.append(el('span', 'badge muted', 'HA paneli bağlı'));
    head.append(name, badges);

    const positionNames = { subay: 'Subay', astsubay: 'Astsubay', uzman: 'Uzman', memur: 'Memur' };
    const info = [];
    if (person.position) info.push(positionNames[person.position] || person.position);
    if (person.email) info.push(person.email);
    if (person.phone) info.push(person.phone);
    info.push(person.last_login ? `Son giriş: ${person.last_login.replace('T', ' ').slice(0, 16)}` : 'Henüz giriş yapmadı');
    const meta = el('div', 'person-meta', info.join(' · '));

    const actions = el('div', 'person-actions');
    const passwordBox = el('form', 'inline-password');
    passwordBox.hidden = true;
    const passwordInput = el('input');
    Object.assign(passwordInput, { type: 'password', minLength: 8, required: true, placeholder: 'Yeni şifre (en az 8)', autocomplete: 'new-password' });
    const save = el('button', 'btn small primary', 'Kaydet');
    save.type = 'submit';
    passwordBox.append(passwordInput, save);
    passwordBox.addEventListener('submit', (event) => {
      event.preventDefault();
      updatePerson(person.id, { password: passwordInput.value }, `${person.display_name} için yeni şifre kaydedildi.`);
    });

    if (person.approval_status !== 'approved') {
      actions.append(personAction('✅ Üyeliği onayla',
        () => updatePerson(person.id, { approval_status: 'approved' }, `${person.display_name} onaylandı.`), 'primary'));
      if (person.approval_status === 'pending') {
        actions.append(personAction('❌ Reddet',
          () => updatePerson(person.id, { approval_status: 'rejected' }, `${person.display_name} reddedildi.`), 'danger'));
      }
    } else {
      actions.append(
        personAction(person.reset_pending ? '🔑 Talebi yanıtla' : '🔑 Şifre ver',
          () => { passwordBox.hidden = !passwordBox.hidden; if (!passwordBox.hidden) passwordInput.focus(); }),
        personAction(person.is_admin ? 'Yöneticiliği kaldır' : 'Yönetici yap',
          () => updatePerson(person.id, { is_admin: !person.is_admin }, 'Yetki güncellendi.')),
        personAction(person.is_active ? 'Pasif yap' : 'Etkinleştir',
          () => updatePerson(person.id, { is_active: !person.is_active }, person.is_active ? 'Kişi pasif yapıldı.' : 'Kişi etkinleştirildi.'),
          person.is_active ? 'danger' : ''),
      );
    }
    item.append(head, meta, actions, passwordBox);
    return item;
  }

  async function loadPeople() {
    const { people } = await api('GET', 'api/people');
    ui.peopleList.replaceChildren(...people.map(personRow));
  }

  async function openPeople() {
    toggleMenu(false);
    try {
      await loadPeople();
      ui.peopleDialog.showModal();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  // ── Olaylar ────────────────────────────────────────────────────────────
  ui.loginForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(ui.loginForm, 'api/login', start);
  });
  ui.registerForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const data = formData(ui.registerForm);
    if (data.password !== data.again) { formError(ui.registerForm, 'Şifreler aynı değil.'); return; }
    submitForm(ui.registerForm, 'api/register', async () => {
      ui.registerForm.reset();
      showAuthView('login');
      toast('Başvurunuz alındı. Yönetici onayından sonra giriş yapabilirsiniz.');
    });
  });
  ui.resetForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(ui.resetForm, 'api/password-reset', async () => {
      ui.resetForm.reset();
      showAuthView('login');
      toast('Hesap eşleşirse şifre yenileme talebiniz yöneticiye iletildi.');
    });
  });
  ui.setupForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(ui.setupForm, 'api/setup', start);
  });

  ui.auth.addEventListener('click', (event) => {
    const button = event.target.closest('[data-auth-view]');
    if (button && !session.setup_required) showAuthView(button.dataset.authView);
  });

  ui.composer.addEventListener('submit', (event) => { event.preventDefault(); sendText(); });
  ui.input.addEventListener('input', autosize);
  ui.input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.isComposing) return;
    const multiline = ui.composer.classList.contains('multiline');
    if (multiline ? (event.ctrlKey || event.metaKey) : !event.shiftKey) {
      event.preventDefault();
      sendText();
    }
  });

  $('#home-btn').addEventListener('click', () => press('menu'));
  narrowScreen.addEventListener('change', () => {
    if (!ui.composer.classList.contains('inline')) ui.input.placeholder = searchPlaceholder();
  });

  ui.accountBtn.addEventListener('click', (event) => { event.stopPropagation(); toggleMenu(ui.accountMenu.hidden); });
  document.addEventListener('click', (event) => { if (!ui.accountMenu.contains(event.target)) toggleMenu(false); });
  ui.accountMenu.addEventListener('click', (event) => {
    const command = event.target.closest('[data-cmd]');
    if (!command) return;
    toggleMenu(false);
    if (command.dataset.cmd === 'logout') logout();
    if (command.dataset.cmd === 'people') openPeople();
    if (command.dataset.cmd === 'issue') {
      ui.issueForm.reset();
      formError(ui.issueForm, '');
      ui.issueDialog.showModal();
      setTimeout(() => $('textarea', ui.issueForm).focus(), 30);
    }
    if (command.dataset.cmd === 'password') {
      ui.passwordForm.reset();
      formError(ui.passwordForm, '');
      ui.passwordDialog.showModal();
    }
  });

  for (const close of document.querySelectorAll('[data-close]')) {
    close.addEventListener('click', () => close.closest('dialog').close());
  }

  ui.passwordForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const data = formData(ui.passwordForm);
    if (data.new !== data.again) { formError(ui.passwordForm, 'Yeni şifreler aynı değil.'); return; }
    submitForm(ui.passwordForm, 'api/password', async () => {
      ui.passwordDialog.close();
      toast('Şifreniz değiştirildi.');
    });
  });

  ui.issueForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(ui.issueForm, 'api/issues', async () => {
      ui.issueDialog.close();
      ui.issueForm.reset();
      toast('Sorun bildiriminiz yöneticiye iletildi.');
    });
  });

  ui.personForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(ui.personForm, 'api/people', async () => {
      const name = ui.personForm.elements.display_name.value;
      ui.personForm.reset();
      toast(`${name} eklendi. Kullanıcı adını ve şifresini kendisine iletin.`);
      await loadPeople();
    });
  });

  window.addEventListener('popstate', (event) => {
    if (event.state && event.state.view && !busy) render(event.state.view, { push: false, focus: false });
  });

  start();
})();
