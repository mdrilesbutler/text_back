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
  saving: 'Saving…', discarded: 'Changes discarded.', dismiss: 'Dismiss', unsaved: 'Unsaved changes',
  discard: 'Discard', save: 'Save', showChanged: 'Show what changed',
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
  document.addEventListener('keydown', e => {
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

// ---------------------------------------------------------------- notices (in flow, never floating)
// Every notice lives in the #notice slot between the header and the h1. The slot is role=status, so
// writing into it is announced; a notice never carries a role of its own and never times out.
const slot = $('#notice');

function dismissNotice(node) {
  const hadFocus = node.contains(document.activeElement);
  node.remove();
  if (hadFocus) $('#main')?.focus();
}

function wireNotice(node) {
  const close = $('[data-notice-dismiss]', node);
  if (!close) return;
  close.hidden = false;
  close.addEventListener('click', () => dismissNotice(node));
}

function notify(text, kind = 'success') {
  if (!slot) return;
  const node = el('div', `notice notice--${kind} toast`);
  node.dataset.notice = '';
  const body = el('div', 'notice__body');
  body.append(el('p', 'notice__text', text));
  const close = el('button', 'icon-btn toast__action');
  close.type = 'button';
  close.dataset.noticeDismiss = '';
  close.append(icon('x'), el('span', 'vh', COPY.dismiss));
  node.append(icon(kind === 'success' ? 'circle-check' : 'info', 'notice__icon'), body, close);
  slot.replaceChildren(node);
  wireNotice(node);
}

function initNotices() {
  for (const node of $$('[data-notice]', slot || document)) wireNotice(node);
}

// ---------------------------------------------------------------- jump chips (Messages)
// The chip of the step on screen is marked current and kept in view inside its scrolling row.
function initJump() {
  const list = $('.jump__list');
  if (!list || !('IntersectionObserver' in window)) return;
  const chips = {};
  for (const a of $$("a[href^='#']", list)) chips[a.getAttribute('href').slice(1)] = a;
  const steps = Object.keys(chips).map(id => document.getElementById(id)).filter(Boolean);
  const visible = {};
  const mark = () => {
    const current = steps.find(s => visible[s.id])?.id;
    if (!current) return;
    for (const [id, chip] of Object.entries(chips)) {
      if (id === current) chip.setAttribute('aria-current', 'location');
      else chip.removeAttribute('aria-current');
    }
    const chip = chips[current];
    const bar = list.parentElement;
    if (chip.offsetLeft < bar.scrollLeft || chip.offsetLeft + chip.offsetWidth > bar.scrollLeft + bar.clientWidth) {
      bar.scrollLeft = chip.offsetLeft - 16;
    }
  };
  const io = new IntersectionObserver(entries => {
    for (const e of entries) visible[e.target.id] = e.isIntersecting;
    mark();
  }, { rootMargin: '-120px 0px -55% 0px' });
  for (const s of steps) io.observe(s);
}

// ---------------------------------------------------------------- unsaved changes (one form at a time)
// A form marked data-track-changes compares every named control with what the page loaded. Its resting Save
// ([data-rest-save], aria-disabled so it still posts without JS) turns on while something differs and the line
// beside it says so. A form also marked data-topsave turns the header into its save bar below 1024 px: what
// changed (links to [data-change-label] holders), Discard and Save. Count words come from the form:
// data-changed-one ("1 rule changed") and data-changed-many ("{n} rules changed"); default "Unsaved changes".
// A header the server already drew (data-topsave-server, a no-JS round trip) is left alone; its Discard
// reloads the saved page.
const fieldValue = el => (el.type === 'checkbox' || el.type === 'radio' ? el.checked : el.value);

// A switch whose line underneath states its position (data-note-on / data-note-off) keeps that line true.
function initSwitchNotes() {
  for (const sw of $$('[data-note-on][data-note-off]')) {
    const note = document.getElementById(sw.getAttribute('aria-describedby'));
    if (note) sw.addEventListener('change', () => { note.textContent = sw.checked ? sw.dataset.noteOn : sw.dataset.noteOff; });
  }
}

function initChangeTracking() {
  const topbar = $('[data-topbar]');
  const server = $('[data-topsave-server]');
  if (server) {
    $('[data-topsave-discard]', server)?.addEventListener('click', e => { e.preventDefault(); location.assign(location.pathname); });
  }
  for (const form of $$('form[data-track-changes]')) {
    const controls = () => [...form.elements].filter(el => el.name && el.type !== 'hidden' && el.type !== 'submit'
      && el.type !== 'button' && el.name !== 'csrf');
    const baseline = new Map(controls().map(el => [el, fieldValue(el)]));
    const save = $(`[data-rest-save][form="${form.id}"]`) || $('[data-rest-save]', form);
    const status = save && $('[data-rest-status]', save.parentElement);
    const restText = status?.textContent || '';
    let submitting = false;
    let bar = null;

    const changes = () => {
      const groups = new Map();
      for (const el of controls()) {
        if (!baseline.has(el) || fieldValue(el) === baseline.get(el)) continue;
        const holder = el.closest('[data-change-label]');
        const key = holder || el.name;
        if (!groups.has(key)) groups.set(key, holder ? [holder.id ? `#${holder.id}` : '', holder.dataset.changeLabel] : null);
      }
      return [...groups.values()];
    };
    const countText = n => (n === 1 && form.dataset.changedOne) ? form.dataset.changedOne
      : (form.dataset.changedMany ? form.dataset.changedMany.replace('{n}', String(n)) : COPY.unsaved);

    function drawBar(list) {
      if (!bar) {
        bar = el('div', 'topsave');
        const details = el('details', 'topsave__changes');
        const summary = el('summary', 'topsave__summary');
        summary.append(el('span', 'topsave__count'), el('span', 'vh', `. ${COPY.showChanged}`), icon('chevron-down', 'topsave__chev'));
        details.append(summary, el('ul', 'topsave__list'));
        const actions = el('div', 'topsave__actions');
        const discard = el('button', 'btn btn--ghost', COPY.discard);
        discard.type = 'button';
        discard.addEventListener('click', () => {
          const moved = [...baseline.keys()].filter(field => fieldValue(field) !== baseline.get(field));
          form.reset();
          for (const field of moved) {
            const value = baseline.get(field);
            if (field.type === 'checkbox' || field.type === 'radio') field.checked = value; else field.value = value;
            field.dispatchEvent(new Event('change', { bubbles: true }));  // dependants (notes, previews) follow
          }
          update();
          notify(COPY.discarded);
          $('#main')?.focus();
        });
        const submit = el('button', 'btn btn--primary', form.dataset.saveLabel || save?.textContent.trim() || COPY.save);
        submit.type = 'submit';
        submit.setAttribute('form', form.id);
        actions.append(discard, submit);
        bar.append(details, actions);
        topbar.append(bar);
      }
      $('.topsave__count', bar).textContent = countText(list.length);
      $('.topsave__list', bar).replaceChildren(...list.filter(Boolean).map(([href, label]) => {
        const li = el('li');
        const a = el('a', '', label);
        a.href = href || '#main';
        a.addEventListener('click', () => { $('.topsave__changes', bar).open = false; });
        li.append(a);
        return li;
      }));
    }

    function update() {
      const list = changes();
      const dirty = list.length > 0;
      if (save) save.setAttribute('aria-disabled', String(!dirty));
      if (status) status.textContent = dirty ? COPY.unsaved : restText;
      if (topbar && !server && 'topsave' in form.dataset) {
        if (dirty) drawBar(list);
        topbar.classList.toggle('topbar--dirty', dirty);
        if (!dirty && bar) { bar.remove(); bar = null; }
      }
      form.toggleAttribute('data-dirty', dirty);
    }

    form.addEventListener('input', update);
    form.addEventListener('change', update);
    form.addEventListener('submit', () => { submitting = true; });
    if ('topsave' in form.dataset) {
      addEventListener('beforeunload', e => {
        if (submitting || !form.hasAttribute('data-dirty')) return;
        e.preventDefault();
        e.returnValue = '';
      });
    }
    update();
  }
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
// Inserts are shown as [Label] (never braces); DATA.labels maps each label to its placeholder name.
const LABELS = DATA.labels || { 'Business name': 'business_name' };
const tokens = t => t.replace(/\[([^\]]+)\]/g, (m, label) => (Object.hasOwn(LABELS, label) ? `{${LABELS[label]}}` : m));

function fill(t, values = DATA.sample || {}) {
  t = tokens(t);
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
    if (show) show.hidden = state !== 'error';  // C's Messages bar has no Show button
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
    cards.forEach(c => { area(c).value = c.dataset.saved; });
    switches.forEach(s => { s.checked = s.dataset.savedChecked === '1'; });
    api.renderAll();
    clearErrors();
    count = 0;
    state = 'clean';
    paint(false);  // the notice below does the announcing (the slot is role=status)
    notify(COPY.discarded);
    save.focus();  // Discard hides itself; focus stays on the bar
  });

  show?.addEventListener('click', () => {
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

// ---------------------------------------------------------------- start
for (const init of [initTheme, initMenu, initNotices, initJump, initSwitchNotes, initChangeTracking, initForms, initTel, initOtp, initPicker]) init();
const messagesForm = $('#messages');
if (messagesForm) {
  const bar = initSavebar(messagesForm);
  bar.attach(initCards(messagesForm, bar));
}
initRail(messagesForm);
initErrorFocus();
initNamePreview();
