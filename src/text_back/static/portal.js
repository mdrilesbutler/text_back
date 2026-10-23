// TextBack client settings: progressive enhancement only. Every page works without this file.
// One plain ES module, no dependencies. Data from the server arrives in #tb-data (JSON, not executed);
// hooks are data-* attributes and ids (see docs/notes/ui-compare-a/implementation-plan.md §F).
const root = document.documentElement;
root.classList.replace('no-js', 'js');

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const DATA = (() => { try { return JSON.parse($('#tb-data')?.textContent || '{}'); } catch { return {}; } })();
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)');
const WIDE = matchMedia('(min-width: 1024px)');
const GROWS = !(window.CSS && CSS.supports('field-sizing', 'content'));
// Every string this file puts on screen (spec §6).
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const COPY = {
  clean: 'No unsaved changes', saved: 'Saved just now', notSaved: 'Not saved',
  notSavedLong: n => (n ? `Not saved · ${plural(n, 'unsaved change')}` : 'Not saved'),
  unsavedShort: n => `${n} unsaved`, unsavedLong: n => plural(n, 'unsaved change'),
  saving: 'Saving…', discarded: 'Changes discarded.', undo: 'Undo', dismiss: 'Dismiss',
  restored: label => `Standard wording restored for ${label}.`, limit: (n, max) => `${n} of ${max} characters`,
  count: (n, k) => `${plural(k, 'text')} · ${n} characters`,  // = client_portal.count_label
  bill: (k, symbol) => `Billed as ${k} texts. ` +  // = client_portal.bill_label
    (symbol ? `The \u201c${symbol}\u201d symbol limits each text to 70 characters.` : 'Customers still see one message.'),
};

// ---------------------------------------------------------------- helpers
const SVG = 'http://www.w3.org/2000/svg';
function icon(name, cls = '') {
  const svg = document.createElementNS(SVG, 'svg');
  const use = document.createElementNS(SVG, 'use');
  for (const [k, v] of [['class', cls ? `icon ${cls}` : 'icon'], ['aria-hidden', 'true'], ['focusable', 'false']]) svg.setAttribute(k, v);
  use.setAttribute('href', `#i-${name}`);
  svg.append(use);
  return svg;
}

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
}

// Python's " ".join(text.split()).
const norm = s => s.split(/\s+/).filter(Boolean).join(' ');

// The one live region. A channel debounces its own messages (the save bar uses 800 ms).
const announcer = $('#announcer');
const announceTimers = {};
function announce(text, { debounce = 150, channel = 'default' } = {}) {
  if (!announcer || !text) return;
  clearTimeout(announceTimers[channel]);
  announceTimers[channel] = setTimeout(() => {
    announcer.textContent = '';
    requestAnimationFrame(() => { announcer.textContent = text; });
  }, debounce);
}

// Open every disclosure that holds a field, focus it, caret at the end, and bring it to the middle of the screen.
function focusField(field) {
  for (let d = field.closest('details'); d; d = d.parentElement.closest('details')) d.open = true;
  field.focus({ preventScroll: true });
  if (field.tagName === 'TEXTAREA') {
    const end = field.value.length;
    field.setSelectionRange(end, end);
    grow(field);
  }
  field.scrollIntoView({ block: 'center', behavior: REDUCED.matches ? 'auto' : 'smooth' });
}

function grow(ta) {
  if (!GROWS || !ta.offsetParent) return;
  ta.style.height = 'auto';
  ta.style.height = `${ta.scrollHeight + 2}px`;
}

// ---------------------------------------------------------------- appearance (System / Light / Dark)
function initTheme() {
  const picker = $('[data-theme-picker]');
  if (!picker) return;
  picker.hidden = false;
  picker.addEventListener('change', e => {
    const value = e.target.value;
    const keep = value === 'light' || value === 'dark';
    const secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `tb_theme=${keep ? value : ''}; Path=/client; Max-Age=${keep ? 31536000 : 0}; SameSite=Lax${secure}`;
    if (keep) root.dataset.theme = value;
    else delete root.dataset.theme;
  });
}

// ---------------------------------------------------------------- account menu
function initMenu() {
  const menu = $('[data-menu]');
  if (!menu) return;
  const summary = $('summary', menu);
  const close = refocus => {
    if (!menu.open) return;
    menu.open = false;
    if (refocus) summary.focus();
  };
  document.addEventListener('keydown', e => {  // registered before the toasts' Escape: an open menu wins
    if (e.key !== 'Escape' || !menu.open) return;
    e.stopImmediatePropagation();
    close(menu.contains(document.activeElement));
  });
  document.addEventListener('click', e => { if (!menu.contains(e.target)) close(false); });
  // A null relatedTarget is a click outside, which the click handler covers.
  menu.addEventListener('focusout', e => {
    if (e.relatedTarget && !menu.contains(e.relatedTarget)) close(false);
  });
}

// ---------------------------------------------------------------- toasts
const region = $('[data-toast-region]');
let currentToast = null;

function dismissToast(t, instant = false) {
  if (!t || t.gone) return;
  t.gone = true;
  clearTimeout(t.timer);
  if (currentToast === t) currentToast = null;
  const hadFocus = t.el.contains(document.activeElement);
  const remove = () => t.el.remove();
  if (instant || REDUCED.matches) remove();
  else {
    t.el.dataset.leaving = '';
    t.el.addEventListener('transitionend', remove, { once: true });
    setTimeout(remove, 400);
  }
  if (hadFocus) (t.returnFocus || $('#main'))?.focus();
}

// Float a toast element: one at a time, 6 s (8 s with an action), paused while hovered or focused.
// A floated toast has no role: the announcer speaks it once (the server's role=status is for JS off).
function floatToast(node, { ms = 6000, returnFocus = null } = {}) {
  if (!region) return null;
  dismissToast(currentToast, true);
  const t = { el: node, timer: 0, returnFocus };
  node.removeAttribute('role');
  node.classList.add('toast--floating');
  region.append(node);
  const close = $('[data-toast-close]', node);
  close.hidden = false;
  close.addEventListener('click', () => dismissToast(t));
  const run = delay => { clearTimeout(t.timer); t.timer = setTimeout(() => dismissToast(t), delay); };
  const pause = () => clearTimeout(t.timer);
  node.addEventListener('mouseenter', pause);
  node.addEventListener('mouseleave', () => { if (!node.contains(document.activeElement)) run(3000); });
  node.addEventListener('focusin', pause);
  node.addEventListener('focusout', e => { if (!node.contains(e.relatedTarget)) run(3000); });
  run(ms);
  currentToast = t;
  announce($('.notice__text', node)?.textContent || '');
  return t;
}

function toast(text, { kind = 'success', action = null, ms = 6000, returnFocus = null } = {}) {
  const node = el('div', `notice notice--${kind} toast`);
  Object.assign(node.dataset, { toast: '', kind });
  node.append(icon(kind === 'success' ? 'circle-check' : 'info', 'notice__icon'), el('p', 'notice__text', text));
  let button = null;
  if (action) {
    button = el('button', 'btn btn--ghost toast__action', action.label);
    button.type = 'button';
    node.append(button);
  }
  const close = el('button', 'icon-btn toast__close');
  close.type = 'button';
  close.dataset.toastClose = '';
  close.append(icon('x'), el('span', 'vh', COPY.dismiss));
  node.append(close);
  const t = floatToast(node, { ms, returnFocus });
  if (button && t) {
    button.addEventListener('click', () => { dismissToast(t, true); action.run(); });
    button.focus();
  }
  return t;
}

function initToasts() {
  if (!region) return;
  // Escape dismisses the current toast from anywhere (the menu's handler runs first and stops it when open).
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && currentToast) dismissToast(currentToast); });
  for (const node of $$('main [data-toast]')) floatToast(node);
}

// ---------------------------------------------------------------- submit guard and loading labels
function initForms() {
  document.addEventListener('submit', e => {
    const form = e.target;
    const button = e.submitter;
    if ('busy' in form.dataset || button?.getAttribute('aria-disabled') === 'true') {
      e.preventDefault();
      return;
    }
    form.dataset.busy = '';
    if (button?.dataset.loading) {
      button.style.width = `${button.getBoundingClientRect().width}px`;
      button.setAttribute('aria-disabled', 'true');
      button.dataset.busyLabel = '';
      button.tbLabel = [...button.childNodes];
      button.replaceChildren(icon('loader-circle', 'spin'), button.dataset.loading);
    }
  }, true);
  // Back/forward cache: a page restored after a submit must be usable again.
  addEventListener('pageshow', e => { if (e.persisted) releaseForms(); });
}

function releaseForms() {
  for (const form of $$('form[data-busy]')) delete form.dataset.busy;
  for (const button of $$('[data-busy-label]')) {
    if (button.tbLabel) button.replaceChildren(...button.tbLabel);
    button.style.width = '';
    button.removeAttribute('aria-disabled');
    delete button.dataset.busyLabel;
  }
}

// ---------------------------------------------------------------- phone numbers and the code field
function initTel() {
  document.addEventListener('focusout', e => {
    const input = e.target;
    if (!input.matches?.('.input--tel')) return;
    let digits = input.value.replace(/\D/g, '');
    if (digits.length === 11 && digits[0] === '1') digits = digits.slice(1);
    if (digits.length === 10) input.value = `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  });
}

function initOtp() {
  for (const box of $$('[data-otp]')) {
    const input = $('.otp__input', box);
    const clean = () => {
      const digits = input.value.replace(/\D/g, '').slice(0, 6);
      if (digits !== input.value) input.value = digits;
      box.dataset.filled = String(digits.length);
    };
    input.addEventListener('paste', e => {
      const digits = (e.clipboardData?.getData('text') || '').replace(/\D/g, '');
      e.preventDefault();
      input.setRangeText(digits, input.selectionStart ?? input.value.length, input.selectionEnd ?? input.value.length, 'end');
      clean();
    });
    input.addEventListener('input', clean);
    clean();
  }
}

// ---------------------------------------------------------------- the SMS engine (identical to the server)
const GSM = new Set([...(DATA.gsm || ''), ...(DATA.ext || '')]);
const EXT = new Set([...(DATA.ext || '')]);
const STOP = /\bstop\b/i;

// = client_portal.sms_parts: (characters, texts, plain GSM). Code points, like Python's len().
function parts(text) {
  const chars = [...text];
  if (chars.every(c => GSM.has(c))) {
    const units = chars.reduce((n, c) => n + (EXT.has(c) ? 2 : 1), 0);
    return [chars.length, units <= 160 ? 1 : Math.ceil(units / 153), true];
  }
  return [chars.length, chars.length <= 70 ? 1 : Math.ceil(chars.length / 67), false];
}

// = the bubble_text macro: URLs in span.sms__link, the opt-out line added for the owner in span.sms__suffix.
function drawBubble(node, body, tail) {
  const kids = body.split(/(https?:\/\/\S+)/).map((part, i) => (i % 2 ? el('span', 'sms__link', part) : part)).filter(k => k !== '');
  if (tail) kids.push(' ', el('span', 'sms__suffix', tail));
  node.replaceChildren(...kids);
}

// = client_portal.fill: str.format_map with unknown names kept; anything Python would refuse leaves the text as typed.
function fill(t, values = DATA.sample || {}) {
  let out = '';
  for (let i = 0; i < t.length;) {
    const c = t[i];
    if ((c === '{' || c === '}') && t[i + 1] === c) { out += c; i += 2; continue; }
    if (c === '}') return t;
    if (c !== '{') { out += c; i += 1; continue; }
    const end = t.indexOf('}', i);
    const name = end < 0 ? '' : t.slice(i + 1, end);
    if (!/^[A-Za-z_]\w*$/.test(name)) return t;
    out += Object.hasOwn(values, name) ? values[name] : `{${name}}`;
    i = end + 1;
  }
  return out;
}

// ---------------------------------------------------------------- message cards
const area = card => $('textarea', card);
// The template in force: what is typed, or the standard wording when the field is empty.
const tpl = card => area(card).value.trim() || card.dataset.default;
const textDirty = card => (norm(area(card).value) || norm(card.dataset.default)) !== norm(card.dataset.saved);
const switchDirty = sw => sw.checked !== (sw.dataset.savedChecked === '1');

function initCards(form, bar) {
  const cards = $$('article.msg', form);
  const byKey = Object.fromEntries(cards.map(card => [card.dataset.card, card]));
  const suffix = byKey.opt_out_suffix;

  // = client_portal.preview_parts: [wording, opt-out line added for the owner or '']
  const preview = card => {
    const t = tpl(card);
    return [norm(fill(t)), card.dataset.optout === '1' && suffix && !STOP.test(t) ? norm(fill(tpl(suffix))) : ''];
  };

  // The footer follows the textarea: "Standard wording" while it holds the standard text, else Reset.
  // (The Customized pill follows the saved file, so it only changes after a save.)
  function setAside(card) {
    const value = norm(area(card).value);
    const custom = value !== '' && value !== norm(card.dataset.default);
    $('[data-reset]', card).hidden = !custom;
    $('[data-std]', card).hidden = custom;
  }

  function setDirty(card) {
    const sw = $('.switch', card);
    const dirty = textDirty(card) || (sw ? switchDirty(sw) : false);
    card.toggleAttribute('data-dirty', dirty);
    $('[data-dirty-pill]', card).hidden = !dirty;
  }

  // The bubbles (card and rail) and the receipt: texts, characters, pips and the billing line from 2 texts.
  function render(card) {
    const [body, tail] = preview(card);
    const text = tail ? `${body} ${tail}`.trim() : body;
    for (const bubble of $$(`[data-preview="${card.dataset.card}"]`)) drawBubble(bubble, body, tail);
    const [n, k, gsm] = parts(text);
    $('[data-count]', card).textContent = COPY.count(n, k);
    $('[data-pips]', card).replaceChildren(...(k > 1 ? Array.from({ length: Math.min(k, 5) }, () => el('i')) : []),
      ...(k > 5 ? [el('b', '', '+')] : []));
    const bill = $('[data-bill]', card);
    bill.hidden = k < 2;
    bill.lastElementChild.textContent = k < 2 ? '' : COPY.bill(k, gsm ? '' : [...text].find(c => !GSM.has(c)));
    $('[data-receipt]', card).toggleAttribute('data-warn', k > 1);
    const note = $('[data-optout-note]', card);
    if (note) note.hidden = !tail;
    setAside(card);
    setDirty(card);
    const ta = area(card);
    const limit = $('[data-limit]', card);
    const length = ta.value.length;
    limit.hidden = length < 420;
    limit.toggleAttribute('data-warn', length >= 460);
    limit.textContent = COPY.limit(length, ta.maxLength);
    grow(ta);
  }

  function renderWithDependants(card) {
    render(card);
    if (card === suffix) for (const other of cards) if (other.dataset.optout === '1') render(other);
  }

  for (const chips of $$('[data-chips]', form)) chips.hidden = false;

  form.addEventListener('input', e => {
    if (e.target.tagName !== 'TEXTAREA') return;
    renderWithDependants(e.target.closest('article.msg'));
    bar.update(e.target);
  });
  form.addEventListener('change', e => {
    if (!e.target.matches('.switch')) return;
    setDirty(e.target.closest('article.msg'));
    bar.update(e.target);
  });

  form.addEventListener('click', e => {
    const reset = e.target.closest('[data-reset]');
    if (reset) {
      e.preventDefault();  // local and undoable through Discard; without JS it posts reset=<key>
      const card = reset.closest('article.msg');
      const ta = area(card);
      ta.value = card.dataset.default;
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      announce(COPY.restored($('.msg__label', card).textContent));
      const details = ta.closest('details');
      if (details.open) focusField(ta);
      else $('summary', details).focus();
      return;
    }
    const chip = e.target.closest('[data-insert]');
    if (chip) {
      const ta = area(chip.closest('article.msg'));
      ta.focus();
      if (!document.execCommand('insertText', false, chip.dataset.insert)) {
        ta.setRangeText(chip.dataset.insert, ta.selectionStart, ta.selectionEnd, 'end');
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
      return;
    }
    const summary = e.target.closest('.editor__summary');
    if (summary) {
      const details = summary.parentElement;
      requestAnimationFrame(() => { if (details.open) focusField(area(details)); });
      return;
    }
    // Tapping the preview opens that card's editor (unless the owner was selecting text in it).
    const band = e.target.closest('[data-band]');
    if (band && getSelection().isCollapsed) focusField(area(band.closest('article.msg')));
  });
  // Keep the caret in the textarea when a chip is clicked with a mouse.
  form.addEventListener('mousedown', e => { if (e.target.closest('[data-insert]')) e.preventDefault(); });
  // Texts are one paragraph: Enter does not add a line.
  form.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.tagName === 'TEXTAREA' && !e.isComposing) e.preventDefault();
  });

  // Fields the browser restored (back button, reload) need their previews redrawn.
  for (const card of cards) if (area(card).value !== area(card).defaultValue) renderWithDependants(card);
  for (const sw of $$('.switch', form)) if (sw.checked !== sw.defaultChecked) setDirty(sw.closest('article.msg'));
  return { cards, renderAll: () => cards.forEach(render), setDirty };
}

// ---------------------------------------------------------------- the save bar
function initSavebar(form) {
  const bar = $('[data-savebar]', form);
  const status = $('[data-savebar-status]', bar);
  const save = $('[data-save]', bar);
  const discard = $('[data-discard]', bar);
  const show = $('[data-show-error]', bar);
  const cards = $$('article.msg', form);
  const switches = $$('.switch', form);
  let state = bar.dataset.initial || 'clean';
  let errorField = $('.msg--invalid textarea', form);
  let count = 0;
  let lastLong = '';
  let api = null;

  const recount = () => cards.filter(textDirty).length + switches.filter(switchDirty).length;

  function paint(announceIt) {
    bar.dataset.state = state;
    const idle = state === 'clean' || state === 'saved';
    save.setAttribute('aria-disabled', String(idle || state === 'saving'));
    discard.hidden = state !== 'dirty';
    show.hidden = state !== 'error';
    const [ic, short, long] = {
      clean: ['circle-check', COPY.clean, COPY.clean],
      saved: ['circle-check', COPY.saved, COPY.saved],
      dirty: ['', COPY.unsavedShort(count), COPY.unsavedLong(count)],
      error: ['circle-alert', COPY.notSaved, COPY.notSavedLong(count)],
      saving: ['loader-circle', COPY.saving, COPY.saving],
    }[state];
    const shortSpan = el('span', 'savebar__short', short);
    shortSpan.setAttribute('aria-hidden', 'true');  // the long label stays readable to assistive tech
    status.replaceChildren(...(ic ? [icon(ic, state === 'saving' ? 'spin' : '')] : []), shortSpan, el('span', 'savebar__long', long));
    if (announceIt && long !== lastLong) announce(long, { debounce: 800, channel: 'savebar' });
    lastLong = long;
  }

  function update(changed) {
    if (state === 'saving') return;
    count = recount();
    if (state === 'error' && errorField && changed !== errorField) { paint(false); return; }
    errorField = null;
    state = count ? 'dirty' : (state === 'saved' ? 'saved' : 'clean');
    paint(true);
  }

  function clearErrors() {
    for (const card of $$('.msg--invalid', form)) card.classList.remove('msg--invalid');
    for (const field of $$('[aria-invalid="true"]', form)) {
      field.removeAttribute('aria-invalid');
      const ids = (field.getAttribute('aria-describedby') || '').split(' ').filter(id => !id.startsWith('e_'));
      field.setAttribute('aria-describedby', ids.join(' '));
    }
    for (const error of $$('.field-error[id^="e_"]', form)) error.remove();
    $('#error-summary')?.remove();
    errorField = null;
  }

  discard.addEventListener('click', () => {
    const snapshot = { texts: cards.map(c => area(c).value), checks: switches.map(s => s.checked) };
    cards.forEach(c => { area(c).value = c.dataset.saved; });
    switches.forEach(s => { s.checked = s.dataset.savedChecked === '1'; });
    api.renderAll();
    clearErrors();
    count = 0;
    state = 'clean';
    paint(false);  // the toast below does the announcing
    const undo = () => {
      cards.forEach((c, i) => { area(c).value = snapshot.texts[i]; });
      switches.forEach((s, i) => { s.checked = snapshot.checks[i]; });
      api.renderAll();
      update();
      save.focus();
    };
    toast(COPY.discarded, { ms: 8000, returnFocus: save, action: { label: COPY.undo, run: undo } });
  });

  show.addEventListener('click', () => {
    const target = errorField || $('#error-summary [data-error-link]');
    if (target?.tagName === 'TEXTAREA') focusField(target);
    else $('#error-summary')?.focus();
  });

  form.addEventListener('submit', e => {
    if (e.defaultPrevented) return;
    state = 'saving';
    paint(false);
  });

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === 's') {
      e.preventDefault();
      if (recount() > 0 && state !== 'saving') form.requestSubmit(save);
    }
  });

  addEventListener('beforeunload', e => {
    if (state === 'saving' || recount() === 0) return;
    e.preventDefault();
    e.returnValue = '';
    setTimeout(releaseForms);  // runs only if the owner chose to stay (e.g. after pressing Sign out)
  });
  addEventListener('pageshow', e => { if (e.persisted && state === 'saving') { state = 'clean'; update(); } });

  count = recount();
  if (state === 'clean' && count) state = 'dirty';
  paint(false);  // "Saved just now" stays until the next edit
  return { update, attach(cardsApi) { api = cardsApi; } };
}

// ---------------------------------------------------------------- error summary and links
function initErrorFocus() {
  const summary = $('#error-summary');
  if (summary) summary.focus({ preventScroll: false });
  document.addEventListener('click', e => {
    const link = e.target.closest?.('[data-error-link]');
    if (!link) return;
    const field = document.getElementById(link.getAttribute('href').slice(1));
    if (!field) return;
    e.preventDefault();
    focusField(field);
  });
}

// ---------------------------------------------------------------- the rail
function initRail(form) {
  const rail = $('[data-rail]');
  if (!rail) return;
  const log = $('[data-rail-log]', rail);
  const select = $('[data-scenario-select]', rail);
  let ringed = null;

  const activate = () => { rail.dataset.active = select.value; };
  const clear = () => { if (ringed) delete ringed.dataset.current; ringed = null; };
  activate();
  select.addEventListener('change', () => {
    activate();
    clear();
    log.scrollTop = 0;
  });

  if (!form) return;
  form.addEventListener('focusin', e => {
    if (!WIDE.matches) return;
    const card = e.target.closest('article.msg');
    if (!card) return;
    const sw = $('.switch', card);
    if (sw && !sw.checked) { clear(); return; }
    const key = card.dataset.sync;
    let thread = $(`.thread[data-scenario="${rail.dataset.active}"]`, rail);
    if (!$(`[data-preview="${key}"]`, thread)) {
      select.value = card.dataset.scenario;
      activate();
      thread = $(`.thread[data-scenario="${select.value}"]`, rail);
    }
    const bubble = $(`[data-preview="${key}"]`, thread);
    if (!bubble || bubble === ringed || !bubble.offsetParent) return;
    clear();
    bubble.dataset.current = '';
    ringed = bubble;
    // offsetTop is relative to the log (position: relative). Never scrollIntoView: it would move the page.
    const top = bubble.offsetTop - (log.clientHeight - bubble.offsetHeight) / 2;
    log.scrollTo({ top, behavior: REDUCED.matches ? 'auto' : 'smooth' });
  });
  form.addEventListener('focusout', e => {
    const card = e.target.closest('article.msg');
    if (card && !card.contains(e.relatedTarget)) clear();
  });
}

// ---------------------------------------------------------------- business name preview
function initNamePreview() {
  const bubble = $('[data-name-preview]');
  const input = $('#business_name');
  if (!bubble || !input) return;
  const { template, suffix, savedName } = bubble.dataset;
  input.addEventListener('input', () => {
    const name = input.value.trim() || savedName;
    bubble.textContent = norm(fill(template, { business_name: name }) + (suffix ? ` ${suffix}` : ''));
  });
}

// ---------------------------------------------------------------- calendar picker (enabled without JS)
function initPicker(form = $('[data-picker]'), save = form && $('[data-picker-save]', form)) {  // waits for a change
  const sync = () => { const on = $('input:checked', form); save.setAttribute('aria-disabled', String(!on || on.defaultChecked)); };
  if (save) { form.addEventListener('change', sync); sync(); }
}

// ---------------------------------------------------------------- styleguide demos (/client/styleguide only)
function initStyleguide() {
  for (const b of $$('[data-demo-toast]')) b.addEventListener('click', () => toast(b.dataset.demoToast, { returnFocus: b }));
  for (const b of $$('[data-demo-motion]')) b.addEventListener('click', () => {
    b.setAttribute('aria-pressed', String(document.getElementById(b.getAttribute('aria-controls')).toggleAttribute('data-run')));
  });
  if ($('[data-demo-toast]')) for (const chips of $$('[data-chips]')) chips.hidden = false;  // the card specimens' chips
}

// ---------------------------------------------------------------- start
for (const init of [initTheme, initMenu, initToasts, initForms, initTel, initOtp, initPicker, initStyleguide]) init();
const messagesForm = $('#messages');
if (messagesForm) {
  const bar = initSavebar(messagesForm);
  bar.attach(initCards(messagesForm, bar));
}
initRail(messagesForm);
initErrorFocus();
initNamePreview();
