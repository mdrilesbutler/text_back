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
  discarded: 'Changes discarded.', dismiss: 'Dismiss', unsaved: 'Unsaved changes',
  discard: 'Discard', save: 'Save', showChanged: 'Show what changed', textback: 'TextBack: ',
  restored: label => `Standard wording restored for ${label}.`,
  ruleReset: label => `${label} is back to its default. Save to keep it.`,
  // = portal_messages.count_label / bill_label / fix_label (deck cost_line, cost_bill_*)
  count: (n, k, notice) => `${plural(k, 'text')} · ${n} characters${notice ? ' with the notice' : ''}`,
  bill: (k, symbol, plain) => `Billed as ${k} texts. ` + (symbol
    ? `The \u201c${symbol}\u201d symbol makes each text hold only 70 characters. ${plain ? `Use \u201c${plain}\u201d instead.` : 'Use a plain letter instead.'}`
    : 'Customers still see one message.'),
  fix: (symbol, plain) => `Replace ${symbol} with ${plain}`,
  whereName: 'Your business name', whereStop: 'Your opt-out line',
  billWhere: (k, where, symbol) => `Billed as ${k} texts. ${where} has a ${symbol}, which makes each text hold only 70 characters.`,
  billLinks: k => `Billed as ${k} texts. The calendar links make this text long. Customers still see one message.`,  // = BILL_LINKS
  billOwn: (k, symbol) => `Billed as ${k} texts. The \u201c${symbol}\u201d symbol makes each text hold only 70 characters.`,
  // = portal_messages.changed_words: a question switch is a setting.
  settingOne: '1 setting changed', settingMany: n => `${n} settings changed`, mixed: n => `${n} changes`,
  copied: 'Copied', copyCode: 'Copy', copyFailed: 'Select the code and copy it',  // deck code_copy
  mobileSame: 'This is the number that signs you in.', mobileChanged: n => `Save to text a code to ${n}.`,  // deck owner_mobile_status
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

// = portal_messages.apply_fix: swap the symbol for the plain one; a dash with no space on a side gets one,
// so "call—this" becomes "call - this", never "call-this" (m2).
function plainSwap(text, symbol) {
  const plain = PLAIN[symbol];
  if (symbol !== '—' && symbol !== '–') return text.split(symbol).join(plain);
  return [...text].map((ch, i, all) => {
    if (ch !== symbol) return ch;
    const before = i ? all[i - 1] : ' ';
    const after = i + 1 < all.length ? all[i + 1] : ' ';
    return `${/\s/.test(before) ? '' : ' '}-${/\s/.test(after) ? '' : ' '}`;
  }).join('');
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
// The Dismiss button sits beside the slot, outside the live region (F7), so it is never read as part of a notice.
const slot = $('#notice');
const dismissButton = $('[data-notice-dismiss]');
const syncDismiss = () => { if (dismissButton) dismissButton.hidden = !(slot && $('[data-notice]', slot)); };

function notify(text, kind = 'success') {
  if (!slot) return;
  const node = el('div', `notice notice--${kind} toast`);
  node.dataset.notice = '';
  const body = el('div', 'notice__body');
  body.append(el('p', 'notice__text', text));
  node.append(icon(kind === 'success' ? 'circle-check' : 'info', 'notice__icon'), body);
  slot.replaceChildren(node);
  syncDismiss();
}

// Bring the notice slot into view (it sits under the header, above the h1), e.g. after Discard far down a page (m3).
function showNotice() {
  (slot?.parentElement || slot)?.scrollIntoView({ block: 'start', behavior: REDUCED.matches ? 'auto' : 'smooth' });
}

// A notice the server rendered is already in the live region when the page loads, so screen readers would
// not announce it: take it out and put it back on the next frame.
function initNotices() {
  dismissButton?.addEventListener('click', () => {
    slot?.replaceChildren();
    syncDismiss();
    $('#main')?.focus();
  });
  for (const node of $$('[data-notice]', slot || document)) {
    if (node.parentElement === slot) {
      node.remove();
      requestAnimationFrame(() => { slot.append(node); syncDismiss(); });
    }
  }
}

// ---------------------------------------------------------------- jump to a step (Messages)
// The step on screen is marked current in the chip row (from 640 px) and named in the phone "Jump to"
// control, whose summary then reads "Jump to: <step>"; picking a step closes it.
function initJump() {
  const chipList = $('.jump__list');
  const menu = $('[data-jumpmenu]');
  const label = menu && $('.jumpmenu__label', menu);
  const links = $$('.jump__link, .jumpmenu__link');
  const steps = [...new Set(links.map(a => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean))];
  menu?.addEventListener('click', e => { if (e.target.closest('.jumpmenu__link')) menu.open = false; });
  // Escape closes the open jump menu and gives focus back to its summary (F9).
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape' || !menu?.open) return;
    menu.open = false;
    $('summary', menu).focus();
  });
  // A jump moves focus to the step's heading (tabindex=-1), so the next Tab starts there (F5).
  for (const a of links) a.addEventListener('click', () => {
    const heading = $('h2', document.getElementById(a.getAttribute('href').slice(1)) || document.body);
    if (heading) requestAnimationFrame(() => heading.focus({ preventScroll: true }));
  });
  if (!steps.length) return;
  // The step on screen is the last one whose top has passed the line under the sticky chrome; at the very end of
  // the page, the last step. Measured on scroll (one frame at a time) and again when scrolling ends (m23).
  const topbar = $('[data-topbar]');
  const current = () => {
    const chrome = (topbar?.getBoundingClientRect().bottom || 0) + Math.max(
      ...[menu, chipList?.parentElement].filter(Boolean).map(x => (getComputedStyle(x).position === 'sticky' ? x.offsetHeight : 0)), 0);
    const line = chrome + 24;
    if (innerHeight + scrollY >= document.documentElement.scrollHeight - 2) {
      return [...steps].reverse().find(s => s.getBoundingClientRect().top < innerHeight) || steps[0];
    }
    return [...steps].reverse().find(s => s.getBoundingClientRect().top <= line) || steps[0];
  };
  let frame = 0;
  const mark = () => {
    frame = 0;
    const current_ = current();
    if (!current_) return;
    for (const a of links) {
      const on = a.getAttribute('href') === `#${current_.id}`;
      if (on) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
      if (on && label && a.classList.contains('jumpmenu__link')) label.textContent = `${label.dataset.lead} ${a.textContent}`;
      if (on && chipList && a.classList.contains('jump__link')) {
        const bar = chipList.parentElement;
        if (a.offsetLeft < bar.scrollLeft || a.offsetLeft + a.offsetWidth > bar.scrollLeft + bar.clientWidth) bar.scrollLeft = a.offsetLeft - 16;
      }
    }
  };
  addEventListener('scroll', () => { if (!frame) frame = requestAnimationFrame(mark); }, { passive: true });
  addEventListener('scrollend', mark);
  addEventListener('resize', () => { if (!frame) frame = requestAnimationFrame(mark); });
  mark();
}

// ---------------------------------------------------------------- unsaved changes (one form at a time)
// A form marked data-track-changes compares every named control with what the page loaded. Its resting Save
// ([data-rest-save], aria-disabled so it still posts without JS) turns on while something differs and the line
// beside it says so. A form also marked data-topsave turns the header into its save bar at every width: what
// changed (links to [data-change-label] holders), Discard and Save. Count words come from the form:
// data-changed-one ("1 rule changed") and data-changed-many ("{n} rules changed"); default "Unsaved changes".
// The form-end bar for the same form ([data-savebar][data-form=<id>]) follows too, always in flow: "No unsaved
// changes" at rest; the count, the changed items as links and Discard while something differs.
// A form the server answered with unsaved values (data-dirty-initial, a rejected save) keeps the server's
// header and bar; its Discard reloads the saved page.
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
  // A rejected save's Discard (desktop bar) also reloads the saved page.
  for (const form of $$('form[data-track-changes]')) {
    const initial = 'dirtyInitial' in form.dataset;
    const savebar = $(`[data-savebar][data-form="${form.id}"]`);
    const controls = () => [...form.elements].filter(el => el.name && el.type !== 'hidden' && el.type !== 'submit'
      && el.type !== 'button' && el.name !== 'csrf');
    const baseline = new Map(controls().map(el => [el, fieldValue(el)]));
    const save = $(`[data-rest-save][form="${form.id}"]`) || $('[data-rest-save]', form);
    const status = save && $('[data-rest-status]', save.parentElement);
    const restText = status?.textContent || '';
    let submitting = false;
    let bar = null;

    function discard() {
      if (initial) { location.assign(location.pathname); return; }
      const moved = [...baseline.keys()].filter(field => fieldValue(field) !== baseline.get(field));
      HTMLFormElement.prototype.reset.call(form);  // a control named "reset" (Reset buttons) shadows form.reset
      for (const field of moved) {
        const value = baseline.get(field);
        if (field.type === 'checkbox' || field.type === 'radio') field.checked = value; else field.value = value;
        // Dependants (switch notes, previews, counts) follow the restored value.
        field.dispatchEvent(new Event(field.tagName === 'TEXTAREA' ? 'input' : 'change', { bubbles: true }));
      }
      update();
      notify(COPY.discarded);
      $('#main')?.focus({ preventScroll: true });
      showNotice();  // the notice sits under the header: bring it into view wherever Discard was pressed (m3)
    }
    const discardButton = savebar && $('[data-savebar-discard]', savebar);
    discardButton?.addEventListener('click', e => { e.preventDefault(); discard(); });

    // A control marked data-change-kind=setting (a Messages question switch) counts as a setting of its own,
    // named by its own data-change-label; everything else groups under its [data-change-label] holder (m29).
    let settingCount = 0;
    const changes = () => {
      const groups = new Map();
      settingCount = 0;
      for (const el of controls()) {
        if (!baseline.has(el) || fieldValue(el) === baseline.get(el)) continue;
        if (el.dataset.changeKind === 'setting') {
          const card = el.closest('[id]');
          groups.set(el, [card ? `#${card.id}` : '', el.dataset.changeLabel]);
          settingCount += 1;
          continue;
        }
        const holder = el.closest('[data-change-label]');
        const key = holder || el.name;
        if (!groups.has(key)) groups.set(key, holder ? [holder.id ? `#${holder.id}` : '', holder.dataset.changeLabel] : null);
      }
      return [...groups.values()];
    };
    const countText = n => {
      const texts = n - settingCount;
      if (settingCount && texts) return COPY.mixed(n);
      if (settingCount) return settingCount === 1 ? COPY.settingOne : COPY.settingMany(settingCount);
      return (n === 1 && form.dataset.changedOne) ? form.dataset.changedOne
        : (form.dataset.changedMany ? form.dataset.changedMany.replace('{n}', String(n)) : COPY.unsaved);
    };

    function drawBar(list) {
      if (!bar) {
        bar = el('div', 'topsave');
        const details = el('details', 'topsave__changes');
        const summary = el('summary', 'topsave__summary');
        summary.append(el('span', 'topsave__count'), el('span', 'vh', `. ${COPY.showChanged}`), icon('chevron-down', 'topsave__chev'));
        details.append(summary, el('ul', 'topsave__list'));
        const actions = el('div', 'topsave__actions');
        const discardTop = el('button', 'btn btn--ghost', COPY.discard);
        discardTop.type = 'button';
        discardTop.addEventListener('click', discard);
        const submit = el('button', 'btn btn--primary', form.dataset.saveLabel || save?.textContent.trim() || COPY.save);
        submit.type = 'submit';
        submit.setAttribute('form', form.id);
        actions.append(discardTop, submit);
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

    function drawSavebar(list, dirty) {
      savebar.classList.toggle('savebar--on', dirty);
      savebar.dataset.state = dirty ? 'dirty' : 'clean';
      if (discardButton) discardButton.hidden = !dirty;
      // The status line is a live region: rewrite it only when its words change, so it speaks once per change.
      const drawn = dirty ? `${countText(list.length)}|${list.filter(Boolean).map(x => x.join('>')).join(',')}` : 'clean';
      if (savebar.dataset.drawn === drawn) return;
      savebar.dataset.drawn = drawn;
      const line = $('[data-savebar-status]', savebar);
      if (!dirty) { line.textContent = line.dataset.clean || restText; return; }
      const names = el('span', 'savebar__names', ': ');
      list.filter(Boolean).forEach(([href, label], i) => {
        const a = el('a', '', label);
        a.href = href || '#main';
        names.append(...(i ? [', '] : []), a);
      });
      line.replaceChildren(el('span', 'savebar__count', countText(list.length)), ...(names.childNodes.length > 1 ? [names] : []));
    }

    function update() {
      const list = changes();
      const dirty = initial || list.length > 0;
      if (save) save.setAttribute('aria-disabled', String(!dirty));
      if (status) status.textContent = dirty ? COPY.unsaved : restText;
      if (initial) { form.setAttribute('data-dirty', ''); return; }
      if (savebar) drawSavebar(list, dirty);
      if (topbar && !server && 'topsave' in form.dataset) {
        if (dirty) drawBar(list);
        topbar.classList.toggle('topbar--dirty', dirty);
        if (!dirty && bar) { bar.remove(); bar = null; }
      }
      form.toggleAttribute('data-dirty', dirty);
    }

    form.addEventListener('input', update);
    form.addEventListener('change', update);
    form.addEventListener('submit', e => { if (!e.defaultPrevented) submitting = true; });
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
const PLAIN = { '—': '-', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '…': '...' };
// = portal_messages.NOTICE_MODEL: the network notice's length (24 characters, two of them billed twice).
const NOTICE_MODEL = `[${'a'.repeat(21)}] `;

// = portal_messages.sms_parts: (characters, texts, plain GSM). Plain texts count code points (Python's len());
// UCS-2 texts count UTF-16 units, as the network does: text.length, so an emoji takes two.
function parts(text) {
  const chars = [...text];
  if (chars.every(c => GSM.has(c))) {
    const units = chars.reduce((n, c) => n + (EXT.has(c) ? 2 : 1), 0);
    return [chars.length, units <= 160 ? 1 : Math.ceil(units / 153), true];
  }
  const n = text.length;
  return [n, n <= 70 ? 1 : Math.ceil(n / 67), false];
}

// = portal_render.split_links: calendar links come out of the words and show as labels (never a raw link).
// Only TextBack's own links: the public base URL, /a/<rowid>-<12 hex>, then /g, /o, /i or nothing.
// The base comes from the sample's own calendar link (DATA.sample.google_link), so the page data carries no other URL.
const LINK_BASE = (DATA.sample?.google_link || '').replace(/\/a\/.*$/, '');
const BASE_RE = LINK_BASE.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
const CAL_LINK = new RegExp(`(?:\\b(?:Google|Outlook|iCal) )?(${BASE_RE}/a/\\d+-[0-9a-f]{12}(?:/([goi]))?)(?![\\w/-])`, 'g');
const LINK_LABELS = { g: 'Add to Google Calendar ›', o: 'Add to Outlook ›', i: 'Add to iCal ›', '': 'Calendar links page ›' };
function splitLinks(text) {
  if (!BASE_RE) return [text, []];
  const matches = [...text.matchAll(CAL_LINK)];
  if (!matches.length) return [text, []];
  const links = matches.map(m => [LINK_LABELS[m[2] || ''], m[1]]);
  const head = text.slice(0, matches[0].index).replace(/\bAdd to calendar:\s*$/i, '');
  const body = head + text.slice(matches[0].index).replace(CAL_LINK, ' ');
  return [norm(body).replace(/\s+([.,;!?])/g, '$1'), links];
}

// = the bubble macro: words (URLs in span.sms__link), the opt-out line in span.sms__suffix, links as labels.
function drawBubble(p, body, tail, links) {
  const kids = body.split(/(https?:\/\/\S+)/).map((part, i) => (i % 2 ? el('span', 'sms__link', part) : part)).filter(k => k !== '');
  if (tail) kids.push(' ', el('span', 'sms__suffix', tail));
  p.replaceChildren(...kids);
  const list = p.parentElement && $('.sms__links', p.parentElement);
  if (!list) return;
  list.replaceChildren(...links.map(([label, url]) => {
    const li = el('li');
    const span = el('span', 'sms__linkbtn', label);
    span.title = url;
    li.append(span);
    return li;
  }));
  list.hidden = !links.length;
}

// = portal_messages.fill: str.format_map with unknown names kept; anything Python would refuse leaves the text as typed.
// Inserts are shown as [Label] (never braces); DATA.labels maps each label to its placeholder name.
const LABELS = DATA.labels || { 'Business name': 'business_name' };
// Labels match whatever the case and spacing, like the server (portal_messages._LABEL_KEYS).
const labelKey = label => label.toLowerCase().split(/\s+/).filter(Boolean).join(' ');
const LABEL_KEYS = Object.fromEntries(Object.entries(LABELS).map(([label, name]) => [labelKey(label), name]));
const tokens = t => t.replace(/\[([^\]]+)\]/g, (m, label) => (Object.hasOwn(LABEL_KEYS, labelKey(label)) ? `{${LABEL_KEYS[labelKey(label)]}}` : m));

// The invite sentence follows the email question's switch, as the booking code does.
function sampleValues() {
  const email = $('#ask_email');
  const invite = email?.checked ? (DATA.invite || {}) : { invite_line: '', invited_email: '' };
  return { ...(DATA.sample || {}), ...(email ? invite : {}) };
}

function fill(t, values = sampleValues()) {
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

// ---------------------------------------------------------------- message cards (live previews)
// Each card follows its textarea: the bubble (here and in the example conversation), the cost line, the
// billing line and its one-tap fix, the STOP-line note, "Unsaved" and "Was: …", Reset vs Standard wording.
const area = card => $('textarea', card);
const tpl = card => area(card).value.trim() || card.dataset.default;
const textDirty = card => norm(area(card).value || card.dataset.default) !== norm(card.dataset.saved);

function initCards(form) {
  if (!form) return;
  const cards = $$('article[data-card]', form);
  if (!cards.length) return;
  const byKey = Object.fromEntries(cards.map(card => [card.dataset.card, card]));
  const suffix = byKey.opt_out_suffix;

  function render(card, typed = false) {
    const key = card.dataset.card;
    const t = tpl(card);
    const body = norm(fill(t));
    const tail = card.dataset.optout === '1' && suffix && !STOP.test(t) ? norm(fill(tpl(suffix))) : '';
    const [words, links] = splitLinks(body);
    for (const p of $$(`[data-preview="${key}"]`)) drawBubble(p, words, tail, links);
    const preview = tail ? `${body} ${tail}` : body;
    const notice = Boolean(DATA.notice) && key !== 'opt_out_suffix';
    const [n, k, plain] = parts(notice ? NOTICE_MODEL + preview : preview);
    for (const c of $$('[data-count]', card)) c.textContent = COPY.count(n, k, notice);
    // = portal_messages.bill_info: the fix only changes the card's own wording; a symbol from the business
    // name or the opt-out line is named where it is, with no button.
    const firstSymbol = text => [...text].find(ch => !GSM.has(ch)) || '';
    const own = plain ? '' : firstSymbol(t.replace(/\[[^\]]*\]/g, ''));
    const elsewhere = plain || own ? null : [[COPY.whereName, sampleValues().business_name || ''], [COPY.whereStop, tail]]
      .map(([where, text]) => [where, firstSymbol(text)]).find(([, sym]) => sym);
    const bill = $('[data-bill]', card);
    bill.hidden = k < 2;
    // = bill_info: the confirmation's length comes from its links, so it gets the honest note and never a fix (m32).
    const confirmation = key === 'booking_confirmation';
    $('[data-bill-text]', bill).textContent = k < 2 ? '' : confirmation ? (own ? COPY.billOwn(k, own) : COPY.billLinks(k))
      : (elsewhere ? COPY.billWhere(k, ...elsewhere)
        : COPY.bill(k, own || (plain ? '' : firstSymbol(preview)), PLAIN[own || firstSymbol(preview)]));
    const fix = $('[data-fix]', bill);
    if (fix) {
      fix.hidden = k < 2 || !PLAIN[own] || confirmation;
      $('[data-fix-label]', fix).textContent = PLAIN[own] ? COPY.fix(own, PLAIN[own]) : '';
      fix.dataset.symbol = PLAIN[own] ? own : '';
    }
    $('[data-link-note]', card).hidden = !links.length;
    const added = $('[data-optout-note]', card);
    if (added) added.hidden = !tail;
    const dirty = textDirty(card);
    $('[data-unsaved-pill]', card)?.toggleAttribute('hidden', !dirty);
    $('[data-custom-pill]', card)?.toggleAttribute('hidden', dirty);
    $('[data-was]', card).hidden = !dirty;
    const value = norm(area(card).value);
    const custom = value !== '' && value !== norm(card.dataset.default);
    $('[data-reset]', card).hidden = !custom;
    $('[data-std]', card).hidden = custom;
    const ta = area(card);
    const limit = $('[data-limit]', card);
    limit.hidden = ta.value.length < 420;
    $('[data-limit-n]', limit).textContent = String(ta.value.length);
    grow(ta);
    // Screen readers hear the cost only when the number of texts changes, a second after typing stops (F3).
    if (typed && card.dataset.texts && card.dataset.texts !== String(k)) announce(COPY.count(n, k, notice), { channel: 'count', debounce: 1000 });
    card.dataset.texts = String(k);
  }
  const renderWithDependants = (card, typed = false) => {
    render(card, typed);
    if (card === suffix) for (const other of cards) if (other.dataset.optout === '1') render(other);
  };

  for (const chips of $$('[data-chips]', form)) chips.hidden = false;
  // Each card's number of texts as the server drew it, so the first keystroke is compared with something (F3).
  for (const card of cards) card.dataset.texts = String(parseInt($('[data-count]', card)?.textContent || '', 10) || '');
  form.addEventListener('input', e => {
    if (e.target.tagName === 'TEXTAREA') renderWithDependants(e.target.closest('article[data-card]'), true);
  });
  form.addEventListener('change', e => {
    const sw = e.target.closest('.switch');
    if (!sw) return;
    const card = sw.closest('article[data-card]');
    card.classList.toggle('qset--off', !sw.checked);
    $('.msg', card).classList.toggle('msg--isoff', !sw.checked);
    if (sw.id === 'ask_email' && byKey.booking_confirmation) render(byKey.booking_confirmation);
  });
  form.addEventListener('click', e => {
    // "Replace — with -": local like Reset (undoable through Discard); without JS it posts fix=<key> and saves.
    const fix = e.target.closest('[data-fix]');
    if (fix) {
      e.preventDefault();
      const card = fix.closest('article[data-card]');
      const ta = area(card);
      const symbol = fix.dataset.symbol;
      if (!symbol || !PLAIN[symbol]) return;
      ta.value = plainSwap(ta.value || card.dataset.default, symbol);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      const details = ta.closest('details');
      if (details && !details.open) details.open = true;
      focusField(ta);
      return;
    }
    const reset = e.target.closest('[data-reset]');
    if (reset) {
      e.preventDefault();  // local and undoable through Discard; without JS it posts reset=<key> (Reset and save)
      const card = reset.closest('article[data-card]');
      const ta = area(card);
      ta.value = card.dataset.default;
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      announce(COPY.restored($('.msg__label', card).textContent));
      const details = ta.closest('details');
      if (details.open) focusField(ta); else $('summary', details).focus();
      return;
    }
    const chip = e.target.closest('[data-insert]');
    if (chip) {
      const ta = area(chip.closest('article[data-card]'));
      ta.focus();
      // A space goes in where the insert would touch a word, so "[Business name]What" can't happen (m1).
      const before = ta.value.slice(0, ta.selectionStart).slice(-1);
      const after = ta.value.slice(ta.selectionEnd, ta.selectionEnd + 1);
      const text = (before && !/[\s(\[“"']/.test(before) ? ' ' : '') + chip.dataset.insert
        + (after && !/[\s.,!?;:)\]”"']/.test(after) ? ' ' : '');
      if (!document.execCommand('insertText', false, text)) {
        ta.setRangeText(text, ta.selectionStart, ta.selectionEnd, 'end');
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
    // Tapping the preview opens that card's editor (unless the owner was selecting text or tapped a control).
    const band = e.target.closest('[data-band]');
    if (band && !e.target.closest('button, a') && getSelection().isCollapsed) focusField(area(band.closest('article[data-card]')));
  });
  // Keep the caret in the textarea when a chip is clicked with a mouse.
  form.addEventListener('mousedown', e => { if (e.target.closest('[data-insert]')) e.preventDefault(); });
  // Texts are one paragraph: Enter does not add a line.
  form.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.tagName === 'TEXTAREA' && !e.isComposing) e.preventDefault();
  });
  // Fields the browser restored (back button, reload) need their previews redrawn.
  for (const card of cards) if (area(card).value !== area(card).defaultValue) renderWithDependants(card);
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

// ---------------------------------------------------------------- the example conversation
// The select switches the thread drawn (data-active). On desktop, editing a card brings its bubble into
// view inside the rail's own scroll (never the page) and rings it.
function initRail(form) {
  const rail = $('[data-rail]');
  if (!rail) return;
  const log = $('[data-rail-log]', rail);
  const select = $('[data-scenario-select]', rail);
  let ringed = null;
  const activate = () => { rail.dataset.active = select.value; };
  const clear = () => { if (ringed) delete ringed.dataset.current; ringed = null; };
  // "Scroll for the rest" (CSS shows it while the log carries data-more): more than the 16px of padding that
  // clears the 32px fade is still below. Never set when the log does not scroll (phones, the in-flow rail).
  const more = () => {
    const scrolls = getComputedStyle(log).overflowY !== 'visible';
    log.toggleAttribute('data-more', scrolls && log.scrollHeight - log.clientHeight - log.scrollTop > 16);
  };
  activate();
  select.addEventListener('change', () => { activate(); clear(); log.scrollTop = 0; more(); });
  log.addEventListener('scroll', more, { passive: true });
  if ('ResizeObserver' in window) {
    const seen = new ResizeObserver(more);
    seen.observe(log);
    for (const thread of $$('.thread', log)) seen.observe(thread);
  }
  more();
  if (!form) return;
  form.addEventListener('focusin', e => {
    if (!WIDE.matches) return;
    const card = e.target.closest('article[data-card]');
    if (!card) return;
    const key = card.dataset.card;
    let p = $(`.thread[data-scenario="${rail.dataset.active}"] [data-preview="${key}"]`, rail);
    if (!p) {
      p = $(`[data-preview="${key}"]`, log);
      if (!p) { clear(); return; }
      select.value = p.closest('.thread').dataset.scenario;
      activate();
    }
    const bubble = p.closest('.sms__bubble');
    if (bubble === ringed || !bubble.offsetParent) return;
    clear();
    bubble.dataset.current = '';
    ringed = bubble;
    const top = bubble.offsetTop - (log.clientHeight - bubble.offsetHeight) / 2;
    log.scrollTo({ top, behavior: REDUCED.matches ? 'auto' : 'smooth' });
  });
  form.addEventListener('focusout', e => {
    const card = e.target.closest('article[data-card]');
    if (card && !card.contains(e.relatedTarget)) clear();
  });
}

// ---------------------------------------------------------------- Schedule: length chips and the one-tap hours
// The number field and the chips follow each other (a chip sets the number; a typed number checks its chip
// or Custom). "Use Mon–Fri, 8 AM–5 PM" fills the grid here instead of posting; it still needs Save.
function initSchedule() {
  const number = $('[data-duration-number]');
  if (number) {
    const chips = $$('[data-duration-chip]');
    // The chip follows the typed value at once (CSS keeps the field shown while it has focus, so it never
    // hides under the cursor at "60").
    number.addEventListener('input', () => {
      const match = chips.find(c => c.value === number.value.trim());
      (match || chips.find(c => c.value === 'custom')).checked = true;
    });
    // CSS shows the minutes field only while Custom is chosen: choosing it reveals the field and moves focus in.
    for (const chip of chips) chip.addEventListener('change', () => {
      if (chip.checked && chip.value !== 'custom') {
        number.value = chip.value;
        number.dispatchEvent(new Event('change', { bubbles: true }));
      } else if (chip.checked) {
        number.focus();
        number.select();
      }
    });
  }
  const suggest = $('[data-suggest-hours]');
  if (!suggest) return;
  suggest.addEventListener('click', e => {
    e.preventDefault();
    const set = $('[name="hours_mode"][value="set"]');
    set.checked = true;
    set.dispatchEvent(new Event('change', { bubbles: true }));
    for (const row of $$('.hrow[data-day]')) {
      const day = row.dataset.day;
      const weekday = !['sat', 'sun'].includes(day);
      const sw = $('.switch', row);
      sw.checked = weekday;
      sw.dispatchEvent(new Event('change', { bubbles: true }));
      if (!weekday) continue;
      const [open, close] = [$(`[name="${day}_open"]`, row), $(`[name="${day}_close"]`, row)];
      open.value = '08:00'; close.value = '17:00';
      open.dispatchEvent(new Event('change', { bubbles: true }));
      close.dispatchEvent(new Event('change', { bubbles: true }));
    }
    $('#working-hours h2')?.focus();
  });
}

// ---------------------------------------------------------------- Schedule: Reset stays local until Save (m11)
// Each Reset carries the control values it puts back (data-reset-values). With JavaScript it sets them in place,
// like Messages, and the change waits for Save (Discard undoes it); a rule already at its default hides its Reset.
function initScheduleReset() {
  const form = $('#schedule-form');
  if (!form) return;
  const buttons = $$('[data-reset-values]', form);
  const targets = new Map(buttons.map(b => { try { return [b, JSON.parse(b.dataset.resetValues)]; } catch { return [b, null]; } }));
  const controlsFor = name => [...form.elements].filter(c => c.name === name);
  const matches = (name, want) => controlsFor(name).every(c => {
    if (c.type === 'radio') return c.checked === (c.value === String(want));
    if (c.type === 'checkbox') return c.checked === Boolean(want);
    return c.value === String(want);
  });
  const sync = () => {
    for (const [button, values] of targets) if (values) button.hidden = Object.entries(values).every(([name, want]) => matches(name, want));
  };
  form.addEventListener('click', e => {
    const button = e.target.closest('[data-reset-values]');
    const values = button && targets.get(button);
    if (!values) return;
    e.preventDefault();
    for (const [name, want] of Object.entries(values)) {
      for (const c of controlsFor(name)) {
        if (c.type === 'radio') c.checked = c.value === String(want);
        else if (c.type === 'checkbox') c.checked = Boolean(want);
        else c.value = String(want);
        c.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    sync();
    announce(COPY.ruleReset($('.vh', button)?.textContent.trim() || ''));
    const field = button.closest('.field, .card')?.querySelector('input:not([type=hidden]), select');
    field?.focus({ preventScroll: true });
  });
  form.addEventListener('input', sync);
  form.addEventListener('change', sync);
  sync();
}

// ---------------------------------------------------------------- business name preview
function initNamePreview() {
  const bubble = $('[data-name-preview]');
  const input = $('#business_name');
  if (!bubble || !input) return;
  const { template, suffix, savedName } = bubble.dataset;
  const who = $('[data-name-who]');
  input.addEventListener('input', () => {
    const name = input.value.trim() || savedName;
    drawBubble(bubble, norm(fill(template, { business_name: name })), suffix || '', []);
    if (who) who.textContent = name;
  });
}

// ---------------------------------------------------------------- Phone: copy a code, the mobile status line
const COPIED_MS = 2000;
// Copy works on plain http and older browsers too (M3): the async clipboard when it is there, otherwise the code
// text is selected and copied with execCommand; if both fail the code stays selected and the label says so.
async function copyText(text, node) {
  try {
    if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; }
  } catch { /* fall through */ }
  const range = document.createRange();
  range.selectNodeContents(node);
  const selection = getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { ok = false; }
  if (ok) selection.removeAllRanges();
  return ok;
}

function initPhone() {
  for (const button of $$('[data-copy]')) {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const code = button.closest('.code')?.querySelector('.code__val') || button;
      const ok = await copyText(button.dataset.copy, code);
      const label = $('[data-copy-label]', button);
      label.textContent = ok ? COPY.copied : COPY.copyFailed;
      announce(ok ? COPY.copied : COPY.copyFailed);
      setTimeout(() => { label.textContent = COPY.copyCode; }, COPIED_MS);
    });
  }
  // The business name's billing line follows the name as it is typed (M7).
  const nameInput = $('#business_name');
  const nameLine = $('[data-name-symbol]');
  if (nameInput && nameLine) {
    nameInput.addEventListener('input', () => {
      const symbol = [...nameInput.value].find(ch => !GSM.has(ch)) || '';
      nameLine.hidden = !symbol;
      $('[data-name-symbol-text]', nameLine).textContent = symbol ? nameLine.dataset.template.replace('{symbol}', symbol) : '';
    });
  }
  const mobile = $('#owner_mobile');
  const status = $('[data-mobile-status]');
  if (!mobile || !status) return;
  const fmt = v => {
    let d = v.replace(/\D/g, '');
    if (d.length === 11 && d[0] === '1') d = d.slice(1);
    return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : '';
  };
  mobile.addEventListener('input', () => {
    const now = fmt(mobile.value);
    status.textContent = !now || now === mobile.dataset.savedMobile ? COPY.mobileSame : COPY.mobileChanged(now);
  });
}

// ---------------------------------------------------------------- Account: the sign-out-everywhere confirm (m6)
// Opening it brings the question and its button fully into view, clear of the bottom bar (scroll-margin in CSS).
function initConfirmInline() {
  for (const details of $$('details.confirm-inline')) {
    details.addEventListener('toggle', () => {
      // Next frame: the page's extra bottom room for the open question (CSS :has) is laid out by then.
      if (details.open) requestAnimationFrame(() => $('.confirm-inline__panel', details)?.scrollIntoView({ block: 'nearest', behavior: REDUCED.matches ? 'auto' : 'smooth' }));
    });
  }
}

// ---------------------------------------------------------------- on-screen keyboard (m25)
// While a text field has focus and the visual viewport is short (the keyboard is up), the bottom bar hides so the
// field and the header save bar keep the room.
function initKeyboard() {
  const vv = window.visualViewport;
  if (!vv) return;
  const typing = () => document.activeElement?.matches?.('input:not([type=checkbox]):not([type=radio]):not([type=submit]), textarea, select');
  const sync = () => root.classList.toggle('kb-open', vv.height < 500 && Boolean(typing()));
  vv.addEventListener('resize', sync);
  document.addEventListener('focusin', sync);
  document.addEventListener('focusout', () => requestAnimationFrame(sync));
}

// ---------------------------------------------------------------- header height (F2)
// At large text sizes the header wraps to two lines; the sticky jump control and scroll-padding read
// --header-h, so it follows the header's real height (the menu open on a phone adds its panel, as before).
function initHeaderHeight() {
  const bar = $('[data-topbar]');
  if (!bar || !('ResizeObserver' in window)) return;
  new ResizeObserver(() => {
    if (bar.querySelector('.menu[open]')) return;  // the open menu pushes the page; the chrome under it stays put
    root.style.setProperty('--header-h', `${bar.getBoundingClientRect().height}px`);
  }).observe(bar);
}

// ---------------------------------------------------------------- Calendar: land on the free times (F6)
function initAvailability() {
  if (location.hash !== '#availability') return;
  const heading = $('#avail-title');
  if (heading) requestAnimationFrame(() => heading.focus({ preventScroll: false }));
}

// ---------------------------------------------------------------- calendar picker (enabled without JS)
function initPicker(form = $('[data-picker]'), save = form && $('[data-picker-save]', form)) {  // waits for a change
  const sync = () => { const on = $('input:checked', form); save.setAttribute('aria-disabled', String(!on || on.defaultChecked)); };
  if (save) { form.addEventListener('change', sync); sync(); }
}

// ---------------------------------------------------------------- start
const messagesForm = $('#messages-form');
initCards(messagesForm);  // before the tracker, so a restored draft is drawn before it is counted
for (const init of [initTheme, initMenu, initNotices, initJump, initSwitchNotes, initSchedule, initScheduleReset, initChangeTracking,
  initForms, initTel, initOtp, initPicker, initConfirmInline, initKeyboard, initAvailability, initHeaderHeight]) init();
initRail(messagesForm);
initErrorFocus();
initNamePreview();
initPhone();
