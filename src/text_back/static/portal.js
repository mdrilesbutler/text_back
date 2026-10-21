/* text_back owner portal — shared behaviour. Plain ES2017, loaded with defer,
   no inline handlers (CSP script-src 'self'). Page scripts append below the
   marker at the end of this file and use window.portal.

   API
   portal.toast(msg, kind)        kind: ok | err | info  (aria-live region #toasts)
   portal.formatPhone(digits)     "7045550123" -> "(704) 555-0123"
   portal.toE164(text)            "(704) 555-0123" -> "+17045550123" or ""
   portal.count(textarea)         re-run the counter for one textarea
   window.portalSegments(text)    optional hook a page may define: returns
                                  {chars, segments, note} for the counter

   data-attributes
   [data-copy="text"]             copies text to the clipboard, toasts "Copied"
   [data-phone]                   formats as you type; writes E.164 to the
                                  nearest sibling [data-phone-e164] if present
   [data-counter]                 textarea; updates #<id>-count
   [data-drawer="rowid"]          toggles the <tr id=rowid> drawer
   [role=tablist] > [role=tab]    arrow-key tabs; data-target names the panel
   [data-insert="{token}"]        inserts token at the caret of the textarea
                                  named by data-for
   details.menu                   closes on outside click or Escape
*/
(function () {
  'use strict';
  var portal = {};

  /* Toasts */
  var toastsEl = null;
  portal.toast = function (msg, kind) {
    toastsEl = toastsEl || document.getElementById('toasts');
    if (!toastsEl) return;
    var t = document.createElement('div');
    t.className = 'toast ' + (kind || 'info');
    var icon = kind === 'ok' ? 'check' : kind === 'err' ? 'alert' : 'info';
    t.innerHTML = '<svg class="i" aria-hidden="true"><use href="#i-' + icon + '"></use></svg>';
    t.appendChild(document.createTextNode(msg));
    toastsEl.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 2500);
  };

  /* Clipboard */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-copy]');
    if (!b) return;
    var text = b.getAttribute('data-copy');
    var done = function () { portal.toast('Copied', 'ok'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { portal.toast('Copy failed', 'err'); });
    } else {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (err) { portal.toast('Copy failed', 'err'); }
      document.body.removeChild(ta);
    }
  });

  /* Phone formatting */
  portal.formatPhone = function (digits) {
    digits = String(digits || '').replace(/\D/g, '');
    if (digits.length === 11 && digits.charAt(0) === '1') digits = digits.slice(1);
    digits = digits.slice(0, 10);
    if (digits.length < 4) return digits;
    if (digits.length < 7) return '(' + digits.slice(0, 3) + ') ' + digits.slice(3);
    return '(' + digits.slice(0, 3) + ') ' + digits.slice(3, 6) + '-' + digits.slice(6);
  };
  portal.toE164 = function (text) {
    var digits = String(text || '').replace(/\D/g, '');
    if (digits.length === 11 && digits.charAt(0) === '1') digits = digits.slice(1);
    return digits.length === 10 ? '+1' + digits : '';
  };
  function wirePhone(input) {
    var hidden = input.parentNode ? input.parentNode.querySelector('[data-phone-e164]') : null;
    function apply() {
      var raw = input.value;
      if (raw.replace(/\D/g, '').length === 0) { input.value = raw.trim() === '+' ? '+' : ''; }
      else if (/^\+(?!1)/.test(raw.trim())) { /* non-US: leave as typed */ }
      else { input.value = portal.formatPhone(raw); }
      if (hidden) hidden.value = portal.toE164(input.value) || (input.value.trim().charAt(0) === '+' ? input.value.replace(/[^\d+]/g, '') : '');
    }
    input.addEventListener('input', apply);
    input.addEventListener('blur', apply);
    if (input.value) apply();
  }

  /* Textarea counter */
  portal.count = function (ta) {
    var out = document.getElementById(ta.id + '-count');
    if (!out) return;
    var text = ta.value || ta.placeholder || '';
    var r = (typeof window.portalSegments === 'function') ? window.portalSegments(text, ta) : null;
    if (!r) {
      var n = text.length;
      r = { chars: n, segments: n <= 160 ? 1 : Math.ceil(n / 153), note: '' };
    }
    out.textContent = r.chars + ' characters · ' + r.segments + (r.segments === 1 ? ' text' : ' texts') + (r.note ? ' · ' + r.note : '');
    out.classList.toggle('over', r.segments > 2);
  };
  function wireCounter(ta) {
    ta.addEventListener('input', function () { portal.count(ta); });
    portal.count(ta);
  }

  /* Placeholder chips */
  document.addEventListener('click', function (e) {
    var chip = e.target.closest('[data-insert]');
    if (!chip) return;
    var ta = document.getElementById(chip.getAttribute('data-for'));
    if (!ta) return;
    var token = chip.getAttribute('data-insert');
    var s = ta.selectionStart == null ? ta.value.length : ta.selectionStart, en = ta.selectionEnd == null ? s : ta.selectionEnd;
    ta.value = ta.value.slice(0, s) + token + ta.value.slice(en);
    ta.selectionStart = ta.selectionEnd = s + token.length;
    ta.focus();
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  });

  /* Drawers */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-drawer]');
    if (!b) return;
    var row = document.getElementById(b.getAttribute('data-drawer'));
    if (!row) return;
    var open = row.hasAttribute('hidden');
    if (open) row.removeAttribute('hidden'); else row.setAttribute('hidden', '');
    b.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  /* Tabs / segmented control */
  function selectTab(tab, focus) {
    var list = tab.closest('[role="tablist"]');
    var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      var p = document.getElementById(t.getAttribute('data-target') || t.getAttribute('aria-controls'));
      if (p) { if (on) p.removeAttribute('hidden'); else p.setAttribute('hidden', ''); }
    });
    if (focus !== false) tab.focus();
  }
  document.addEventListener('click', function (e) {
    var tab = e.target.closest('[role="tablist"] [role="tab"]');
    if (tab) { e.preventDefault(); selectTab(tab); }
  });
  document.addEventListener('keydown', function (e) {
    var tab = e.target.closest ? e.target.closest('[role="tablist"] [role="tab"]') : null;
    if (!tab) return;
    var tabs = Array.prototype.slice.call(tab.closest('[role="tablist"]').querySelectorAll('[role="tab"]'));
    var i = tabs.indexOf(tab), next = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = tabs[(i + 1) % tabs.length];
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = tabs[(i - 1 + tabs.length) % tabs.length];
    else if (e.key === 'Home') next = tabs[0];
    else if (e.key === 'End') next = tabs[tabs.length - 1];
    if (next) { e.preventDefault(); selectTab(next); }
  });

  /* Details popover: close on outside click or Escape */
  document.addEventListener('click', function (e) {
    Array.prototype.forEach.call(document.querySelectorAll('details.menu[open]'), function (d) {
      if (!d.contains(e.target)) d.removeAttribute('open');
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    Array.prototype.forEach.call(document.querySelectorAll('details.menu[open]'), function (d) {
      d.removeAttribute('open');
      var s = d.querySelector('summary'); if (s) s.focus();
    });
  });

  /* Boot */
  function init(root) {
    Array.prototype.forEach.call(root.querySelectorAll('[data-phone]'), wirePhone);
    Array.prototype.forEach.call(root.querySelectorAll('textarea[data-counter]'), wireCounter);
    Array.prototype.forEach.call(root.querySelectorAll('[role="tablist"]'), function (list) {
      var sel = list.querySelector('[role="tab"][aria-selected="true"]') || list.querySelector('[role="tab"]');
      if (sel) selectTab(sel, false);
    });
  }
  portal.init = init;
  window.portal = portal;
  init(document);
})();
/* ---- page scripts below this line (builders) ---- */
/* Messages: GSM-7/UCS-2 segments, live preview, Reset without a round trip. */
(function () {
  'use strict';
  document.documentElement.classList.add('js');
  var GSM = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà";
  var EXT = "^{}\\[~]|€", TAG = '[SignalWire Free Trial]';
  var preview = document.getElementById('preview');
  var sample = {}, trial = false;
  if (preview) {
    try { sample = JSON.parse(preview.getAttribute('data-sample') || '{}'); } catch (e) { sample = {}; }
    trial = preview.getAttribute('data-trial') === '1';
  }
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var wide = window.matchMedia('(min-width: 1100px)');
  function raw(ta) { return ta.value || ta.placeholder || ''; }
  function suffixText() { var s = document.getElementById('opt_out_suffix'); return s ? raw(s) : ''; }
  /* Same rule as messages.MessageSet.render: fill allowed fill-ins, add the opt-out line when STOP is missing. */
  function rendered(ta) {
    var text = raw(ta), allowed = (ta.getAttribute('data-allowed') || '').split(' ');
    text = text.replace(/\{(\w+)\}/g, function (m, name) { return allowed.indexOf(name) >= 0 ? String(sample[name] || '') : ''; });
    var suffixed = ta.getAttribute('data-suffix-required') === '1' && !/\bstop\b/i.test(raw(ta));
    if (suffixed) text += ' ' + suffixText();
    return { text: text.replace(/\s+/g, ' ').trim(), suffixed: suffixed };
  }
  /* Mirrors portal_messages.segments: chars are UTF-16 units (String.length), code points decide the alphabet. */
  window.portalSegments = function (text, ta) {
    var r = ta && ta.hasAttribute('data-allowed') ? rendered(ta) : { text: text, suffixed: false };
    var body = (trial ? TAG + ' ' : '') + r.text, septets = 0, ucs2 = false, special = '';
    Array.from(body).forEach(function (c) {
      if (GSM.indexOf(c) >= 0) septets += 1; else if (EXT.indexOf(c) >= 0) septets += 2; else { ucs2 = true; special = special || c; }
    });
    var n = ucs2 ? (body.length <= 70 ? 1 : Math.ceil(body.length / 67)) : (septets <= 160 ? 1 : Math.ceil(septets / 153));
    var notes = [];
    if (r.suffixed) notes.push('Includes the opt-out line.');
    if (trial) notes.push("Includes the '" + TAG + "' tag until registration completes.");
    if (ucs2) notes.push('Uses a special character (' + special + '), so each text holds 70 characters.');
    if (ta && ta.value.length > 480) notes.push('Over the 480-character limit.');
    return { chars: body.length, segments: n, note: notes.join(' ') };
  };
  /* Red means over the 480-character limit, not "more than two texts". */
  function markOver(ta) {
    var out = document.getElementById(ta.id + '-count');
    if (out) out.classList.toggle('over', ta.value.length > 480);
  }
  function recount(ta) { portal.count(ta); markOver(ta); }
  function paint(ta) {
    if (!preview) return;
    var r = rendered(ta);
    Array.prototype.forEach.call(preview.querySelectorAll('[data-key="' + ta.id + '"] .text'), function (el) { el.textContent = r.text; });
  }
  var areas = Array.prototype.slice.call(document.querySelectorAll('textarea[data-allowed]'));
  areas.forEach(function (ta) {
    recount(ta);  /* the shared counter ran before portalSegments existed */
    ta.addEventListener('input', function () {
      paint(ta); markOver(ta);  /* the shared [data-counter] listener has already recounted this one */
      if (ta.id === 'opt_out_suffix') areas.forEach(function (other) { if (other.getAttribute('data-suffix-required') === '1') { paint(other); recount(other); } });
    });
    ta.addEventListener('focus', function () {
      if (!preview) return;
      Array.prototype.forEach.call(preview.querySelectorAll('.bubble.is-active'), function (b) { b.classList.remove('is-active'); });
      var bubble = preview.querySelector('[data-key="' + ta.id + '"]');
      if (!bubble) return;
      bubble.classList.add('is-active');
      /* Scroll the phone screen only, never the page. */
      var sc = preview.querySelector('.screen');
      if (sc && bubble.offsetParent) sc.scrollTo({ top: bubble.offsetTop - sc.clientHeight / 2 + bubble.offsetHeight / 2, behavior: reduce ? 'auto' : 'smooth' });
    });
  });
  /* The optional questions show or hide their bubbles. */
  ['ask_phone', 'ask_email'].forEach(function (name) {
    var box = document.querySelector('input[name="' + name + '"]');
    if (!box || !preview) return;
    box.addEventListener('change', function () {
      Array.prototype.forEach.call(preview.querySelectorAll('[data-when="' + name + '"]'), function (el) {
        if (box.checked) el.removeAttribute('hidden'); else el.setAttribute('hidden', '');
      });
      if (name === 'ask_email') { sample.invite_line = box.checked ? 'A calendar invite is on its way to dana@example.com.' : ''; sample.invited_email = box.checked ? 'dana@example.com' : ''; }
      areas.forEach(function (ta) { paint(ta); recount(ta); });
    });
  });
  /* Reset: clear the field now; Save persists it. Without JS the same button posts the form. */
  var form = document.getElementById('messages-form');
  if (form) form.addEventListener('click', function (e) {
    var b = e.target.closest('button[name="reset"]');
    if (!b) return;
    var ta = document.getElementById(b.value);
    if (!ta) return;
    e.preventDefault();
    ta.value = '';
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    ta.focus();
    portal.toast('Reset. Save to keep it.', 'info');
  });
  /* Preview sheet: a fixed <details> below 1100px, always open as the right rail from 1100px. */
  var sheet = document.getElementById('preview-sheet');
  if (sheet) {
    var fit = function () { sheet.open = wide.matches; };
    fit();
    if (wide.addEventListener) wide.addEventListener('change', fit); else if (wide.addListener) wide.addListener(fit);
  }
})();
/* Scheduling: length presets fill the number; the day rows follow the hours mode; Reset restores a group's defaults. */
(function () {
  'use strict';
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-set-for]');
    if (!b) return;
    var input = document.getElementById(b.getAttribute('data-set-for'));
    if (!input) return;
    input.value = b.getAttribute('data-set-value');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
  });
  var form = document.getElementById('scheduling-form');
  if (!form) return;
  var rows = document.getElementById('hours-rows'), hint = document.getElementById('hours_mode-hint');
  function sync() {
    var set = document.getElementById('hours_mode-set');
    var on = !!(set && set.checked);
    if (rows) { if (on) rows.removeAttribute('hidden'); else rows.setAttribute('hidden', ''); }
    if (hint) hint.textContent = hint.getAttribute(on ? 'data-hint-set' : 'data-hint-any') || hint.textContent;
  }
  Array.prototype.forEach.call(form.querySelectorAll('input[name="hours_mode"]'), function (r) { r.addEventListener('change', sync); });
  sync();
  /* Reset: put the group's controls back to data-default now; Save persists. Without JS the button posts the form. */
  form.addEventListener('click', function (e) {
    var b = e.target.closest('button[name="reset"]');
    if (!b) return;
    var ids = (b.getAttribute('data-reset') || b.value).split(' '), first = null;
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el || !el.hasAttribute('data-default')) return;
      first = first || el;
      var d = el.getAttribute('data-default');
      if (el.type === 'checkbox' || el.type === 'radio') el.checked = d === '1'; else el.value = d;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    if (!first) return;  /* nothing to restore here: let the server handle it */
    e.preventDefault();
    first.focus();
    portal.toast('Reset. Save to keep it.', 'info');
  });
})();
/* After a failed save, focus the first control the server marked invalid. */
(function () {
  'use strict';
  if (!document.querySelector('.flash.err')) return;
  var bad = document.querySelector('[aria-invalid="true"]');
  if (bad && typeof bad.focus === 'function') bad.focus();
})();
/* Phone and Calendar: a carrier pill shows its codes at once (Save keeps it); Verify / Check buttons
   show a busy label while the form posts (never disabled, or the pressed button would drop out of the post). */
(function () {
  'use strict';
  var pills = document.getElementById('carrier-pills');
  if (pills) {
    var show = function () {
      var on = pills.querySelector('input:checked'), key = on ? on.value : '';
      Array.prototype.forEach.call(document.querySelectorAll('[data-codes]'), function (block) {
        if (block.getAttribute('data-codes') === key) block.removeAttribute('hidden'); else block.setAttribute('hidden', '');
      });
      var none = document.getElementById('codes-none');
      if (none) { if (key) none.setAttribute('hidden', ''); else none.removeAttribute('hidden'); }
    };
    Array.prototype.forEach.call(pills.querySelectorAll('input'), function (r) { r.addEventListener('change', show); });
  }
  document.addEventListener('submit', function (e) {
    var b = e.submitter;
    if (!b || !b.hasAttribute('data-busy-label')) return;
    b.setAttribute('aria-busy', 'true');
    b.textContent = b.getAttribute('data-busy-label');
  });
})();
