'use strict';

(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const ui = {
    boot: $('#boot'), auth: $('#auth'), app: $('#app'),
    loginForm: $('#login-form'), setupForm: $('#setup-form'), ingressNote: $('#ingress-note'),
    screen: $('#screen'), buttons: $('#buttons'), topSlot: $('#top-slot'), inlineSlot: $('#inline-slot'),
    composer: $('#composer'), input: $('#composer-input'),
    accountBtn: $('#account-btn'), accountMenu: $('#account-menu'),
    busy: $('#busy'), busyText: $('#busy-text'), toast: $('#toast'),
    passwordDialog: $('#password-dialog'), passwordForm: $('#password-form'),
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
  const ALLOWED_TAGS = new Set(['B', 'STRONG', 'I', 'EM', 'U', 'S', 'CODE', 'PRE', 'A', 'BR']);

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
    ui.input.placeholder = inline ? MODE_PLACEHOLDER[mode] : SEARCH_PLACEHOLDER;
    ui.input.inputMode = /length/.test(mode || '') ? 'decimal' : 'text';
    ui.input.rows = mode === 'ai_analysis' ? 6 : 1;
    ui.input.value = '';
    autosize();
    if (inline && focus) setTimeout(() => ui.input.focus({ preventScroll: true }), 30);
  }

  function autosize() {
    if (ui.composer.classList.contains('multiline')) { ui.input.style.height = ''; return; }
    ui.input.style.height = 'auto';
    ui.input.style.height = `${Math.min(ui.input.scrollHeight, 160)}px`;
  }

  // ── Ekranı çiz ─────────────────────────────────────────────────────────
  const viewKey = (view) => JSON.stringify([view.blocks, view.buttons, view.mode || null]);

  function render(view, { push = true, focus = true } = {}) {
    const changed = !current || viewKey(current) !== viewKey(view);
    current = { blocks: view.blocks || [], buttons: view.buttons || [], mode: view.mode || null };

    ui.screen.replaceChildren();
    for (const block of current.blocks) {
      const div = el('div', 'block');
      div.append(sanitize(block));
      ui.screen.append(div);
    }
    ui.screen.hidden = current.blocks.length === 0;

    ui.buttons.replaceChildren();
    for (const row of current.buttons) {
      const line = el('div', 'row');
      line.dataset.count = String(row.length);
      for (const button of row) {
        const node = el('button', `btn ${tone(button.text)}`.trim(), button.text);
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

  function showAuth() {
    ui.app.hidden = true;
    ui.auth.hidden = false;
    ui.setupForm.hidden = !session.setup_required;
    ui.loginForm.hidden = session.setup_required;
    ui.ingressNote.hidden = !session.ingress;
    const first = $('input', session.setup_required ? ui.setupForm : ui.loginForm);
    setTimeout(() => first.focus(), 30);
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
    const item = el('li', `person${person.is_active ? '' : ' inactive'}`);
    const head = el('div', 'person-head');
    const name = el('div', 'person-name');
    name.append(el('b', '', person.display_name), el('small', '', `@${person.username}`));
    const badges = el('div', 'badges');
    if (person.is_admin) badges.append(el('span', 'badge', 'Yönetici'));
    if (!person.is_active) badges.append(el('span', 'badge muted', 'Pasif'));
    if (person.ha_linked) badges.append(el('span', 'badge muted', 'HA paneli bağlı'));
    head.append(name, badges);

    const meta = el('div', 'person-meta', person.last_login
      ? `Son giriş: ${person.last_login.replace('T', ' ').slice(0, 16)}` : 'Henüz giriş yapmadı');

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

    actions.append(
      personAction('🔑 Şifre ver', () => { passwordBox.hidden = !passwordBox.hidden; if (!passwordBox.hidden) passwordInput.focus(); }),
      personAction(person.is_admin ? 'Yöneticiliği kaldır' : 'Yönetici yap',
        () => updatePerson(person.id, { is_admin: !person.is_admin }, 'Yetki güncellendi.')),
      personAction(person.is_active ? 'Pasif yap' : 'Etkinleştir',
        () => updatePerson(person.id, { is_active: !person.is_active }, person.is_active ? 'Kişi pasif yapıldı.' : 'Kişi etkinleştirildi.'),
        person.is_active ? 'danger' : ''),
    );
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
  ui.setupForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitForm(ui.setupForm, 'api/setup', start);
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

  ui.accountBtn.addEventListener('click', (event) => { event.stopPropagation(); toggleMenu(ui.accountMenu.hidden); });
  document.addEventListener('click', (event) => { if (!ui.accountMenu.contains(event.target)) toggleMenu(false); });
  ui.accountMenu.addEventListener('click', (event) => {
    const command = event.target.closest('[data-cmd]');
    if (!command) return;
    toggleMenu(false);
    if (command.dataset.cmd === 'logout') logout();
    if (command.dataset.cmd === 'people') openPeople();
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
