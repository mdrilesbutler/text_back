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
