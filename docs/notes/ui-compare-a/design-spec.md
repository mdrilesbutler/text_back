# TextBack /client settings: design spec (variant A, "conversation spine")

Date 2026-10-22. Branch `ui/compare-a`. Inputs: `docs/notes/ui-compare-a/direction.md` (settled direction), `saas-website/docs/DESIGN.md` (the brand, which wins on taste), the explorer contract (which wins on behaviour) and `src/text_back/client_portal.py` MESSAGES/GROUPS (exact strings). If this spec and the behaviour contract disagree, the contract wins and the conflict gets flagged.

---

## 0. Non-negotiables

1. **Behaviour stays frozen.** Routes, methods, field names, status codes, cookies, notices and error strings do not change. Every save answers its own POST with a 200 page. No redirect, no `?saved=1`.
2. **`/client/verify` stays byte-identical** whether or not the number is on file. It shows no part of any phone number, and the string `0123` appears nowhere in the response: not in the sprite, inline markup or placeholders. CSS and JS are separate responses. I checked the current sprite and it has 0 hits.
3. **The Messages form always posts all 21 textareas plus `ask_phone` and `ask_email`.**
   - Never put `disabled` on a textarea or a switch.
   - The first control inside the form stays `<button type=submit class=vh tabindex=-1 aria-hidden=true name=save value=1></button>`.
4. **CSRF markup is literal:** `<input type=hidden name=csrf value='{{ csrf }}'>`. The name is unquoted and the value is single-quoted, because `csrf_of()` parses it that way.
5. **OTP inputs keep the attribute unquoted:** `autocomplete=one-time-code`. A test greps for exactly that.
6. **Everything works with JS off.** JS only adds behaviour (see the table in §5.3).
7. **One signature, the spine plus the bubble.** Everything else stays quiet: white cards and 1px stone borders. Only four things get a shadow: the phone frame, the account popover, the toast and the sticky save bar.
8. **Copy voice:**
   - Second person, sentences under 20 words, no exclamation points.
   - Never "AI".
   - Never a promise of a live human.

---

## 1. Tokens

### 1.1 Literal CSS (top of `src/text_back/static/client.css`)

```css
@font-face {
  font-family: "Archivo"; font-style: normal; font-weight: 600; font-display: swap;
  src: url("/client/static/fonts/archivo-600-latin.woff2") format("woff2");
}
@font-face {
  font-family: "Source Sans 3"; font-style: normal; font-weight: 400 600; font-display: swap;
  src: url("/client/static/fonts/source-sans-3-var-latin.woff2") format("woff2");
}

/* ---------- theme-dependent: LIGHT (default) ---------- */
:root,
[data-theme="light"] {
  color-scheme: light;

  /* Neutral scale: stone */
  --stone-50: #fafaf9;  --stone-100: #f5f5f4; --stone-200: #e7e5e4; --stone-300: #d6d3d1;
  --stone-400: #a8a29e; --stone-500: #78716c; --stone-600: #57534e; --stone-700: #44403c;
  --stone-800: #292524; --stone-900: #1c1917; --stone-950: #0c0a09;

  /* Surfaces */
  --bg: #ffffff;          /* page, cards, header, inputs' surroundings */
  --surface: #fafaf9;     /* sidebar, preview well, phone frame, chips, switch row */
  --raised: #ffffff;      /* popover, toast, sticky save bar, tab bar (always border + shadow/hairline) */
  --sunken: #f5f5f4;      /* hover fills, tracks, skeleton, disabled button fill */
  --field-bg: #ffffff;

  /* Text */
  --text-ink: #171717;
  --text-muted: #57534e;
  --text-subtle: #6b645f; /* counts, captions, placeholders; passes 4.5:1 on every surface */
  --on-accent: #ffffff;

  /* Lines */
  --line: #e7e5e4;        /* hairline: card borders, dividers (decorative) */
  --line-strong: #d6d3d1; /* secondary button border, spine, dashed elbows (decorative) */
  --line-input: #78716c;  /* field, radio, switch-off borders: >= 3:1 */

  /* Accent (one) */
  --accent: #166534;              /* text, links, icons, focus */
  --accent-fill: #166534;         /* primary button, TextBack bubble, switch on, radio dot */
  --accent-fill-hover: #14532d;
  --accent-fill-pressed: #0f3d22;
  --accent-tint: #e8f0eb;         /* accent/10 on white */
  --accent-tint-hover: #dae6df;   /* accent/16 on white */
  --accent-line: #b9d1c2;         /* accent/30 on white */

  /* Semantic status (always icon + word + color) */
  --success-fg: #166534; --success-bg: #e8f0eb; --success-line: #b9d1c2;
  --warning-fg: #92400e; --warning-bg: #fffbeb; --warning-line: #e9d6bf;
  --danger-fg:  #b91c1c; --danger-bg:  #fef2f2; --danger-line:  #f0c7c7;
  --info-fg:    #44403c; --info-bg:    #f5f5f4; --info-line:    #d6d3d1;
  --missed: #ef4444;     /* brand red: the missed-call dot only */

  /* Focus */
  --focus: #166534;

  /* Conversation */
  --bubble-customer-bg: #ffffff; --bubble-customer-fg: #171717; --bubble-customer-line: #e7e5e4;
  --bubble-textback-bg: #166534; --bubble-textback-fg: #ffffff;
  --bubble-you-bg: #171717;      --bubble-you-fg: #ffffff;
  --badge-customer: #57534e; --badge-textback: #166534; --badge-you: #171717;
  --phone-frame: #fafaf9; --phone-screen: #ffffff;
  --spine: #d6d3d1;

  /* Elevation (only phone, popover, toast, save bar) */
  --shadow-phone: 0 24px 60px -30px rgba(0, 0, 0, 0.35);
  --shadow-pop:   0 16px 40px -16px rgba(23, 23, 23, 0.28), 0 2px 6px -2px rgba(23, 23, 23, 0.10);
  --shadow-bar:   0 10px 30px -10px rgba(23, 23, 23, 0.25), 0 1px 3px rgba(23, 23, 23, 0.08);
}

/* ---------- theme-dependent: DARK (system) ---------- */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #0c0a09; --surface: #1c1917; --raised: #1c1917; --sunken: #292524; --field-bg: #0c0a09;
    --text-ink: #f5f5f4; --text-muted: #a8a29e; --text-subtle: #9c9590; --on-accent: #ffffff;
    --line: #292524; --line-strong: #44403c; --line-input: #857e79;
    --accent: #6fbf8b; --accent-fill: #15803d; --accent-fill-hover: #166534; --accent-fill-pressed: #14532d;
    --accent-tint: #202e23; --accent-tint-hover: #283d2d; --accent-line: #34523d;
    --success-fg: #6fbf8b; --success-bg: #202e23; --success-line: #34523d;
    --warning-fg: #e8b04b; --warning-bg: #261e11; --warning-line: #594420;
    --danger-fg:  #f87171; --danger-bg:  #281615; --danger-line:  #5f2e2d;
    --info-fg:    #d6d3d1; --info-bg:    #292524; --info-line:    #44403c;
    --missed: #ef4444;
    --focus: #6fbf8b;
    --bubble-customer-bg: #292524; --bubble-customer-fg: #f5f5f4; --bubble-customer-line: #44403c;
    --bubble-textback-bg: #15803d; --bubble-textback-fg: #ffffff;
    --bubble-you-bg: #f5f5f4;      --bubble-you-fg: #171717;
    --badge-customer: #a8a29e; --badge-textback: #6fbf8b; --badge-you: #f5f5f4;
    --phone-frame: #1c1917; --phone-screen: #0c0a09;
    --spine: #44403c;
    --shadow-phone: 0 24px 60px -30px rgba(0, 0, 0, 0.8);
    --shadow-pop:   0 16px 40px -12px rgba(0, 0, 0, 0.7), 0 2px 6px -2px rgba(0, 0, 0, 0.5);
    --shadow-bar:   0 10px 30px -8px rgba(0, 0, 0, 0.7), 0 1px 3px rgba(0, 0, 0, 0.5);
  }
}

/* ---------- theme-dependent: DARK (forced by Appearance or styleguide panel) ----------
   Declarations must stay identical to the media block above. */
:root[data-theme="dark"],
[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0c0a09; --surface: #1c1917; --raised: #1c1917; --sunken: #292524; --field-bg: #0c0a09;
  --text-ink: #f5f5f4; --text-muted: #a8a29e; --text-subtle: #9c9590; --on-accent: #ffffff;
  --line: #292524; --line-strong: #44403c; --line-input: #857e79;
  --accent: #6fbf8b; --accent-fill: #15803d; --accent-fill-hover: #166534; --accent-fill-pressed: #14532d;
  --accent-tint: #202e23; --accent-tint-hover: #283d2d; --accent-line: #34523d;
  --success-fg: #6fbf8b; --success-bg: #202e23; --success-line: #34523d;
  --warning-fg: #e8b04b; --warning-bg: #261e11; --warning-line: #594420;
  --danger-fg:  #f87171; --danger-bg:  #281615; --danger-line:  #5f2e2d;
  --info-fg:    #d6d3d1; --info-bg:    #292524; --info-line:    #44403c;
  --missed: #ef4444;
  --focus: #6fbf8b;
  --bubble-customer-bg: #292524; --bubble-customer-fg: #f5f5f4; --bubble-customer-line: #44403c;
  --bubble-textback-bg: #15803d; --bubble-textback-fg: #ffffff;
  --bubble-you-bg: #f5f5f4;      --bubble-you-fg: #171717;
  --badge-customer: #a8a29e; --badge-textback: #6fbf8b; --badge-you: #f5f5f4;
  --phone-frame: #1c1917; --phone-screen: #0c0a09;
  --spine: #44403c;
  --shadow-phone: 0 24px 60px -30px rgba(0, 0, 0, 0.8);
  --shadow-pop:   0 16px 40px -12px rgba(0, 0, 0, 0.7), 0 2px 6px -2px rgba(0, 0, 0, 0.5);
  --shadow-bar:   0 10px 30px -8px rgba(0, 0, 0, 0.7), 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* ---------- theme-independent ---------- */
:root {
  /* Families */
  --font-display: "Archivo", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-body: "Source Sans 3", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace; /* OTP only */

  /* Type scale (size / line-height / tracking) */
  --fs-display: 1.75rem;   --lh-display: 2.125rem; --tr-display: -0.01em;  /* 28/34, 32/40 at >=1024 */
  --fs-title: 1.375rem;    --lh-title: 1.75rem;    --tr-title: -0.005em;   /* 22/28 */
  --fs-heading: 1.125rem;  --lh-heading: 1.5rem;                           /* 18/24 */
  --fs-lead: 1.125rem;     --lh-lead: 1.75rem;                             /* 18/28 */
  --fs-body: 1.0625rem;    --lh-body: 1.625rem;                            /* 17/26 */
  --fs-label: 1rem;        --lh-label: 1.375rem;                           /* 16/22 */
  --fs-small: 0.9375rem;   --lh-small: 1.375rem;                           /* 15/22 */
  --fs-caption: 0.8125rem; --lh-caption: 1.125rem;                         /* 13/18, the floor */
  --fs-eyebrow: 0.875rem;  --lh-eyebrow: 1rem;     --tr-caps: 0.05em;      /* 14/16 brand eyebrow */
  --fs-bubble: 1rem;       --lh-bubble: 1.375rem;                          /* 16/22 card bubbles */
  --fs-bubble-rail: 0.9375rem; --lh-bubble-rail: 1.25rem;                  /* 15/20 rail bubbles */
  --fs-otp: min(1.875rem, calc((100vw - 2rem) / 10.44));                   /* 30px max, fits 320px */
  --fw-regular: 400; --fw-medium: 500; --fw-semibold: 600;

  /* Space: 4px base */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem; --space-5: 1.25rem;
  --space-6: 1.5rem;  --space-8: 2rem;   --space-10: 2.5rem; --space-12: 3rem; --space-14: 3.5rem;
  --space-16: 4rem;   --space-24: 6rem;

  /* Radius */
  --radius-sm: 6px;   /* buttons, inputs (brand 0.375rem) */
  --radius-md: 8px;   /* cards, status blocks, radio rows, nav items, OTP cells (brand 0.5rem) */
  --radius-lg: 12px;  /* preview well, popover, toast, save bar */
  --radius-bubble: 16px; --radius-tail: 6px;
  --radius-phone: 32px;  --radius-screen: 24px; --radius-full: 999px;

  /* Sizes */
  --tap: 2.75rem;      /* 44 */
  --tap-lg: 3rem;      /* 48 primary on phone */
  --tap-fine: 2.25rem; /* 36, only under (hover: hover) and (pointer: fine) */
  --field-h: 3rem;     /* 48 inputs everywhere */
  --otp-h: 3.5rem;     /* 56 */
  --icon-sm: 1rem; --icon-md: 1.125rem; --icon-lg: 1.25rem; --icon-nav: 1.5rem;

  /* Motion */
  --dur-fast: 120ms; --dur-base: 180ms; --dur-slow: 250ms; --dur-spin: 800ms;
  --ease-out: cubic-bezier(0.2, 0.8, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);

  /* Layers */
  --z-node: 1; --z-sticky: 10; --z-savebar: 20; --z-tabbar: 30; --z-popover: 40; --z-toast: 50; --z-skip: 60;

  /* Layout */
  --container: 66rem;  /* 1056 content max */
  --measure: 40rem;    /* 640 Business/Calendar column, Messages list max */
  --auth: 25rem;       /* 400 sign-in column */
  --rail-w: 20rem;     /* 320; 360 at >=1280 */
  --nav-w: 5.5rem;     /* 88 sidebar */
  --header-h: 3.5rem;  /* 56; 64 at >=1024 */
  --tabbar-h: 4rem;    /* 64 + safe area */
  --gutter: 1rem;      /* 16; 24 / 32 / 40 */
  --spine-col: 1.5rem; --spine-node: 1.5rem; --spine-gap: 0.5rem; --spine-icon: 0.875rem;
  --moment-gap: 2.5rem; --card-gap: 0.75rem; --card-pad: 1rem; --branch-indent: 1rem;
  --focus-w: 2px; --focus-off: 2px;
}
@media (min-width: 640px) {
  :root {
    --gutter: 1.5rem; --spine-col: 2.5rem; --spine-node: 2rem; --spine-gap: 1rem; --spine-icon: 1rem;
    --moment-gap: 3.5rem; --card-gap: 1rem; --card-pad: 1.25rem; --branch-indent: 1.5rem;
  }
}
@media (min-width: 1024px) {
  :root { --gutter: 2rem; --header-h: 4rem; --fs-display: 2rem; --lh-display: 2.5rem; }
}
@media (min-width: 1280px) {
  :root { --gutter: 2.5rem; --rail-w: 22.5rem; }
}
```

**Base rules:**
- `html { -webkit-text-size-adjust: 100%; }`
- `body { margin: 0; background: var(--bg); color: var(--text-ink); font: var(--fw-regular) var(--fs-body)/var(--lh-body) var(--font-body); }`
- `.tnum { font-variant-numeric: tabular-nums; }` on every count, phone number, OTP, save-bar N, limit counter and stepper number.
- `.vh` is the standard visually-hidden utility.
- `:focus-visible { outline: var(--focus-w) solid var(--focus); outline-offset: var(--focus-off); }` is the global focus ring.
- `a { color: var(--accent); text-underline-offset: 3px; }`

### 1.2 Type roles

| Role | Family | Size / LH | Weight | Tracking | Used for |
|---|---|---|---|---|---|
| Display | Archivo | 28/34 (32/40 at ≥1024) | 600 | -0.01em | H1, one per page |
| Title | Archivo | 22/28 | 600 | -0.005em | Moment H2, "Any time" H2, status block heading |
| Heading | Archivo | 18/24 | 600 | 0 | Card label H3, card headings ("What Google will ask"), picker legend, rail title |
| Lead | Source Sans 3 | 18/28 | 400 | 0 | Page lead, `--text-muted`, max 60ch |
| Body | Source Sans 3 | 17/26 | 400 (600 strong) | 0 | Paragraphs, inputs, textareas, radio names, toast text |
| Label | Source Sans 3 | 16/22 | 600 | 0 | Form labels, button text (16/20), switch text (500) |
| Small | Source Sans 3 | 15/22 | 400 | 0 | When-lines, rules, helpers, inline errors (600), account meta |
| Caption | Source Sans 3 | 13/18 | 500 (pills 600) | 0 | Counts, pills, tab-bar labels (13/16), phone sub-line |
| Eyebrow | Source Sans 3 | 14/16 | 500 | 0.05em, uppercase | Sign-in eyebrow, "Any time", "Optional questions", "Insert" |
| Role badge | Source Sans 3 | 13/16 | 600 | 0.05em, uppercase | CUSTOMER / TEXTBACK / YOU above bubbles |
| Bubble | Source Sans 3 | 16/22 card, 15/20 rail | 400 | 0 | SMS text |
| OTP | mono stack | `--fs-otp` / 1 | 600 | via letter-spacing | Code input only |

Nothing renders below 13px. Inputs and textareas are 17px, which stops iOS from zooming on focus. Archivo is used only for H1, H2 and H3.

### 1.3 Contrast table (computed, WCAG 2.x relative luminance)

| Kind | Pair | Light | Ratio | Dark | Ratio | Need |
|---|---|---|---|---|---|---|
| Text | `--text-ink` on `--bg` | #171717 / #ffffff | 17.93 | #f5f5f4 / #0c0a09 | 18.11 | 4.5 |
| Text | `--text-ink` on `--surface` | #171717 / #fafaf9 | 17.17 | #f5f5f4 / #1c1917 | 16.03 | 4.5 |
| Text | `--text-ink` on `--sunken` | #171717 / #f5f5f4 | 16.43 | #f5f5f4 / #292524 | 13.90 | 4.5 |
| Text | `--text-muted` on `--bg` | #57534e / #ffffff | 7.63 | #a8a29e / #0c0a09 | 7.83 | 4.5 |
| Text | `--text-muted` on `--surface` | #57534e / #fafaf9 | 7.30 | #a8a29e / #1c1917 | 6.93 | 4.5 |
| Text | `--text-muted` on `--sunken` | #57534e / #f5f5f4 | 6.99 | #a8a29e / #292524 | 6.01 | 4.5 |
| Text | `--text-subtle` on `--bg` | #6b645f / #ffffff | 5.81 | #9c9590 / #0c0a09 | 6.69 | 4.5 |
| Text | `--text-subtle` on `--surface` | #6b645f / #fafaf9 | 5.56 | #9c9590 / #1c1917 | 5.93 | 4.5 |
| Text | `--text-subtle` on `--sunken` | #6b645f / #f5f5f4 | 5.33 | #9c9590 / #292524 | 5.14 | 4.5 |
| Text | `--accent` (links, TextBack badge) on `--bg` | #166534 / #ffffff | 7.13 | #6fbf8b / #0c0a09 | 8.94 | 4.5 |
| Text | `--accent` on `--surface` | #166534 / #fafaf9 | 6.83 | #6fbf8b / #1c1917 | 7.91 | 4.5 |
| Text | `--accent` on `--accent-tint` (active nav, success pill, booked pill) | #166534 / #e8f0eb | 6.14 | #6fbf8b / #202e23 | 6.43 | 4.5 |
| Text | `--accent` on `--accent-tint-hover` | #166534 / #dae6df | 5.56 | #6fbf8b / #283d2d | 5.29 | 4.5 |
| Text | `--text-ink` on `--accent-tint` (checked radio row) | #171717 / #e8f0eb | 15.45 | #f5f5f4 / #202e23 | 13.04 | 4.5 |
| Text | `--on-accent` on `--accent-fill` (primary, TextBack bubble) | #ffffff / #166534 | 7.13 | #ffffff / #15803d | 5.02 | 4.5 |
| Text | `--on-accent` on `--accent-fill-hover` | #ffffff / #14532d | 9.11 | #ffffff / #166534 | 7.13 | 4.5 |
| Text | `--on-accent` on `--accent-fill-pressed` | #ffffff / #0f3d22 | 12.27 | #ffffff / #14532d | 9.11 | 4.5 |
| Text | customer bubble fg/bg | #171717 / #ffffff | 17.93 | #f5f5f4 / #292524 | 13.90 | 4.5 |
| Text | TextBack bubble fg/bg | #ffffff / #166534 | 7.13 | #ffffff / #15803d | 5.02 | 4.5 |
| Text | You bubble fg/bg | #ffffff / #171717 | 17.93 | #171717 / #f5f5f4 | 16.43 | 4.5 |
| Text | `--warning-fg` on `--warning-bg` | #92400e / #fffbeb | 6.84 | #e8b04b / #261e11 | 8.42 | 4.5 |
| Text | `--warning-fg` on `--bg` | #92400e / #ffffff | 7.09 | #e8b04b / #0c0a09 | 10.11 | 4.5 |
| Text | `--text-ink` on `--warning-bg` | #171717 / #fffbeb | 17.29 | #f5f5f4 / #261e11 | 15.08 | 4.5 |
| Text | `--text-muted` on `--warning-bg` | #57534e / #fffbeb | 7.36 | #a8a29e / #261e11 | 6.52 | 4.5 |
| Text | `--danger-fg` on `--danger-bg` | #b91c1c / #fef2f2 | 5.91 | #f87171 / #281615 | 6.24 | 4.5 |
| Text | `--danger-fg` on `--bg` | #b91c1c / #ffffff | 6.47 | #f87171 / #0c0a09 | 7.14 | 4.5 |
| Text | `--text-ink` on `--danger-bg` | #171717 / #fef2f2 | 16.39 | #f5f5f4 / #281615 | 15.83 | 4.5 |
| Text | `--text-muted` on `--danger-bg` | #57534e / #fef2f2 | 6.97 | #a8a29e / #281615 | 6.85 | 4.5 |
| Text | `--info-fg` on `--info-bg` | #44403c / #f5f5f4 | 9.42 | #d6d3d1 / #292524 | 10.18 | 4.5 |
| UI | `--line-input` (field, radio, switch-off) on `--bg`/`--field-bg` | #78716c / #ffffff | 4.80 | #857e79 / #0c0a09 | 4.95 | 3 |
| UI | `--line-input` on `--surface` (switch row) | #78716c / #fafaf9 | 4.59 | #857e79 / #1c1917 | 4.38 | 3 |
| UI | `--focus` ring on `--bg` | #166534 / #ffffff | 7.13 | #6fbf8b / #0c0a09 | 8.94 | 3 |
| UI | `--focus` ring on `--surface` | #166534 / #fafaf9 | 6.83 | #6fbf8b / #1c1917 | 7.91 | 3 |
| UI | `--accent-fill` (switch on, radio dot) on `--bg` | #166534 / #ffffff | 7.13 | #15803d / #0c0a09 | 3.94 | 3 |
| UI | `--missed` dot on `--bg` | #ef4444 / #ffffff | 3.76 | #ef4444 / #0c0a09 | 5.25 | 3 |
| UI | `--missed` dot on `--surface` | #ef4444 / #fafaf9 | 3.60 | #ef4444 / #1c1917 | 4.65 | 3 |
| UI | segment pips (`--text-muted`) on `--bg` | #57534e / #ffffff | 7.63 | #a8a29e / #0c0a09 | 7.83 | 3 |

**Exemptions and limits:**
- `--line`, `--line-strong` and `--spine` are decorative hairlines. They are never the only cue: order comes from headings, and state comes from icon plus word.
- Disabled controls are exempt from contrast, but still use `--text-subtle` on `--sunken` (5.33 / 5.14).
- `--text-subtle` is never used on status backgrounds.

---

## 2. Layout and shell

### 2.1 Breakpoints

| Name | Range | Navigation | Messages |
|---|---|---|---|
| phone | < 640 | bottom tab bar | one column, rail below the list |
| sm | 640–1023 | bottom tab bar | one column (list max 640), rail below |
| lg | 1024–1279 | 88px sidebar | list + sticky rail 320 |
| xl | ≥ 1280 | 88px sidebar | list (max 640) + sticky rail 360 |

**768–1023 decision: bottom tabs, not the sidebar.**
- Those widths are mostly tablets held in the hand, where the bottom bar is in thumb reach.
- With a sidebar, the Messages list plus rail would squeeze cards under 400px.
- One switch point (1024) means one navigation rule to test.

### 2.2 Shell DOM (every signed-in page)

```html
<html lang="en" class="no-js" data-theme="{light|dark|absent}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="light dark">
  <meta name="theme-color" media="(prefers-color-scheme: light)" content="#ffffff">
  <meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0c0a09">
  <meta name="robots" content="noindex">
  <meta name="format-detection" content="telephone=no">   <!-- stops iOS linking numbers inside bubbles -->
  <title>{Page} · TextBack</title>
  <link rel="preload" href="/client/static/fonts/source-sans-3-var-latin.woff2?v={{v}}" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/client/static/fonts/archivo-600-latin.woff2?v={{v}}" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/client/static/client.css?v={{v}}">
  <script src="/client/static/client.js?v={{v}}" defer></script>
</head>
<body>
  {% include "client/_icons.svg.j2" %}
  <a class="skip" href="#main">Skip to content</a>
  <div class="shell">
    <header class="topbar">…</header>
    <nav class="nav" aria-label="Settings">…</nav>          <!-- one element: tab bar <1024, sidebar >=1024 -->
    <main id="main" class="page" tabindex="-1">…</main>
  </div>
  <div class="toast-region" data-toast-region aria-live="polite"></div>
  <div class="vh" id="announcer" aria-live="polite"></div>
</body>
```

- `client.js` replaces `no-js` with `js` on `<html>` on its first line.
- Pages without JS never depend on the `js` class for content, only for enhancement.

**Grid:**
- Phone: `.shell { display: block }`.
- ≥1024: `.shell { display: grid; grid-template-columns: var(--nav-w) minmax(0, 1fr); grid-template-areas: "top top" "nav main"; }`.

**Page container:**
- `.page { max-width: calc(var(--container) + 2 * var(--gutter)); margin-inline: auto; padding: var(--space-6) var(--gutter) calc(var(--tabbar-h) + env(safe-area-inset-bottom) + var(--space-12)); }`
- At ≥1024: `padding: var(--space-10) var(--gutter) var(--space-24)`.
- Never any horizontal page scroll. Use `min-width: 0` on grid children and `overflow-wrap: anywhere` inside bubbles.

### 2.3 Header (`.topbar`), full width on every size, not sticky

**Box:** height `--header-h`. `padding-inline: max(var(--gutter), env(safe-area-inset-left))` (right side mirrored). `background: var(--bg)`, `border-bottom: 1px solid var(--line)`. `display: flex; align-items: center; gap: var(--space-3)`.

**Contents, left to right:**
1. Brand link `.brand`.
   - Signed in it points to `/client/messages`; signed out to `/client/login`.
   - Contents: `i-message-square-text` at 20px in `--accent`, plus "TextBack" in Archivo 600 18/24 ink. No underline. Focus ring.
2. Separator `.topbar__sep`: 1×20px, `--line-strong`. Signed in only.
3. Business name `.topbar__biz`: 15/22 500 `--text-muted`. `flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis`. Signed in only.
4. Account menu `details.menu` (§3.19), `margin-left: auto`. Signed in only.

The header is not sticky. The tab bar holds navigation on phone, so a sticky header would only take daylight-reading space. The ≥1024 sidebar is sticky by itself.

### 2.4 Navigation (`nav.nav`)

**Markup:** three `a.nav__item`, each `<span class="nav__icon"><svg><use href="#i-…"/></svg></span><span class="nav__label">…</span>`. The current page gets `aria-current="page"`.

| Item | Icon |
|---|---|
| Messages | `i-message-square-text` |
| Business | `i-store` |
| Calendar | `i-calendar-days` |

**Below 1024 (tab bar):**
- Container: `position: fixed; inset: auto 0 0 0; z-index: var(--z-tabbar); height: calc(var(--tabbar-h) + env(safe-area-inset-bottom)); padding-bottom: env(safe-area-inset-bottom); background: var(--raised); border-top: 1px solid var(--line); display: grid; grid-template-columns: repeat(3, 1fr)`.
- Item: `display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; min-height: 64px`. Label 13/16.

**At 1024 and up (sidebar):**
- Container: `grid-area: nav; position: sticky; top: 0; align-self: start; height: 100dvh; background: var(--surface); border-right: 1px solid var(--line); padding: var(--space-4) var(--space-2); display: flex; flex-direction: column; gap: var(--space-1)`.
- Items: the same vertical icon-over-label component at 72×64, `border-radius: var(--radius-md)`.

The tab bar and sidebar reuse one component. That consistency is worth more than a wide sidebar with only three entries.

### 2.5 Content widths

| Screen | Width |
|---|---|
| Sign in, Enter code | `.auth` max 400px. Margin top 32px on phone, 96px at ≥1024. Centred. |
| Business, Calendar | `.page__body` max 640px, left-aligned inside `.page`, so H1 x-position matches Messages. |
| Messages | `.msg-layout`. Phone: block, list max 640, centred at sm. ≥1024: `display: grid; grid-template-columns: minmax(0, 1fr) var(--rail-w); column-gap: var(--space-10)`, which becomes `var(--space-14)` at ≥1280. The list column stays ≤ 640. |

Computed widths:
- 1024: content 872, list 512, card 456.
- 1280: content 1056, list 640, card 584.
- 375: content 343, card 311, branch card 295.

### 2.6 Rail placement

- **≥1024:** `aside.rail` is grid column 2, `position: sticky; top: var(--space-6); align-self: start; max-height: calc(100dvh - var(--space-12)); display: flex; flex-direction: column`.
- **Below 1024:** the rail renders after the form. `margin-top: var(--space-12); padding-top: var(--space-8); border-top: 1px solid var(--line)`. `id="conversation"` is the target of the "See the whole conversation" link.
- The aside sits **outside** the `<form>`, so its scenario radios are never posted.

### 2.7 Wireframes

Legend:

| Mark | Meaning |
|---|---|
| `[ ]` | button |
| `( )` | pill or radio |
| `:` | the spine |
| `'` | dashed branch elbow |
| `{  }` | preview well |
| `<- n ->` | width in px |

**Sign in, 375**
```
+---------------------------------------+
| [#] TextBack                          |  topbar 56
+---------------------------------------+
   (32)
   SCHEDULING ASSISTANT SETTINGS           eyebrow 14 accent
   Oak & Pine Tree Care                    H1 28/34
   Enter the business mobile on file       lead 18/28 muted
   and we'll text you a sign-in code.
   No password to remember.
   (24)
   Business mobile                         label 16/600
   +-----------------------------------+
   | 704 555 0123                      |   input 48, tel
   +-----------------------------------+
   (16)
   [          Text me a code           ]   primary lg 48, full width
   (40)
   TextBack by FluxWorks                   caption, subtle
```
**Sign in, 1024:** same column, 400 wide and centred, 96 below the 64 topbar. No nav, no account menu.

**Enter code, 375 (1024 is the same 400 column)**
```
+---------------------------------------+
| [#] TextBack                          |
+---------------------------------------+
   OAK & PINE TREE CARE                    eyebrow
   Check your phone                        H1
   Enter the 6-digit code we just          lead
   texted. It expires in ten minutes.
   Sign-in code                            label
   +----++----++----++----++----++----+
   | 4  || 8  || 1  ||    ||    ||    |    ONE input drawn as 6 cells, 56 tall
   +----++----++----++----++----++----+
   [              Sign in              ]   primary lg
   Didn't get it? Send a new code          link 16/22 600 accent, 44 tall
```

**Messages, 375, top of page, clean**
```
+---------------------------------------+
| [#] TextBack | Oak & Pine Tree C… (o v)|  topbar 56
+---------------------------------------+
 Your messages                            H1
 Every text Oak & Pine Tree Care's        lead
 scheduling assistant sends, in the
 order a customer meets them. Changes
 apply to new conversations after you
 save.
 (i) Previews fill in sample details,     small, subtle
     like tree removal at 12 Elm St.
 [v See the whole conversation]           link, 44 tall (hidden >=1024)
 (32)
 (P)* Missed call                         node 24 + red dot, H2 22/28
  :   A call goes unanswered. Within      blurb small muted
  :   seconds the caller gets this text.
  :  +--------------------------------+   card 311
  :  | First text after a missed call |   H3 18/24
  :  | Sent the moment a call goes    |   when, small muted
  :  | unanswered.                    |
  :  | (v Standard wording)           |   pill 28 (row min 44)
  :  | [s] Carriers require an opt-out|   rule, small muted, shield icon
  :  |     line: if your wording…     |
  :  | {   (* Missed call · just now) }|  well: missed pill
  :  | {                    TEXTBACK  }|
  :  | {    +---------------------+   }|
  :  | {    | Hey, sorry we missed|   }|  bubble 16/22
  :  | {    | your call—this is…  |   }|
  :  | {    | Reply STOP to opt   |   }|
  :  | {    | out.               _/   }|
  :  | Opt-out line added             |   link 15/22 accent
  :  |     134 characters · 3 texts ##|   caption tnum + pips (right)
  :  |--------------------------------|   hairline
  :  | [/] Edit wording            v  |   summary 44
  :  +--------------------------------+
  :  (40)
 (?)  The questions
  :   Asked one at a time, in this order…
+---------------------------------------+
|   [=]          [=]          [=]       |  tab bar 64 + safe area
| Messages    Business    Calendar      |
+---------------------------------------+
```

**Messages, 375, question with branch, optional question off**
```
  :  +--------------------------------+
  :  | Question 3: day and time       |
  :  | Asked once the location is…    |
  :  | (v Standard wording)           |
  :  | {   TEXTBACK  [What day and…]  }|
  :  |      138 characters · 1 text #  |
  :  | [/] Edit wording            v  |
  :  +--------------------------------+
  :    '  (8)
  :    '-+------------------------------+   branch, indent 16, dashed elbow
  :      | If the time could not be     |
  :      | understood                   |
  :      | Sent instead of moving on…   |
  :      | (v Standard wording)         |
  :      | { CUSTOMER                   }|
  :      | { [Sometime next week]       }|  customer bubble, left
  :      | {             TEXTBACK       }|
  :      | {   [Please send a day and…] }|
  :      | [/] Edit wording          v  |
  :      +------------------------------+
  :  +--------------------------------+
  :  | Question 4: the name           |  …
  :  OPTIONAL QUESTIONS                    eyebrow
  :  +--------------------------------+
  :  | Optional question: best phone  |
  :  | number                         |
  :  | Asked only when switched on.…  |
  :  | (v Standard wording)           |
  :  | +----------------------------+ |  switch row (surface)
  :  | | Also ask for the best      | |
  :  | | phone number        (o-- ) | |  switch off
  :  | +----------------------------+ |
  :  | Not asked right now. Switch it |  replaces well + meta
  :  | on to add this question.       |
  :  | [/] Edit wording            v  |
  :  +--------------------------------+
  :  (phone_reprompt branch: display none, still posted)
```

**Messages, 375, rejected save and dirty save bar**
```
 +-------------------------------------+   error summary, under page head
 |# (!) Not saved. Fix First text after|   4px danger left bar, danger-bg
 |#     a missed call: must not promise|
 |#     a person or the business line  |
 |#     ('call us').                   |
 +-------------------------------------+
 …
  :  +================================+   invalid card: danger-line border + 4px danger inset bar
  :  | First text after a missed call |
  :  | (/ Customized) (! Unsaved)     |
  :  | [<- Use standard wording]      |   ghost, 44
  :  | {   …bubble with typed text… } |
  :  | [/] Edit wording            ^  |   open
  :  | (x) Not saved: must not promise|   field-error 15/22 600 danger
  :  |     a person or the business…  |
  :  | +----------------------------+ |
  :  | | Hi from Oak & Pine, call us| |   textarea, danger border
  :  | | anytime…                   | |
  :  | +----------------------------+ |
  :  | Texts are sent as one para…    |   helper
  :  | INSERT (+ Business name)       |   chips
  :  +================================+
 +-------------------------------------+   save bar: sticky, bottom = tabbar + 8
 | (!) Not saved   [Show] [Save changes]|   raised + shadow-bar, radius 12, 64 tall
 +-------------------------------------+
+---------------------------------------+
|  tab bar                              |
+---------------------------------------+
```

**Messages, 375, end of page (Any time, resting save bar, rail)**
```
  :  … You step in cards …                 spine ends at the last card
 (40)
 ANY TIME                                  eyebrow, no node, no spine
 START, HELP and STOP                      H2
 Replies carriers require to the three…    blurb
 +------------------------------------+    cards full column width (no spine offset)
 | Reply to START                     |
 | { CUSTOMER [START]  TEXTBACK [You're subscribed…] } |
 +------------------------------------+
 … Reply to HELP, Reply to STOP, Opt-out line …
 (32)
 +------------------------------------+    save bar resting (clean): static, no shadow
 | (v) All changes saved  [Save changes]|  Save aria-disabled
 +------------------------------------+
 ------------------------------------- (48 + hairline)
 Conversation preview                      #conversation, H2 (heading style)
 (Books a job) (Second try) (No reply)     scenario radios, wrap
 (Calendar error) (Needs you) (Safety)
 (Keywords)
 +------------------------------------+    phone frame max 384, centred
 | +--------------------------------+ |
 | | (OP) Oak & Pine Tree Care      | |
 | |      Text message              | |
 | |--------------------------------| |
 | |   (* Missed call · just now)   | |    log 480 tall, scrolls
 | |                     TEXTBACK   | |
 | |       [Hey, sorry we missed…]  | |
 | | CUSTOMER                       | |
 | | [Yes, I need some tree work.]  | |
 | +--------------------------------+ |
 +------------------------------------+
 Sample conversation · nothing is sent ·   caption
 names invented                  [Play]
```

**Messages, 1024**
```
+------------------------------------------------------------------------------------------------+
| [#] TextBack | Oak & Pine Tree Care                                                     (o v)   |  64
+--------+---------------------------------------------------------------------------------------+
| <-88-> | (40)                                                                                  |
|  (=)   | Your messages                                                        H1 32/40         |
|Messages| Every text Oak & Pine Tree Care's scheduling assistant sends, in the order a customer  |
|        | meets them. Changes apply to new conversations after you save.                         |
|  [=]   | (i) Previews fill in sample details, like tree removal at 12 Elm St.                   |
|Business| (32)                                                                                  |
|        | <------------- list 512 --------------->  <40>  <------- rail 320, sticky top 24 ---> |
|  [=]   | (P)* Missed call                                 Conversation preview                  |
|Calendar|  :   A call goes unanswered. Within seconds…     (Books a job)(Second try)(No reply)   |
|        |  :  +--------------------------------------+     (Calendar error)(Needs you)(Safety)  |
|        |  :  | First text after a missed call       |     (Keywords)                           |
|        |  :  | Sent the moment a call goes unanswered|    +-------------------------------+    |
|        |  :  | (v Standard wording)                 |     | +---------------------------+ |    |
|        |  :  | [s] Carriers require an opt-out line…|     | | (OP) Oak & Pine Tree Care | |    |
|        |  :  | {   (* Missed call · just now)      }|     | |      Text message         | |    |
|        |  :  | {                         TEXTBACK  }|     | |---------------------------| |    |
|        |  :  | {        [Hey, sorry we missed… ]   }|     | | (* Missed call · just now)| |    |
|        |  :  | Opt-out line added  134 characters · 3 texts ###  |  [Hey, sorry we…]   ←ring | |    |
|        |  :  | [/] Edit wording                   v |     | | CUSTOMER [Yes, I need…]   | |    |
|        |  :  +--------------------------------------+     | +---------------------------+ |    |
|        |  :  (40)                                         +-------------------------------+    |
|        | (?)  The questions                               Sample conversation · nothing is     |
|        |  :  …                                            sent · names invented        [Play]  |
|        | +-- save bar (sticky bottom 16, list width) --+                                       |
|        | | 2 unsaved changes      [Discard] [Save changes]|                                    |
+--------+---------------------------------------------------------------------------------------+
```

**Business, 375 (1024: same card in a 640 column; button auto width, left)**
```
 Your business                             H1
 How the assistant introduces the          lead
 business, where customers are pointed,
 and where sign-in codes go.
 +-------------------------------------+   card
 | Business name                       |   label
 | Used in every text customers get.   |   helper
 | +---------------------------------+ |
 | | Oak & Pine Tree Care            | |   input 48
 | +---------------------------------+ |
 | { IN THE FIRST TEXT               } |   eyebrow inside well
 | {     [Hey, sorry we missed your… ]} |  live TextBack bubble
 | (24)                                |
 | Number in the HELP reply   Optional |
 | Shown when a customer texts HELP.   |
 | Leave blank to show (704) 555-0100. |
 | Customers are never transferred to  |
 | it; the assistant handles the       |
 | texting.                            |
 | +---------------------------------+ |
 | |                                 | |
 | +---------------------------------+ |
 | (24)                                |
 | Your mobile                         |
 | Sign-in codes come to this number.  |
 | If you change it, we text a code to |
 | the new number and nothing changes  |
 | until you enter it.                 |
 | +---------------------------------+ |
 | | (980) 555-0123                  | |
 | +---------------------------------+ |
 +-------------------------------------+
 (24)
 [        Save business details        ]   primary lg, full width <640
```

**Confirm new mobile, 375 (1024: same, 640 column)**
```
 Confirm your new mobile                   H1
 (v)----------------(2)                    stepper
 Details saved      Confirm the new number
 We texted a six-digit code to             lead (number allowed here: signed in)
 (980) 555-0199. Enter it to move sign-in
 to that number. It expires in ten
 minutes; until then codes still go to
 your current mobile.
 +-------------------------------------+
 | Code from the text                  |
 | [ ][ ][ ][ ][ ][ ]                  |   OTP
 +-------------------------------------+
 [          Confirm new mobile          ]   primary lg
 [        Keep my current mobile        ]   secondary, separate form
 Didn't get it? [Send the code again]      ghost, separate form
```

**Calendar, 375, connected + picker**
```
 Your calendar
 The assistant only offers times that are free on this calendar, and every
 booking is added to it before the customer gets a confirmation.
 +-------------------------------------+   status block, data-status=ready
 | (calendar-check Connected)          |   success pill
 | Connected to Google Calendar        |   title 22/28
 | Google Calendar is connected.       |   body
 | Appointments are checked against    |
 | and booked on **Tree jobs**.        |
 |-------------------------------------|
 | Calendar   Tree jobs                |   dl, 15/22, tnum
 | Provider   Google                   |
 +-------------------------------------+
 (24)
 +-------------------------------------+   picker card
 | Which calendar should the assistant |   legend, heading 18/24
 | use?                                |
 | Free times are checked on this      |
 | calendar and new appointments are   |
 | added to it.                        |
 | +---------------------------------+ |
 | | ( ) Personal (main calendar)    | |   56 row
 | +---------------------------------+ |
 | +=================================+ |   checked: accent border + tint
 | | (o) Tree jobs        (v In use) | |
 | +=================================+ |
 | [          Use this calendar      ] |
 +-------------------------------------+
 (24)
 +-------------------------------------+
 | What Google will ask                |
 | • You pick the Google account that  |
 |   owns your business calendar.      |
 | • …                                 |
 | [   Reconnect Google Calendar     ] |   secondary when ready
 +-------------------------------------+
```

**Calendar, 1024, reconnect needed (640 column)**
```
 Your calendar                                            H1
 lead
 +-------------------------------------------------------+
 | (triangle-alert Paused)                               |  warning pill
 | Reconnect needed                                      |
 | Google has disconnected the calendar. Bookings are   |
 | paused until you reconnect.                          |
 |-------------------------------------------------------|
 | Bookings   Paused                                     |
 +-------------------------------------------------------+
 +-------------------------------------------------------+
 | What Google will ask                                  |
 | • … (4 lines)                                         |
 | [Connect Google Calendar]                             |  primary
 +-------------------------------------------------------+
 (picker hidden while not connected)
```

**Styleguide, 1024**
```
 Styleguide                                              H1
 Every token and component on the settings pages…        lead
 [On this page: Tokens · Type · … · Save bar]            anchor list, wraps
 ── Buttons ───────────────────────────────────────────
 +---------- LIGHT (data-theme=light) ---+---------- DARK (data-theme=dark) ----+
 | specimen grid                         | identical specimen grid              |
 +---------------------------------------+--------------------------------------+
 ── Fields ── … (each section repeats the light|dark pair; stacked below 1024)
```

---

## 3. Component inventory

Every hover style applies only inside `@media (hover: hover)`. Styleguide forced states use `.is-hover`, `.is-active` and `.is-focus` alongside the matching pseudo-classes. Every icon is `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-NAME"/></svg>` with `width/height: 1em` unless a size is given.

### 3.1 Buttons `.btn`

**Base:**
- `display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2)`.
- `height: var(--tap); padding: 0 var(--space-4); border: 1px solid transparent; border-radius: var(--radius-sm)`.
- `font: var(--fw-semibold) var(--fs-label)/1.25rem var(--font-body); white-space: nowrap; cursor: pointer`.
- `transition: background-color var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out)`.
- Icon 18px.

**Size modifiers:**
- `.btn--lg` is 48 tall with 20px padding.
- `.btn--block` is `width: 100%`.
- Below 1024, `.btn--primary` is always 48 tall.
- `.btn--sm` (36) is allowed only under `(hover: hover) and (pointer: fine)`. Otherwise it stays 44.

| Variant | Default | Hover | Pressed (`:active`) | Focus-visible | Disabled (`aria-disabled="true"`) | Loading |
|---|---|---|---|---|---|---|
| `--primary` | bg `--accent-fill`, fg `--on-accent` | bg `--accent-fill-hover` | bg `--accent-fill-pressed` | global ring, offset 2 | bg `--sunken`, fg `--text-subtle`, border `--line`, `cursor: not-allowed` | spinner icon (`i-loader-circle`, rotating), label swapped (§6), `aria-disabled="true"`, width locked to pre-loading width |
| `--secondary` | bg `--bg`, fg `--text-ink`, border `--line-strong` | bg `--sunken` | bg `--line` | ring | fg `--text-subtle`, border `--line` | same as primary |
| `--ghost` | transparent, fg `--accent` | bg `--accent-tint` | bg `--accent-tint-hover` | ring | fg `--text-subtle` | n/a |
| `--danger-ghost` | transparent, fg `--danger-fg` | bg `--danger-bg` | bg `--danger-line` | ring | fg `--text-subtle` | n/a |
| `.icon-btn` | 44×44, radius md, transparent, fg `--text-muted`, icon 20 | bg `--sunken`, fg `--text-ink` | bg `--line` | ring | n/a | n/a |

**Disabled and loading rules:**
- Use `aria-disabled` rather than `disabled`, so the control stays discoverable. JS blocks activation.
- The real `disabled` attribute is never used outside the styleguide.
- Loading starts on the form's `submit` event, applied to `event.submitter`.
- While loading, the form gets `data-busy`. Further submits are blocked with `preventDefault()`.

**Where each variant is used:**

| Variant | Used for |
|---|---|
| Primary | Text me a code, Sign in, Save changes, Save business details, Confirm new mobile, Use this calendar, Connect Google Calendar (when not connected) |
| Secondary | Keep my current mobile, Reconnect Google Calendar (when connected) |
| Ghost | Use standard wording, Send the code again, Show, Undo, Play |
| Danger-ghost | Discard |
| Icon | toast close, account trigger |

### 3.2 Text input `.input` (inside `.field`)

**Input:**
- `height: var(--field-h); width: 100%; padding: 0 14px; font: 400 var(--fs-body)/1.5rem var(--font-body)`.
- `color: var(--text-ink); background: var(--field-bg); border: 1px solid var(--line-input); border-radius: var(--radius-sm)`.
- Placeholder colour `--text-subtle`.

**Field order** (helper above the control, so it stays visible above the phone keyboard):
1. `label` (16/22 600).
2. Optional tag `.tag`: "Optional", 13/18 500 `--text-subtle`, `margin-left: 8px`, inside the label.
3. `.field-help` (15/22 muted, margin 4px 0 8px).
4. The control.
5. `.field-error` (margin-top 8).

Fields are stacked with a 24px gap.

**States:**

| State | Style |
|---|---|
| Hover | border `--text-muted` |
| Focus | border `--accent-fill`, `outline: 2px solid var(--focus); outline-offset: 1px` |
| Invalid (`aria-invalid="true"`) | border `--danger-fg` plus `box-shadow: inset 0 0 0 1px var(--danger-fg)` (2px look, no layout shift) |
| Error text | `.field-error` with `id`, referenced by `aria-describedby` |
| Read-only and disabled | not used |

### 3.3 Tel input `.input.input--tel`

**Attributes:** `type=tel inputmode=tel maxlength=24`, `.tnum`.
- Sign-in `mobile` and `owner_mobile` use `autocomplete=tel`.
- `business_contact` uses `autocomplete=off`. It is the business's number, not the user's.

**Formatting** is JS and on `blur` only. Never reformat while typing. Never block characters (`+` is allowed).
1. Strip non-digits.
2. If 11 digits starting with 1, drop the 1.
3. If 10 digits, set the value to `(AAA) BBB-CCCC`. Otherwise leave it untouched.

The server's `normalize_mobile` accepts either form.

### 3.4 Textarea `.textarea` (message editor)

- `width: 100%; padding: 12px 14px; font: 400 var(--fs-body)/var(--lh-body) var(--font-body)`. Border, background and states as for `.input`.
- `min-height: calc(3 * var(--lh-body) + 26px)` (≈104px). `max-height: calc(12 * var(--lh-body) + 26px)`, then it scrolls.
- Auto-grow uses `field-sizing: content` where supported. The JS fallback runs on `input` and on the editor's `toggle`: set `height = 'auto'`, then `height = scrollHeight + 2 + 'px'`.
- No-JS or unsupported: `rows=4` with `resize: vertical`. With JS auto-grow: `resize: none`.
- Attributes: `maxlength=480 spellcheck=true autocapitalize=sentences enterkeyhint=done`.
- **Enter is blocked** (JS `keydown`, `!e.isComposing`), because texts are one paragraph and the server collapses whitespace anyway.

### 3.5 OTP field `.otp` (one real input, six CSS cells)

```html
<div class="otp" data-otp>
  <input id=code name=code class="otp__input" inputmode=numeric autocomplete=one-time-code
         pattern="[0-9]{6}" maxlength=6 required autofocus spellcheck=false autocapitalize=off
         autocorrect=off aria-describedby="code-help [code-error]">
  <span class="otp__cells" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></span>
</div>
```

```css
.otp { position: relative; width: 17ch; height: var(--otp-h); overflow: hidden;
       font: 600 var(--fs-otp)/1 var(--font-mono); font-variant-numeric: tabular-nums; }
.otp__cells { position: absolute; inset: 0; display: flex; gap: 0.4ch; pointer-events: none; }
.otp__cells i { flex: none; width: 2.5ch; height: 100%; border: 1px solid var(--line-input);
                border-radius: var(--radius-md); background: var(--field-bg); }
.otp__input { position: relative; z-index: 1; display: block; width: 18.2ch; height: 100%;
              margin: 0; padding: 0 0 0 0.75ch; border: 0; background: transparent; outline: none;
              font: inherit; letter-spacing: 1.9ch; color: var(--text-ink); caret-color: var(--accent); }
.otp__cells i { z-index: 0; }              /* cells sit behind; input bg is transparent */
.otp:focus-within .otp__cells i { border-color: var(--accent-fill); }
.otp:focus-within .otp__cells i:nth-child(var-from-JS) { … }   /* see JS note */
.otp:has(.otp__input[aria-invalid="true"]) .otp__cells i { border-color: var(--danger-fg); }
```

**How the geometry works:**
- Every measurement is in `ch` of the monospace stack, so each digit (exactly 1ch wide) lands centred in its 2.5ch cell. The pitch is 2.9ch, which is 1ch of glyph plus 1.9ch of spacing.
- The input is 18.2ch wide inside a 17ch clipped wrapper. That leaves the caret room after the sixth digit, so the browser never scrolls the text sideways.
- `--fs-otp` keeps the whole field inside 288px at 320px viewports.

**Focus:**
- Without JS, the whole group's cells turn accent on focus.
- With JS, `data-filled="n"` on `.otp` gives the next empty cell a 2px accent border: `.otp[data-filled="0"] .otp__cells i:nth-child(1)` through `[data-filled="5"] … :nth-child(6)` set `box-shadow: inset 0 0 0 1px var(--accent-fill)`.

**JS:**
- On `paste`, strip non-digits, keep the first 6, set the value and `preventDefault`.
- On `input`, strip non-digits. This handles autofill with spaces.
- No auto-submit. WCAG 3.2.2 applies, and the user taps Sign in.

**Error:** the inline `.field-error` sits below the cells, and the input gets `aria-invalid`.

**Check before shipping:** test iOS Safari, Chrome Android and desktop Firefox. If digits drift, adjust only the 1.9ch / 0.75ch pair.

### 3.6 Switch `.switch` ("Also ask")

```html
<label class="switch-row" for="ask_phone">
  <span class="switch-row__text">Also ask for the best phone number</span>
  <input type="checkbox" role="switch" class="switch" id="ask_phone" name="ask_phone" value="1" {checked}>
</label>
```

**Row:** `display: flex; justify-content: space-between; align-items: center; gap: 16px; min-height: 44px; padding: 8px 12px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-md)`. Text 16/22 500 ink.

**Switch:** `appearance: none; flex: none; width: 44px; height: 26px; border: 2px solid var(--line-input); border-radius: var(--radius-full); background: var(--field-bg); position: relative; cursor: pointer`.

**Thumb** (`::before`): 18×18 at top 2, left 2, `--line-input`, `transition: transform var(--dur-base) var(--ease-standard), background-color var(--dur-base)`.

**States:**

| State | Style |
|---|---|
| Checked | bg and border `--accent-fill`, thumb `--on-accent`, `transform: translateX(18px)` |
| Hover | off: border `--text-muted`; on: bg `--accent-fill-hover` |
| Focus-visible | global ring |

The on/off state is carried by thumb position plus fill, and announced by `role=switch`. When messages are not editable, the switch is replaced by a pill: "Asked" (success, `i-check`) or "Not asked" (neutral, `i-x`).

### 3.7 Radio list `.choice-list` (calendar picker)

**Fieldset** (border and padding reset): `legend` styled as Heading 18/24 Archivo, then `.field-help`, then the choices with an 8px gap.

```html
<label class="choice"><input class="radio" type=radio name=calendar_id value="…" {checked}>
  <span class="choice__text"><span class="choice__name">Personal</span><span class="choice__meta"> (main calendar)</span></span>
  {% if current %}<span class="pill pill--success"><svg i-circle-check/>In use</span>{% endif %}
</label>
```

**Choice row:** `display: grid; grid-template-columns: 20px 1fr auto; gap: 12px; align-items: center; min-height: 56px; padding: 12px 16px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--bg); cursor: pointer`.
- Name 17/26 600.
- Meta 15/22 muted.

**Radio:** `appearance: none; 20×20; border: 2px solid var(--line-input); border-radius: 50%; background: var(--field-bg)`.
- Checked: border `--accent-fill`, `background: radial-gradient(circle, var(--accent-fill) 0 4px, var(--field-bg) 4.5px)`.

**Row states:**
- Hover: bg `--surface`.
- Checked (`.choice:has(.radio:checked)`): border `--accent-fill`, bg `--accent-tint`.
- Focus-visible on the radio: global ring.
- Keyboard: native arrow keys.

### 3.8 Pill `.pill` and role badge

**Pill:** `display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; border-radius: var(--radius-full); border: 1px solid; font: 600 var(--fs-caption)/var(--lh-caption) var(--font-body)`. Icon 14.

| Variant | fg | bg | border |
|---|---|---|---|
| `--success` | `--success-fg` | `--success-bg` | `--success-line` |
| `--warning` | `--warning-fg` | `--warning-bg` | `--warning-line` |
| `--danger` | `--danger-fg` | `--danger-bg` | `--danger-line` |
| `--info` | `--info-fg` | `--info-bg` | `--info-line` |
| `--neutral` | `--text-muted` | `--bg` | `--line-strong` |

**Fixed uses:**

| Word | Variant | Icon |
|---|---|---|
| Standard wording | neutral | `i-check` |
| Customized | success | `i-pencil` |
| Unsaved | warning | `i-circle-alert` |
| Asked | success | `i-check` |
| Not asked | neutral | `i-x` |
| In use | success | `i-circle-check` |

Calendar status words are listed in §3.9.

**Role badge `.sms__badge`:** 13/16 600 uppercase, 0.05em tracking, padding 0 4px.
- Colours: `--badge-customer`, `--badge-textback` or `--badge-you`.
- Words: "Customer", "TextBack", "You".

### 3.9 Status block `.status` (calendar, 5 variants)

**Box:** `background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-md); padding: var(--card-pad); display: grid; gap: 12px`.

**Rows, in order:**
1. Pill.
2. `h2.status__title` (Title 22/28).
3. `p.status__detail` (17/26 ink, `strong` 600).
4. Optional `dl.status__meta`: `display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; padding-top: 12px; border-top: 1px solid var(--line)`. `dt` is 15/22 muted; `dd` is 15/22 600 ink `.tnum`.
5. Optional actions row (flex, wrap, 12px gap).

The block carries `data-status`.

| `data-status` | Pill (variant, icon, word) | Title (preserved) | Detail (preserved) | Meta |
|---|---|---|---|---|
| `ready` | success, `i-calendar-check`, "Connected" | Connected to Google Calendar | Google Calendar is connected. Appointments are checked against and booked on **{label}**. | Calendar: {label}; Provider: Google |
| `reauth_required` | warning, `i-triangle-alert`, "Paused" | Reconnect needed | Google has disconnected the calendar. Bookings are paused until you reconnect. | Bookings: Paused |
| `unavailable` | danger, `i-circle-x`, "Error" | The calendar could not be read | The calendar connection could not be read. Reconnect to resume bookings. | Bookings: Paused |
| `none` (stub) | info, `i-flask-conical`, "Test mode" | Test mode: no calendar connected | No real calendar is connected (test mode). Bookings are not recorded anywhere yet. | Bookings: Not recorded |
| `managed` | success, `i-user-check`, "Connected" | {Provider} calendar connected | Your {provider} calendar is connected and managed by your operator. | Managed by: Your operator |

### 3.10 Stepper `.stepper` (2 steps)

```html
<ol class="stepper" aria-label="Change your mobile">
  <li class="stepper__step is-done"><span class="stepper__dot"><svg i-check/></span><span class="stepper__label"><span class="vh">Done: </span>Details saved</span></li>
  <li class="stepper__step is-current" aria-current="step"><span class="stepper__dot tnum">2</span><span class="stepper__label">Confirm the new number</span></li>
</ol>
```

**Layout:** `display: flex; align-items: flex-start; gap: 0`. Each step is a column (dot, then label, 8px gap) with `flex: 1`.
- The connector is `.stepper__step + .stepper__step::before`: a 2px line, `--accent-fill`, joining the dots, running from dot centre to dot centre, positioned at `top: 13px`.

**Dot:** 28×28 circle.

| Step | Dot | Label |
|---|---|---|
| Done | bg `--accent-fill`, check icon 16 `--on-accent` | 15/22 500 muted |
| Current | `border: 2px solid var(--accent-fill)`, bg `--bg`, number 13/18 600 `--accent` | 15/22 600 ink |

Both steps stay on one row at 375. Labels may wrap to two lines.

### 3.11 Notice `.notice` (inline banners and error summary)

**Box:** `display: grid; grid-template-columns: 20px 1fr; gap: 12px; padding: 12px 16px; border: 1px solid var(--{status}-line); border-left: 4px solid var(--{status}-fg); border-radius: var(--radius-md); background: var(--{status}-bg)`.
- Icon 20 in `--{status}-fg`, `margin-top: 3px`.
- Text 16/24 ink. Optional title 17/26 600.
- The 4px left bar echoes the brand's human-gate card.

**Variants:**

| Variant | Icon | Role | Used for |
|---|---|---|---|
| `--info` | `i-info` | `status` | Not-editable message, can't-connect note |
| `--warning` | `i-triangle-alert` | `status` | Not used in v1, styleguide only |
| `--danger` | `i-circle-alert` | `alert` | Page errors (calendar errors, "Message editing is not set up for this account yet.") |
| `--success` | `i-circle-check` | `status` | No-JS fallback rendering of a toast |

**Error summary `.notice--danger.error-summary`:**
- `id="error-summary" role="alert" tabindex="-1"`, placed directly under the page header.
- Links: `--danger-fg`, 600, underline, offset 3px.
- With JS, it is focused on load (`preventScroll: false`).
- Focus ring: global ring, offset 2.

### 3.12 Inline error `.field-error`

`display: grid; grid-template-columns: 18px 1fr; gap: 8px; font: 600 var(--fs-small)/var(--lh-small) var(--font-body); color: var(--danger-fg)`, with icon `i-circle-alert`. Always has an `id` and is referenced by the control's `aria-describedby`.

### 3.13 Toast `.toast`

**Without JS**, the server renders the notice at the top of `main` as `.notice--success` (or `--info`) with `role=status` and `data-toast`. It stays there.

**With JS**, it is moved into `.toast-region` and gets `.toast--floating`:
- Region: `position: fixed; z-index: var(--z-toast); top: calc(env(safe-area-inset-top) + 12px); left: var(--gutter); right: var(--gutter)`. At ≥1024: `left: auto; right: 24px; width: 400px`.
- Floating toast: `background: var(--raised); border: 1px solid var(--line); border-left-width: 1px; border-radius: var(--radius-lg); box-shadow: var(--shadow-bar); padding: 12px 8px 12px 16px; grid-template-columns: 20px 1fr auto 44px`.
- Contents: icon in status colour, text 16/24 ink, optional ghost action (for example "Undo"), close `.icon-btn` with `i-x` and "Dismiss" as visually hidden text.

**Timing:**
- Enter: opacity 0→1 and translateY(-8px)→0, over `--dur-slow` with `--ease-out`.
- Exit: the reverse, over `--dur-base` with `--ease-in`, then the toast is removed.
- Auto-dismiss after 6000ms; the Undo toast lasts 8000ms.
- The timer pauses while the toast is hovered or has focus, and restarts at 3000ms afterwards.
- Escape inside the toast dismisses it.
- Only one toast at a time; a new one replaces the old.

**Announcement:** 150ms after load, JS copies the toast text into `#announcer`. Errors are never toasts.

### 3.14 Placeholder chip `.chip`

**Container `.chips`:** `display: flex; flex-wrap: wrap; align-items: center; gap: 8px`. It starts with the label `<span class="eyebrow eyebrow--muted">Insert</span>`.
- The container has the `hidden` attribute in the server HTML; JS removes it.
- The no-JS fallback `p.chips-fallback` (shown only under `.no-js`) uses 15/22 muted text.

**Chip:** `<button type=button class=chip data-insert="{business_name}"><svg i-plus/>Business name<span class=vh> placeholder</span></button>`.
- `display: inline-flex; align-items: center; gap: 6px; height: 44px; padding: 0 12px; border-radius: var(--radius-full); background: var(--surface); border: 1px solid var(--line-strong); color: var(--text-ink); font: 500 var(--fs-small)/1.25rem var(--font-body)`. The plus icon is 16px in `--accent`.
- Height drops to 36 under `(hover: hover) and (pointer: fine)`.
- Hover bg `--sunken`, pressed bg `--line`, global focus ring.

**Insert behaviour:**
1. Focus the textarea.
2. `document.execCommand('insertText', false, token)`, which keeps native undo. If it returns false, use `setRangeText(token, start, end, 'end')`.
3. Dispatch `input`.

**Plain names:**

| Token | Chip text |
|---|---|
| `{business_name}` | Business name |
| `{service}` | Job |
| `{when}` | Day and time |
| `{location}` | Address |
| `{calendar_links}` | Add-to-calendar links |
| `{links_page}` | Links page |
| `{google_link}` | Google Calendar link |
| `{outlook_link}` | Outlook link |
| `{ical_link}` | iCal link |
| `{invite_line}` | Invite sentence |
| `{invited_email}` | Customer email |
| `{event_id}` | Calendar event ID |
| `{contact_line}` | Contact number sentence |

Chips appear in `sorted(PLACEHOLDERS[key])` order, which means token-name order. `opt_out_suffix` has no chips.

### 3.15 Segment meter `.count` + `.pips`

`<span class="count tnum" data-count>134 characters · 3 texts</span><span class="pips" data-pips aria-hidden="true"><i></i><i></i><i></i></span>`

- Count text is 13/18 500 `--text-muted`.
- Pips: each 10×6, `border-radius: 2px`, bg `--text-muted`, 3px gap. Render `min(k, 5)` pips, plus a "+" caption when k > 5.
- The non-GSM suffix " (symbols like — shorten each text)" stays part of the count string, exactly as `_count_label` produces it. The meter row may wrap.
- No colour judgement on segment counts: the shipped default intro is itself 3 texts.

### 3.16 SMS bubble `.sms`, thread pills, handoff divider

**Item** (`div.sms.sms--{customer|textback|you}` in cards, `li` in the rail): `display: flex; flex-direction: column; gap: 4px`.
- Customer: `align-items: flex-start`.
- TextBack and You: `align-items: flex-end`.

**Bubble `.sms__bubble`:**
- `max-width: 88%` in cards, 85% in the rail.
- Padding 10px 14px in cards (16/22 text); 8px 12px in the rail (15/22 → 15/20).
- `border-radius: var(--radius-bubble)`, with the tail corner `var(--radius-tail)`: bottom-left for customer, bottom-right for TextBack and You.
- `overflow-wrap: anywhere; white-space: normal`.
- Colours from the bubble tokens. The customer bubble gets `border: 1px solid var(--bubble-customer-line)`.

**Thread pill `.tpill`:** `align-self: center; display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 12px; border-radius: var(--radius-full); font: 500 var(--fs-caption)/var(--lh-caption) var(--font-body)`.

| Variant | Style |
|---|---|
| `--missed` | bg `--surface`, border `--line`, fg `--text-muted`, `::before` 6px dot in `--missed` |
| `--neutral` | same, no dot, optional 14px icon (`i-clock`, `i-bell`, `i-ellipsis`) |
| `--booked` | bg `--accent-tint`, fg `--accent`, 600, `i-check` 14 |

**Handoff divider `.handoff`:** `display: flex; align-items: center; gap: 12px; font: 600 var(--fs-caption)/1rem var(--font-body); text-transform: uppercase; letter-spacing: var(--tr-caps); color: var(--text-ink)`. `::before` and `::after` are `flex: 1; border-top: 1px dashed var(--line-strong)`.

**Rail sync highlight:** `.sms__bubble[data-current]` gets `outline: 2px solid var(--focus); outline-offset: 2px`.

**Typing indicator:** the brand's three dots, Play only (§5).

The **You** role is defined and shown in the styleguide but not used in the rail. TextBack does not relay owner texts today, so showing one would be untrue.

### 3.17 Phone frame rail `.rail`

```html
<aside class="rail" id="conversation" aria-labelledby="rail-title" data-rail>
  <h2 class="rail__title" id="rail-title">Conversation preview</h2>
  <fieldset class="scenarios"><legend class="vh">Show conversation</legend>
    <input class="vh-input" type="radio" name="scenario" id="sc-booked" value="booked" checked><label class="scenario" for="sc-booked">Books a job</label>
    … sc-retry, sc-noreply, sc-failed, sc-needsyou, sc-safety, sc-keywords …
  </fieldset>
  <div class="phone" role="group" aria-label="Sample text conversation with {business}">
    <div class="phone__screen">
      <div class="phone__head"><span class="phone__avatar" aria-hidden="true">OP</span>
        <div><p class="phone__name">{business}</p><p class="phone__sub">Text message</p></div></div>
      <div class="phone__log" tabindex="0" aria-label="Messages" data-rail-log>
        <ol class="thread" data-scenario="booked" aria-label="Books a job">…</ol> … one per scenario …
      </div>
    </div>
  </div>
  <div class="phone__foot"><p>Sample conversation · nothing is sent · names invented</p>
    <button type="button" class="btn btn--ghost btn--sm" data-play hidden>Play</button></div>
</aside>
```

**Title:** Heading role (Archivo 18/24), rendered as `h2`.

**Scenario switcher:**
- `.scenarios`: `display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 16px; border: 0; padding: 0`.
- `.vh-input`: visually hidden but focusable.
- `.scenario`: `display: inline-flex; align-items: center; height: 44px; padding: 0 14px; border-radius: var(--radius-full); border: 1px solid var(--line-strong); background: var(--bg); color: var(--text-ink); font: 500 var(--fs-small)/1.25rem var(--font-body); cursor: pointer`. Height is 36 under a fine pointer.
- Checked (`.vh-input:checked + .scenario`): bg `--accent-tint`, border `--accent-line`, fg `--accent`, 600.
- Focus (`.vh-input:focus-visible + .scenario`): global ring.
- Hover: bg `--sunken`.

**Frame and screen:**
- `.phone`: `background: var(--phone-frame); border: 1px solid var(--line); border-radius: var(--radius-phone); padding: 12px; box-shadow: var(--shadow-phone); width: 100%; max-width: 24rem; margin-inline: auto`. At ≥1024: `flex: 1 1 auto; min-height: 18rem; display: flex`.
- `.phone__screen`: `background: var(--phone-screen); border: 1px solid var(--line); border-radius: var(--radius-screen); overflow: hidden; display: flex; flex-direction: column; flex: 1`.
- `.phone__head`: `display: flex; gap: 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line)`.
  - Avatar: 32 circle, bg `--accent-tint`, fg `--accent`, 13px 600.
  - Name: 15/20 600, ellipsis.
  - Sub-line: 13/18 muted.
- `.phone__log`: `padding: 16px; overflow-y: auto; overscroll-behavior: contain; height: 30rem` below 1024; `flex: 1; height: auto` at ≥1024. Focus ring is inset (`outline-offset: -2px`).
- `.thread`: `list-style: none; margin: 0; padding: 0; display: none; flex-direction: column; gap: 12px`.

**Scenario visibility:**
- Default: `.thread[data-scenario="booked"] { display: flex }`.
- With `:has()`, for each id: `.rail:has(#sc-retry:checked) .thread { display: none } .rail:has(#sc-retry:checked) .thread[data-scenario="retry"] { display: flex }`.
- JS also sets `data-active` on the rail, so browsers without `:has()` still switch.

**Optional-question items** carry `data-ask="phone"` or `data-ask="email"`. They hide with `body:has(#ask_phone:not(:checked)) [data-ask="phone"] { display: none }` (and the email equivalent). This works without JS.

**Foot:** `display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 12px`. Caption 13/18 muted.

**Scenarios** (customer lines are sample text, owned by this spec; TextBack lines are `data-preview="{key}"` bubbles):

| id | Label | Sequence |
|---|---|---|
| `booked` | Books a job | missed pill "Missed call · just now" → intro → C "Yes, I need some tree work." → prompt_service → C "Tree removal. An oak is leaning toward the house." → prompt_location → C "12 Elm St" → prompt_preferred_time → C "Thursday at 4" → prompt_name → C "Alex Rivera" → [phone] prompt_phone → C "YES" → [email] prompt_email → C "alex@example.com" → booking_confirmation → booked pill "Booked · on your calendar" |
| `retry` | Second try | neutral pill "After the job and address" → prompt_preferred_time → C "Sometime next week" → preferred_time_reprompt → C "Wednesday at 10" → prompt_name → C "Alex Rivera" → [phone] prompt_phone → C "Use my work phone" → phone_reprompt → C "YES" → [email] prompt_email → C "alex at example" → email_reprompt → C "alex@example.com" → slot_unavailable → C "Thursday at 4" → booking_confirmation → booked pill |
| `failed` | Calendar error | neutral pill "After all the questions" → prompt_name → C "Alex Rivera" → booking_error → neutral pill "No booking was made" |
| `noreply` | No reply | missed pill → intro → neutral pill (`i-clock`) "No reply" → followup_1 → neutral pill (`i-clock`) "Still no reply" → followup_2 → neutral pill "Texts stop here" |
| `needsyou` | Needs you | prompt_preferred_time → C "Can I just talk to the owner about pricing?" → handoff_ack → handoff divider "You take it from here" → neutral pill (`i-bell`) "You get a lead with this conversation" |
| `safety` | Safety | prompt_location → C "A big limb just came down on the power line by our house" → handoff_ack_safety → handoff divider → neutral pill (`i-bell`) "You get an urgent lead" |
| `keywords` | Keywords | C "START" → opt_in → C "HELP" → help → C "STOP" → opt_out_ack |

In `retry`, the time "Wednesday at 10" is the one that is taken. That keeps the confirmation's sample time (Thursday, Oct 22 at 4:00 PM) truthful. `opt_out_suffix` appears appended inside the intro, follow-ups, START and HELP bubbles.

**Card-to-scenario map** for focus sync:

| Keys | Scenario |
|---|---|
| intro, prompt_*, booking_confirmation, opt_out_suffix | `booked` |
| preferred_time_reprompt, phone_reprompt, email_reprompt, slot_unavailable | `retry` |
| booking_error | `failed` |
| followup_1, followup_2 | `noreply` |
| handoff_ack | `needsyou` |
| handoff_ack_safety | `safety` |
| opt_in, help, opt_out_ack | `keywords` |

### 3.18 Sticky save bar `.savebar`

```html
<div class="savebar" data-savebar data-state="nojs">
  <p class="savebar__status" data-savebar-status></p>
  <div class="savebar__actions">
    <button type="button" class="btn btn--ghost" data-show-error hidden>Show</button>
    <button type="button" class="btn btn--danger-ghost" data-discard hidden>Discard</button>
    <button type="submit" class="btn btn--primary" name="save" value="1" data-save aria-keyshortcuts="Control+S Meta+S">Save changes</button>
  </div>
</div>
```

**Box:** `display: flex; align-items: center; justify-content: space-between; gap: 8px 12px; min-height: 64px; margin-top: var(--space-8); padding: 8px 8px 8px 16px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: var(--raised)`.
- Status text 16/22 600 ink, `.tnum`, with an 18px icon.
- `.savebar__status` has `aria-live="polite"`. JS writes to it, debounced by 800ms.

**Sticky rule:** `position: sticky; z-index: var(--z-savebar); box-shadow: var(--shadow-bar)`.
- Bottom offset below 1024: `bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + var(--space-2))`.
- Bottom offset at 1024 and up: `bottom: var(--space-4)`.

| `data-state` | When | Position | Status (phone / ≥640) | Buttons |
|---|---|---|---|---|
| `nojs` | No JS (server default) | sticky | empty | Save changes |
| `clean` | JS, nothing differs from saved | static, no shadow | `i-circle-check` muted, "All changes saved" | Save changes, `aria-disabled` |
| `saved` | First 4000ms after a successful POST, then becomes `clean` | static | `i-circle-check` in `--accent`, "All changes saved" | Save changes, `aria-disabled` |
| `dirty` | One or more cards or switches differ | sticky; enters with translateY(12px)→0 and opacity, over `--dur-slow` | "{N} unsaved" / "{N} unsaved change(s)" | Discard, Save changes |
| `error` | After a rejected POST, until the offending textarea changes | sticky | `i-circle-alert` danger, "Not saved" / "Not saved · 1 message needs a change" | Show (focuses the offending textarea), Save changes |
| `saving` | After submit | sticky | `i-loader-circle` spinning, "Saving…" | Save changes loading ("Saving…"), others hidden |

**Counting N:** count cards where `norm(textarea.value || data-default) !== norm(data-saved)`, plus switches whose `checked` differs from `data-saved-checked`. `norm` collapses whitespace and trims.

**Discard:**
1. Restore every textarea to `data-saved` and every switch to its saved state.
2. Re-render previews.
3. Set state to `clean`.
4. Show the Undo toast "Changes discarded." and move focus to its Undo button.
5. Undo restores the discarded values and moves focus to Save changes.

### 3.19 Account menu `details.menu`

**Trigger:** `<summary class="menu__trigger icon-btn">` containing `i-circle-user-round` (22), `<span class="vh">Account</span>` and `i-chevron-down` (16).
- `min-width: 44px; padding: 0 8px; gap: 4px`.
- Hide the native marker: `list-style: none`, plus `::-webkit-details-marker { display: none }`.
- Open: bg `--sunken`, chevron rotated 180°.

**Panel `.menu__panel`:** `position: absolute; right: 0; top: calc(100% + 8px); width: min(18rem, calc(100vw - 2 * var(--gutter))); z-index: var(--z-popover); background: var(--raised); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-pop); padding: 8px`. `details.menu` is `position: relative`.

**Panel contents:**
1. **Who:** `padding: 8px 12px 12px; border-bottom: 1px solid var(--line)`. Business name 16/22 600, then "Signed in with (980) 555-0123" 15/22 muted `.tnum`.
2. **Appearance:** `data-theme-picker`, `hidden` until JS removes it. Padding 12. Eyebrow "Appearance", then three radio pills (same component as `.scenario`), `name=theme`, values `system`, `light`, `dark`. Light shows `i-sun`, Dark shows `i-moon`, System has no icon.
   - On change, set the cookie `tb_theme=light|dark` (path=/client, SameSite=Lax, max-age=31536000, not httponly), or delete it for System.
   - Apply `document.documentElement.dataset.theme` immediately.
3. **Sign out:** `<form method=post action=/client/logout>` with the CSRF input and `<button type=submit class="menu__item"><svg i-log-out/>Sign out</button>`.
   - `.menu__item`: `width: 100%; height: 44px; display: flex; gap: 12px; align-items: center; padding: 0 12px; border-radius: var(--radius-md); font: 500 16px/22px; color: var(--text-ink)`. Icon 18 muted. Hover bg `--sunken`.

**Motion:** the panel enters with opacity 0→1 and scale 0.98→1 from the top right, over `--dur-base`.

**JS:**
- Escape closes and returns focus to the summary.
- A click outside closes it.
- `focusout` to outside the menu closes it.

### 3.20 Nav item `.nav__item`

**Item:** `color: var(--text-muted); text-decoration: none`. `.nav__icon`: 56×32, `border-radius: var(--radius-full)`, grid centred, icon 24. Label 13/16 500.

| State | Style |
|---|---|
| Hover | fg `--text-ink`; icon wrapper bg `--sunken` |
| Pressed | icon wrapper bg `--line` |
| Active (`aria-current=page`) | fg `--accent`; label 600; icon wrapper bg `--accent-tint` with `box-shadow: inset 0 0 0 1px var(--accent-line)` |
| Active pressed | `--accent-tint-hover` |
| Focus-visible | `outline: 2px solid var(--focus); outline-offset: -4px` |

### 3.21 Page header `.page-head`

`display: grid; gap: 8px; margin-bottom: var(--space-8)`. Contents:
- `h1`: Display, `letter-spacing: var(--tr-display)`.
- `p.lead`: 18/28 muted, `max-width: 60ch`.
- Optional `p.page-head__meta`: 15/22 `--text-subtle` with a 16px `i-info` icon.
- Optional jump link.

### 3.22 Moments and spine

```html
<ol class="moments" aria-label="The conversation, in order">
  <li class="moment" id="g_missed" aria-labelledby="h_missed">
    <span class="moment__node moment__node--missed" aria-hidden="true"><svg><use href="#i-phone-missed"/></svg></span>
    <div class="moment__head"><h2 id="h_missed">Missed call</h2><p>A call goes unanswered. …</p></div>
    <div class="moment__cards">…cards…</div>
  </li>
  …
</ol>
```

**Container:** `.moments { list-style: none; margin: 0; padding: 0; position: relative; display: grid; gap: var(--moment-gap); }`

**Spine line:** `.moments::before { content: ""; position: absolute; left: calc(var(--spine-col) / 2 - 1px); top: calc(var(--spine-node) / 2); bottom: 0; width: 2px; background: var(--spine); }`

**Moment grid:** `.moment { display: grid; grid-template-columns: var(--spine-col) minmax(0, 1fr); column-gap: var(--spine-gap); row-gap: var(--space-4); }`
- `.moment__node` is grid-column 1, row 1. `.moment__head` and `.moment__cards` are grid-column 2.

**Node:** `.moment__node { position: relative; z-index: var(--z-node); width: var(--spine-node); height: var(--spine-node); border-radius: 50%; background: var(--bg); border: 1px solid var(--line-strong); display: grid; place-items: center; color: var(--text-muted); font-size: var(--spine-icon); margin-top: 2px; }`

**Missed node:** the icon colour is ink. `::after` is the brand red dot: `width: 10px; height: 10px; border-radius: 50%; background: var(--missed); box-shadow: 0 0 0 2px var(--bg); position: absolute; top: -2px; right: -2px`.

**Node icons:**

| Moment | Icon |
|---|---|
| Missed call | `i-phone-missed` |
| The questions | `i-message-circle-question` |
| Booking | `i-calendar-check` |
| No reply | `i-clock` |
| You step in | `i-hand` |

**Head:** `h2` is Title 22/28. The blurb is 15/22 muted.

**Cards:** `.moment__cards { display: grid; gap: var(--card-gap); }`. A parent card and its branches form one `.qset { display: grid; gap: var(--space-2); }`.

**"Optional questions":** `p.eyebrow.eyebrow--muted` inside `.moment__cards` before the optional `.qset`s, `margin-top: 8px`.

**Any time section:** `section.anytime` comes after `.moments`. `margin-top: var(--moment-gap)`, no node, no spine, cards full column width. Contents: eyebrow "Any time" (accent) → `h2` → blurb → `.anytime__cards` (grid, `--card-gap`).

### 3.23 Message card `.msg`

```html
<article class="msg{ msg--branch}{ msg--optional}{ msg--invalid}" id="m_{key}" data-card="{key}"
         data-default="{DEFAULT}" data-saved="{effective saved text}" data-optout="{1|0}" aria-labelledby="l_{key}">
  <header class="msg__head">
    <h3 class="msg__label" id="l_{key}">{label}</h3>
    <p class="msg__when" id="w_{key}">{when}</p>
  </header>
  <div class="msg__status">
    <span class="pill pill--neutral|pill--success" data-state-pill>…Standard wording|Customized</span>
    <span class="pill pill--warning" data-dirty-pill hidden><svg i-circle-alert/>Unsaved</span>
    <button type="submit" name="reset" value="{key}" class="btn btn--ghost" data-reset {hidden if standard}>
      <svg i-rotate-ccw/>Use standard wording<span class="vh"> for {label}</span></button>
  </div>
  {optional} <label class="switch-row" for="ask_{field}">…</label>
  {rule}     <p class="msg__rule" id="r_{key}"><svg i-shield-check/>{rule}</p>
  <div class="well msg__preview">
    {trigger}  e.g. <div class="sms sms--customer"><span class="sms__badge">Customer</span><p class="sms__bubble">Sometime next week</p></div>
    <div class="sms sms--textback"><span class="sms__badge">TextBack</span><p class="sms__bubble" data-preview="{key}">{rendered}</p></div>
    {after}    e.g. <p class="tpill tpill--booked">…Booked · on your calendar</p>
  </div>
  {optional} <p class="msg__off">Not asked right now. Switch it on to add this question.</p>
  <div class="msg__meta">
    {optout}  <a class="msg__optout" href="#m_opt_out_suffix" data-optout-note {hidden if not appended}>Opt-out line added</a>
    <span class="msg__countwrap"><span class="count tnum" data-count>…</span><span class="pips" data-pips aria-hidden="true">…</span></span>
  </div>
  <details class="editor" {open if invalid}>
    <summary class="editor__summary"><svg i-pencil/>Edit wording<span class="vh">: {label}</span><svg class="editor__chev" i-chevron-down/></summary>
    <div class="editor__body">
      {invalid} <p class="field-error" id="e_{key}"><svg i-circle-alert/>Not saved: {reason}</p>
      <label class="vh" for="f_{key}">Wording for {label}</label>
      <textarea class="textarea" id="f_{key}" name="{key}" maxlength=480 rows=4 data-autogrow
                aria-describedby="x_{key}{ r_{key}}{ e_{key}}"{ aria-invalid=true}>{effective text}</textarea>
      <p class="field-help" id="x_{key}">Texts are sent as one paragraph. Leave it empty to use the standard wording.</p>
      <div class="chips" data-chips hidden>…</div>
      <p class="chips-fallback">Words in curly brackets are filled in for you. This message can use: {business_name} (Business name).</p>
      <p class="limit tnum" data-limit hidden>412 of 480 characters</p>
    </div>
  </details>
</article>
```

**Card box:** `.msg { position: relative; display: grid; gap: var(--space-3); padding: var(--card-pad); background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-md); scroll-margin-top: var(--space-6); }`

**Parts:**
- `.msg__label`: Archivo 600 18/24.
- `.msg__when`: 15/22 muted.
- `.msg__status`: `display: flex; flex-wrap: wrap; align-items: center; gap: 8px`.
- `.msg__rule`: `display: grid; grid-template-columns: 16px 1fr; gap: 8px`, 15/22 muted; the icon is muted with `margin-top: 3px`.
- `.well`: `background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2)`.
- `.msg__meta`: `display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 4px 12px`. With no opt-out link: `justify-content: flex-end`.
- `.msg__optout`: 15/22 600 accent.
- `.editor`: `margin: 0 calc(-1 * var(--card-pad)) calc(-1 * var(--card-pad)); padding: 0 var(--card-pad); border-top: 1px solid var(--line)`.
- `.editor__summary`: `min-height: var(--tap); display: flex; align-items: center; gap: 8px; color: var(--accent); font: 600 16px/22px var(--font-body); cursor: pointer; list-style: none`. The chevron sits at `margin-left: auto` and rotates 180° when open (`--dur-base`).
- `.editor__body`: `display: grid; gap: 12px; padding-bottom: var(--card-pad)`.

**What the editor shows:**
- **Effective text:** the textarea always renders the wording in force, meaning the custom text, or the default when there is none. It is never blank-with-placeholder, so the owner edits real words rather than retyping.
- **Customized:** shown when `norm(value) !== '' && norm(value) !== norm(default)`.
- **Empty value:** counts as Standard wording, and the bubble shows the default.
- **Limit counter:** shown only when `value.length >= 420`. It uses `--warning-fg` at ≥ 460.
- **Trigger and after items** in the well (same samples as the rail):

| Key | In the well |
|---|---|
| intro | missed pill "Missed call · just now" |
| preferred_time_reprompt | customer bubble "Sometime next week" |
| phone_reprompt | customer bubble "Use my work phone" |
| email_reprompt | customer bubble "alex at example" |
| slot_unavailable | customer bubble "Wednesday at 10" |
| booking_confirmation | booked pill after the bubble |
| followup_1 | "No reply" pill before |
| followup_2 | "Still no reply" pill before, "Texts stop here" pill after |
| handoff_ack | customer bubble "Can I just talk to the owner about pricing?" before |
| handoff_ack_safety | customer bubble "A big limb just came down on the power line by our house" before |
| opt_in | customer bubble "START" before |
| help | customer bubble "HELP" before |
| opt_out_ack | customer bubble "STOP" before |

**Card states:**

| State | Visual |
|---|---|
| Standard | neutral pill; reset hidden |
| Customized | success pill; reset visible |
| Dirty (`data-dirty`) | Unsaved pill visible (JS) |
| Focus-within | border `--line-strong`; rail sync (≥1024) |
| Invalid (`msg--invalid`) | `border-color: var(--danger-line); box-shadow: inset 4px 0 0 var(--danger-fg)`; editor open; field-error above the textarea; textarea `aria-invalid` |
| Optional, switched off | `.msg--optional:has(.switch:not(:checked))` hides `.msg__preview` and `.msg__meta` and shows `.msg__off` (15/22 muted). `.qset:has(> .msg--optional .switch:not(:checked)) > .msg--branch { display: none }`. Textareas stay in the DOM and are still posted |
| Branch (`msg--branch`) | `margin-left: var(--branch-indent)`. The elbow `::before` is `position: absolute; left: calc(-1 * var(--branch-indent) + 4px); top: calc(-1 * var(--space-2) - 1px); width: calc(var(--branch-indent) - 6px); height: calc(var(--space-2) + 30px); border-left: 2px dashed var(--line-strong); border-bottom: 2px dashed var(--line-strong); border-bottom-left-radius: 6px` |
| Read-only (not editable) | no form, no editor, no reset; switch replaced by an Asked or Not asked pill |

**Card loading and skeleton:** none. Cards are server-rendered.

### 3.24 Skeleton `.skeleton`

`background: var(--sunken); border-radius: var(--radius-sm)`. Text lines are 12px tall; blocks get an explicit height.
- Shimmer: a `linear-gradient(90deg, transparent, color-mix(in srgb, var(--bg) 60%, transparent), transparent)` sweep over 1200ms linear, infinite.
- Under reduced motion: static.
- **Not used on any v1 page**, because every page is server-rendered with its data. It exists in the styleguide, reserved for future async content.

### 3.25 Empty state `.empty`

`display: grid; justify-items: start; gap: 8px; padding: var(--card-pad); border: 1px dashed var(--line-strong); border-radius: var(--radius-md)`.
- Icon 24 in a 48 circle, bg `--sunken`, fg `--text-muted`.
- Title 17/26 600. Body 15/22 muted. Optional action.

Uses in v1:
- Calendar ready with exactly one choice: icon `i-calendar-days`, title "{label}", body "This is the only calendar this account can add appointments to."
- Calendar ready with zero choices: the picker is omitted entirely.

### 3.26 Card `.card` (Business form, picker, "What Google will ask")

`background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-md); padding: var(--card-pad); display: grid; gap: var(--space-4)`. Cards on a page are separated by 24px. Card headings use the Heading role.

### 3.27 Skip link `.skip`

Visually hidden until focused. Then `position: fixed; top: 8px; left: 8px; z-index: var(--z-skip); background: var(--raised); padding: 8px 12px; border-radius: var(--radius-md); box-shadow: var(--shadow-pop)`.

---

## 4. Screens

Shared rules:
- Every page keeps `Cache-Control: no-store`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`.
- Signed-in pages carry the topbar, nav and account menu.
- Auth pages carry the topbar with brand only.

### 4.1 Sign in (`GET/POST /client/login`)

**Structure (`.auth`, top to bottom):**
1. Eyebrow "Scheduling assistant settings".
2. H1 `{business_name}`.
3. Lead (24 below).
4. `<form method=post action=/client/login>` with `.field`:
   - Label "Business mobile" for `mobile`.
   - `input#mobile.input.input--tel`: `name=mobile type=tel autocomplete=tel inputmode=tel required maxlength=24 placeholder="704 555 0123"`.
5. `.btn--primary.btn--lg.btn--block` "Text me a code" (16 below the field).
6. Footer caption "TextBack by FluxWorks" (40 below).

**Error:** "Enter the mobile number as digits, like 704 555 0123." renders as `.field-error#mobile-error`. The input gets `aria-invalid=true aria-describedby=mobile-error autofocus`. No error summary on a one-field form.

**Loading:** the button shows "Sending code…" with a spinner. The 303 to `/client/verify` follows.

**Focus order:** skip link → brand → mobile → submit.

**At 1024:** identical; the column is centred 96px below the header.

### 4.2 Enter code (`GET/POST /client/verify`)

**Structure:**
1. Eyebrow `{business_name}`.
2. H1 "Check your phone".
3. Lead.
4. `<form method=post action=/client/verify>`: label "Sign-in code" for `code`, then the OTP field (§3.5) with `autofocus`.
5. Primary lg block "Sign in".
6. Link "Didn't get it? Send a new code" to `/client/login` (16 below, 44 tall, 600 accent).

**Error:** CODE_FAILURE renders as `.field-error#code-error` below the cells, with `aria-invalid` and autofocus. The value is not re-filled.

**Loading:** "Signing in…".

**Hard rules:**
- No business number, owner number or masked digits.
- No `0123` anywhere, so the placeholder is absent.
- The response does not vary with the submitted number.

**Focus order:** skip → brand → code → Sign in → Send a new code.

### 4.3 Messages (`GET/POST /client/messages`)

**Order, phone first:**
1. `.page-head`:
   - H1 "Your messages".
   - Lead.
   - Meta line "Previews fill in sample details, like tree removal at 12 Elm St."
   - Below 1024 only, the jump link "See the whole conversation" (`href=#conversation`, with `i-chevron-down`).
2. If error: the error summary (§3.11), focused on load. Its link targets `#f_{bad_key}`. With JS, clicking it opens the editor, focuses the textarea and puts the caret at the end. Without JS, the anchor scroll works because the editor renders open.
3. If not editable: `.notice--info` "Message editing is not set up for this account yet. Ask your operator to enable it." Then everything renders read-only and there is no form element. The rail still renders.
4. `.msg-layout`, containing:
   - The `form#messages.msg-list`: CSRF, the hidden save button, then `ol.moments`, then `section.anytime`, then `.savebar`.
   - `aside.rail`.

**Spine content** (the structure lives in a new Python `LAYOUT` constant; `GROUPS` stays untouched for other callers):

| Moment (`id`, H2, node) | Blurb (preserved) | Cards |
|---|---|---|
| `g_missed` "Missed call" `i-phone-missed` + red dot | A call goes unanswered. Within seconds the caller gets this text. | intro |
| `g_questions` "The questions" `i-message-circle-question` | Asked one at a time, in this order. The assistant only moves on once it has an answer. | prompt_service; prompt_location; prompt_preferred_time (+ branch preferred_time_reprompt); prompt_name; eyebrow "Optional questions"; prompt_phone with switch `ask_phone` (+ branch phone_reprompt); prompt_email with switch `ask_email` (+ branch email_reprompt) |
| `g_booking` "Booking" `i-calendar-check` | With the answers in hand the assistant checks your calendar and books a free slot. | booking_confirmation (+ branches slot_unavailable, booking_error) |
| `g_noreply` "No reply" `i-clock` | If the customer goes quiet, two reminders. Then it stops. | followup_1; followup_2 |
| `g_owner` "You step in" `i-hand` | When a text needs you, automated scheduling pauses and you get a lead. | handoff_ack; handoff_ack_safety |
| Off spine: `g_keywords`, eyebrow "Any time", H2 "START, HELP and STOP" | Replies carriers require to the three keywords, and the opt-out line itself. | opt_in; help; opt_out_ack; opt_out_suffix |

**Branch meaning:** a dashed elbow means "sent instead, when something needs another try". So slot_unavailable and booking_error hang under the confirmation, and the reprompts hang under their question. DOM order differs from `GROUPS`. That is harmless because posting is by field name.

**Interaction notes:**
- **Typing:** on each `input`, synchronously re-render this card's bubble, count, pips, opt-out note, state pill, Unsaved pill and every rail bubble with the same `data-preview`. If the key is `opt_out_suffix`, re-render every `data-optout="1"` card. Then recompute N.
- **Rendering logic:** port the existing `MESSAGES_SCRIPT` exactly. Fill uses the sample JSON. The opt-out rule tests the *template* with `/\bstop\b/i`. Whitespace is collapsed. GSM counting is 160/153 or 70/67, with extended characters counting 2.
- **Reset (JS):**
  1. `preventDefault`, then set the value to the default and dispatch `input`.
  2. Announce "Standard wording restored for {label}." through `#announcer`.
  3. Move focus to the textarea if the editor is open, otherwise to the editor summary, because the reset button hides itself.
- **Reset (no JS):** posts `reset={key}`. The server resets that key and saves everything else submitted.
- **Edit wording open:** with JS, the textarea gets focus with the caret at the end, then auto-grows.
- **Switch:** the card collapses or expands through CSS, it counts as a change, and the rail hides or shows `data-ask` items.
- **Rail sync** (≥1024, JS only): on `focusin` inside a card, if the rail's current scenario does not contain `data-preview={key}`, check the mapped scenario's radio. Then set `data-current` on that bubble and centre it in the log with `log.scrollTo({top, behavior})`. Never use `scrollIntoView`, which would scroll the page. On `focusout` of the card, clear `data-current`. Switched-off optional keys do not sync.
- **Ctrl/Cmd+S:** submits the form when it is dirty; `preventDefault` always.
- **beforeunload:** prompts when dirty. Submit clears the flag.
- **Submit:** the save bar goes to `saving`, plus the button loading state and the double-submit guard. On the server, a whitespace-collapsed value equal to the default is stored as "" (§7).

**Focus order** (Tab through a card): switch (if any) → Use standard wording (if visible) → Opt-out line added (if shown) → Edit wording summary → [textarea → chips] when open. After the last card come Show/Discard and Save changes. The rail follows: scenario radios (one tab stop, arrow keys inside), then the log (scrollable region), then Play.

**States:**
- Success: the toast "Saved. New conversations use these messages from now on." and the save bar in `saved`.
- Rejected: the error summary, the invalid card open with the inline reason, every typed value and toggle kept, and the save bar in `error`.
- CSRF 400: currently a JSON body (see §8).
- "No messages file" POST: `.notice--danger` "Message editing is not set up for this account yet."

**At 1024:**
- The page head loses the jump link.
- The list column and rail sit side by side; the rail is sticky.
- The save bar is sticky inside the list column at bottom 16.
- Nothing else changes: same spine and same card anatomy.

### 4.4 Business (`/client/business`) and confirm step

**Business form:** `.page-head` (H1 "Your business" + lead), then the error summary if any (`.notice--danger`, focused on load). Then:

```
<form method=post action=/client/business class="page__body">
  csrf
  .card
    .field  label "Business name"; help "Used in every text customers get."; input#business_name name=business_name
            required maxlength=60 autocomplete=organization; then .well.field-preview:
            eyebrow "In the first text" + TextBack bubble (data-template = current intro template,
            data-suffix = filled opt-out suffix if intro lacks STOP else ""). JS fills {business_name}
            with the trimmed input value (or the saved name when empty) on input.
    .field  label "Number in the HELP reply" + tag "Optional"; help (preserved, see §6);
            input#business_contact.input--tel name=business_contact autocomplete=off placeholder="704 555 0123"
    .field  label "Your mobile"; help (preserved); input#owner_mobile.input--tel name=owner_mobile required autocomplete=tel
  [Save business details]  primary (block below 640)
</form>
```

**Error mapping** (server, by exact string), so the right field gets `aria-invalid`, the inline `.field-error`, and the summary link `#{field}`:

| Error string | Field |
|---|---|
| "Enter a business name of 1 to 60 characters." | `business_name` |
| "Enter the customer phone number as digits, like 704 555 0123, or leave it blank." | `business_contact` |
| "Enter your mobile as digits, like 704 555 0123." | `owner_mobile` |

The summary reads "Not saved." with the message as a link to the field. Submitted values are re-filled (already supported).

**Notices** (toasts): "Saved.", "Kept your current mobile.", "Saved. Sign-in codes now go to {fmt}."

**Loading:** "Saving…".

**Focus order:** name → HELP number → mobile → Save.

**Confirm step** (the response to a changed mobile, and to `/client/business/confirm` errors). Structure:
1. H1 "Confirm your new mobile".
2. Stepper (§3.10).
3. Lead with `<strong class=tnum>{pending formatted}</strong>`.
4. `<form method=post action=/client/business/confirm>` with CSRF and a `.card` containing the label "Code from the text" and the OTP (`autofocus`, `autocomplete=one-time-code` unquoted).
5. Primary lg "Confirm new mobile".
6. `<form method=post action=/client/business/confirm>` with CSRF and `<button class="btn btn--secondary btn--block-phone" name=cancel value=1>Keep my current mobile</button>`, 12 below.
7. `<form method=post action=/client/business>` with CSRF and hidden `business_name`, `business_contact` (both current saved values) and `owner_mobile` (= pending), containing "Didn't get it?" plus ghost "Send the code again". This re-requests the code through the existing route and rate limit.

**Confirm errors:** CODE_FAILURE renders inline under the OTP. The GET `/client/business/keep` route stays, but the UI never links to it.

**At 1024:** a 640 column; buttons are auto width and left-aligned in one row: Confirm new mobile, then Keep my current mobile.

### 4.5 Calendar (`/client/calendar`)

**Order:**
1. `.page-head`: H1 "Your calendar" + lead.
2. Page error, if any (`?error=` value, "Connecting a calendar is not set up for this account yet."): `.notice--danger role=alert`.
3. Success notice: toast "The assistant now uses {name}."
4. Status block (§3.9) with `data-status`.
5. **If status is `ready`, google, and there is more than one choice:** a picker `.card` with `<form method=post action=/client/calendar>`, CSRF, a fieldset legend "Which calendar should the assistant use?", help, the choice list (current checked, with an "In use" pill), and primary "Use this calendar".
   - "Pick one of the calendars listed." renders as `.field-error` above the list, and the fieldset gets `aria-describedby`.
   - With exactly one choice and `ready`: show the empty state from §3.25 instead.
   - With any other status: no picker.
6. **If google and can_connect:** a `.card` with heading "What Google will ask", the 4-item list (§6), and `<form method=post action=/client/calendar>` with CSRF, `<input type=hidden name=action value=connect>` and the button.
   - When `ready`: secondary "Reconnect Google Calendar", and this card comes **after** the picker.
   - When `reauth_required` or `unavailable`: primary "Connect Google Calendar" (server verb logic unchanged), and this card comes **directly after** the status block.
   - Loading label: "Opening Google…".
7. **If google and not can_connect:** `.notice--info` "Connecting a calendar from this page is still being set up by your operator."
8. **Stub and managed:** the status block only.

**Focus order:** status (static) → picker radios (one tab stop) → Use this calendar → Connect/Reconnect.

**At 1024:** a 640 column; buttons are auto width.

### 4.6 Styleguide (`GET /client/styleguide`, owner-only)

**Access and headers:**
- Session required; otherwise 303 to `/client/login`. `include_in_schema=False`.
- Same headers plus `X-Robots-Tag: noindex`. Not linked from any nav.
- Uses the real shell with nav, with no item marked current.

**Specimens:**
- No specimen form posts: every button is `type=button`, and inputs have no `name`.
- From ≥1024, each specimen section renders as two panels side by side, `<div data-theme="light">` and `<div data-theme="dark">`, each with `background: var(--bg); padding: 24px; border: 1px solid var(--line); border-radius: var(--radius-lg)`. Below 1024 they stack.

**Sections, in order** (each `h2` with an `id`; an anchor list sits at the top):

1. **Tokens: colour.** A swatch for every colour token in §1.1: name, light hex, dark hex, and the ratio against its pair from §1.3.
2. **Tokens: type.** Every role from §1.2, rendered with the sample "Oak & Pine Tree Care" and its size/line-height label.
3. **Tokens: space, radius, elevation, motion, z-index.** Bars for `--space-*`. Boxes for each radius and each shadow. A "Run" button that animates a box with each duration and easing (honours reduced motion). The z-index list as text.
4. **Icons.** All 52 sprite symbols at 24px with their ids.
5. **Buttons.** Primary, secondary, ghost, danger-ghost and icon, each in default, `.is-hover`, `.is-focus`, `.is-active`, `aria-disabled` and `.is-loading`. Sizes md, lg, sm, and block.
6. **Fields.** Text input (empty, filled, focus, invalid with error); tel (unformatted, formatted); textarea (short, auto-grown long, invalid); label + Optional tag + help + error; OTP (empty, "481", filled with "000000", invalid). The OTP specimen never contains "0123".
7. **Choices.** Switch row (off, on, focus); radio list (3 rows: main, checked "In use", hover).
8. **Status.** Pills (all 5 variants plus Standard wording, Customized, Unsaved, Asked, Not asked, In use); all 5 calendar status blocks; notices (info, warning, danger, success).
9. **Feedback.** Toast (success static, success with Undo static, plus a "Show toast" button for the live one); error summary; inline error; stepper; skeleton (text, 3 lines, and a 120px block); empty state.
10. **Conversation.** Role badges; customer, TextBack and You bubbles (card and rail sizes); missed, neutral and booked pills; handoff divider; typing indicator; segment meter for 1, 2 and 3 texts plus the non-GSM note; placeholder chips (all 13 names).
11. **Message card.** Standard; customized; dirty; invalid (open); optional off; branch under a parent; read-only.
12. **Spine.** A two-moment excerpt (missed node + one generic node, two cards, one branch) followed by an "Any time" section header.
13. **Phone rail.** The full rail with all 7 scenarios, using the live business name and the default wording.
14. **Save bar.** All 6 states rendered statically in a column (nojs, clean, saved, dirty with N=2, error, saving).
15. **Shell.** Topbar (signed in and signed out); nav items (tab bar form and sidebar form; default, hover, active, focus); account menu panel rendered open as a static copy (not a `details`); page header with lead, meta and jump link.

---

## 5. Motion and states

### 5.1 What animates

| Element | Property | Duration / easing |
|---|---|---|
| Button, chip, nav, choice row (hover/press) | background, border, colour | 120ms `--ease-out` |
| Switch thumb | transform, background | 180ms `--ease-standard` |
| Editor and menu chevrons | rotate 180° | 180ms `--ease-standard` |
| Editor body on open | opacity 0→1, translateY(4px)→0 | 180ms `--ease-out` (no height animation) |
| Account popover | opacity, scale 0.98→1 (origin top right) | 180ms `--ease-out` |
| Save bar entering `dirty` | opacity, translateY(12px)→0 | 250ms `--ease-out` |
| Save bar leaving to `clean` | none (it returns to its resting slot) | n/a |
| Toast in / out | opacity, translateY(-8px) | 250ms out / 180ms in |
| Rail scenario change | none; threads swap instantly; the log scrolls to the top | n/a |
| Rail sync | log `scrollTo` smooth; ring appears with no transition | browser smooth |
| Rail Play | brand demo timing: 400ms lead-in; typing indicator `clamp(700, chars×28, 1800)`ms; reveal 250ms rise 6px; 350ms after messages; 900ms before the handoff divider; 500ms before pills | as brand |
| Spinner | rotate 360° | 800ms linear, infinite |
| Skeleton | gradient sweep | 1200ms linear, infinite |
| Live preview text | none (instant) | n/a |

Nothing bounces, nothing moves on page load, and there are no parallax or scroll-triggered reveals.

### 5.2 Reduced motion

`@media (prefers-reduced-motion: reduce)`:
- Every transition and animation goes to `0.01ms`.
- The spinner does not rotate; the label "Saving…" carries the state.
- Skeletons are static.
- The Play button stays `hidden`, and the full thread is always shown.
- `scrollTo` uses `behavior: 'auto'`.
- Toast and save bar appear and disappear without movement.

### 5.3 JS-off behaviour

| Piece | JS off | JS on adds |
|---|---|---|
| Account menu | `details` toggles; Sign out POST works; Appearance hidden | Escape / outside click / focusout close; Appearance control |
| Theme | system preference, or the server-read `tb_theme` cookie | Appearance sets the cookie and applies it instantly |
| Nav | links | none |
| Notices | inline `.notice` at the top of main; stays | floats as a toast, auto-dismisses, announced |
| Error summary | at top; anchor links scroll (the invalid editor renders open) | focused on load; link click focuses the textarea |
| Editor | native `details`; textarea `rows=4`, resizable; Enter inserts newlines (server collapses them) | focus on open, auto-grow, Enter blocked |
| Bubble, counts, pills | server-rendered for saved or submitted text; static while typing | live |
| Reset | submit `reset={key}` (saves other submitted edits too) | local, undoable through Discard |
| Chips | hidden; fallback sentence lists the allowed tokens | insert at cursor |
| Switch | native checkbox; card collapse and rail hiding via `:has()` | counts toward unsaved |
| Save bar | sticky "Save changes" only | 6 states, Discard, Show, Ctrl/Cmd+S, beforeunload |
| Rail | server-rendered threads; scenario radios switch via `:has()` | live text, focus sync, Play, fallback switching without `:has()` |
| OTP | one input; typed or pasted (maxlength truncates) | paste sanitising, next-cell highlight |
| Tel inputs | as typed | `(AAA) BBB-CCCC` on blur |
| Submits | browser default | loading label and spinner, double-submit guard |
| Business preview bubble | server-rendered with the saved name | updates as the name is typed |
| Calendar | native radios and POSTs | "Opening Google…" loading |
| Styleguide | static specimens | live toast and motion demos |

### 5.4 Feedback timing

| Event | Timing |
|---|---|
| Pressed visual | immediate (`:active`) |
| Loading state | applied synchronously in the `submit` handler |
| Preview and count | synchronous per keystroke |
| N recount | synchronous; screen-reader announcement debounced 800ms |
| `saved` → `clean` | 4000ms |
| Success toast | 6000ms |
| Undo toast | 8000ms |
| Toast after hover or focus | resumes at 3000ms |
| Error summary focus on load | 0ms after DOMContentLoaded |
| Notice text copied to `#announcer` | 150ms |

---

## 6. Copy deck

Status column: **P** = preserved server or test string, used verbatim. **N** = new. **C** = changed from the current markup.

### 6.1 Global

| Where | String | Status |
|---|---|---|
| `<title>` | "Sign in · TextBack", "Enter code · TextBack", "Messages · TextBack", "Business · TextBack", "Confirm your new mobile · TextBack", "Calendar · TextBack", "Styleguide · TextBack" | N |
| Skip link | Skip to content | N |
| Brand | TextBack | N |
| Nav label (aria) | Settings | N |
| Nav items | Messages · Business · Calendar | N |
| Account trigger (vh) | Account | N |
| Account meta | Signed in with {owner mobile, formatted} | N |
| Appearance | Appearance · System · Light · Dark | N |
| Sign out | Sign out | N |
| Toast close (vh) | Dismiss | N |
| Auth footer | TextBack by FluxWorks | N |

### 6.2 Sign in and Enter code

| String | Status |
|---|---|
| Scheduling assistant settings (eyebrow) | P |
| {business_name} (H1) | P |
| Enter the business mobile on file and we'll text you a sign-in code. No password to remember. | P |
| Business mobile | P |
| 704 555 0123 (placeholder, sign-in page only) | P |
| Text me a code / loading: Sending code… | P / N |
| Enter the mobile number as digits, like 704 555 0123. | P |
| Check your phone | P |
| Enter the 6-digit code we just texted. It expires in ten minutes. | P |
| Sign-in code | P |
| Sign in / loading: Signing in… | P / N |
| Didn't get it? Send a new code | P |
| That code is not right or has expired. Check the text or send a new code. | P |

### 6.3 Messages

| Where | String | Status |
|---|---|---|
| H1 | Your messages | P |
| Lead | Every text {business_name}'s scheduling assistant sends, in the order a customer meets them. Changes apply to new conversations after you save. | C |
| Meta | Previews fill in sample details, like tree removal at 12 Elm St. | N |
| Jump link | See the whole conversation | N |
| Moment headings and blurbs | as in §4.3 table | P |
| Eyebrows | Optional questions · Any time | N |
| Card labels, when-lines, rules | `client_portal.MESSAGES`, verbatim | P |
| Pills | Standard wording · Customized | P |
| Pills | Unsaved · Asked · Not asked | N |
| Reset | Use standard wording (vh: " for {label}") | P |
| Switches | Also ask for the best phone number · Also ask for an email address | P |
| Optional off | Not asked right now. Switch it on to add this question. | N |
| Role badges | Customer · TextBack | N |
| Thread pills | Missed call · just now · No reply · Still no reply · Texts stop here · Booked · on your calendar · After the job and address · After all the questions · No booking was made · You get a lead with this conversation · You get an urgent lead | N |
| Handoff divider | You take it from here | N |
| Opt-out note | Opt-out line added | N |
| Count | {n} characters · {k} text / texts, plus " (symbols like — shorten each text)" | P |
| Editor summary | Edit wording (vh: ": {label}") | C (was "Edit the wording") |
| Textarea label (vh) | Wording for {label} | N |
| Editor help | Texts are sent as one paragraph. Leave it empty to use the standard wording. | N |
| Chips label | Insert | N |
| Chip names | §3.14 table | N |
| Chips fallback | Words in curly brackets are filled in for you. This message can use: {token} ({name}), … | N |
| Limit | {len} of 480 characters | N |
| Error summary | Not saved. Fix {label}: {reason} (label is a link) | P |
| Error summary, no key | Not saved: {error} | P |
| Inline error | Not saved: {reason} | P |
| Save bar | All changes saved · {N} unsaved (phone) / {N} unsaved change / {N} unsaved changes · Not saved (phone) / Not saved · 1 message needs a change · Saving… | N |
| Save bar buttons | Save changes · Discard · Show | N (Save was "Save messages") |
| Success toast | Saved. New conversations use these messages from now on. | P |
| Discard toast | Changes discarded. · Undo | N |
| Reset announcement | Standard wording restored for {label}. | N |
| Not editable | Message editing is not set up for this account yet. Ask your operator to enable it. | P |
| POST without file | Message editing is not set up for this account yet. | P |
| Rail title | Conversation preview | N |
| Rail legend (vh) | Show conversation | N |
| Scenarios | Books a job · Second try · Calendar error · No reply · Needs you · Safety · Keywords | N |
| Rail group (aria) | Sample text conversation with {business_name} | N |
| Rail sub-line | Text message | N (brand) |
| Rail caption | Sample conversation · nothing is sent · names invented | N |
| Play | Play · Playing · Play again | N |
| Sample customer lines | as in the §3.17 scenario table and the §3.23 trigger table | N |

### 6.4 Business and confirm

| String | Status |
|---|---|
| Your business (H1) | P |
| How the assistant introduces the business, where customers are pointed, and where sign-in codes go. | P |
| Business name | P |
| Used in every text customers get. | C (replaces the `{business_name}` example) |
| In the first text (preview eyebrow) | N |
| Number in the HELP reply | C (was "Phone number customers should call") |
| Optional (tag) | N |
| Shown when a customer texts HELP. Leave blank to show {sender}. Customers are never transferred to it; the assistant handles the texting. | P (`{sender}` = formatted business number or "the number the texts come from") |
| Your mobile | P |
| Sign-in codes come to this number. If you change it, we text a code to the new number and nothing changes until you enter it. | P |
| Save business details / Saving… | P / N |
| Validation strings (3) | P |
| Not saved. (summary title) | N |
| Saved. · Kept your current mobile. · Saved. Sign-in codes now go to {fmt}. | P |
| Confirm your new mobile | P |
| Details saved · Confirm the new number (stepper; "Done: " vh) | P / N |
| We texted a six-digit code to {number}. Enter it to move sign-in to that number. It expires in ten minutes; until then codes still go to your current mobile. | P |
| Code from the text | P |
| Confirm new mobile / Confirming… | P / N |
| Keep my current mobile | P (was "…instead") |
| Didn't get it? · Send the code again | N |
| Stepper aria-label: Change your mobile | N |

### 6.5 Calendar

| String | Status |
|---|---|
| Your calendar (H1) | P |
| The assistant only offers times that are free on this calendar, and every booking is added to it before the customer gets a confirmation. | P |
| Status titles and details (5) | P |
| Status pill words: Connected · Paused · Error · Test mode | N |
| Meta labels: Calendar · Provider · Bookings · Managed by; values Google · Paused · Not recorded · Your operator | N |
| What Google will ask | P |
| You pick the Google account that owns your business calendar. / Google asks you to let this assistant see and edit your calendars. / It only checks free times and adds appointments. Nothing else in that account is read. / Afterwards, you choose which calendar it uses. | C (the paragraph split into 4 items) |
| Connect Google Calendar · Reconnect Google Calendar / Opening Google… | P / N |
| Connecting a calendar from this page is still being set up by your operator. | P |
| Which calendar should the assistant use? | P |
| Free times are checked on this calendar and new appointments are added to it. | P |
| (main calendar) | P |
| In use | N |
| Use this calendar / Saving… | P / N |
| This is the only calendar this account can add appointments to. | N |
| The assistant now uses {name}. | P |
| Pick one of the calendars listed. · Connecting a calendar is not set up for this account yet. · Google did not grant calendar access. Try connecting again. · Google could not confirm a calendar this account can write to. Try again with the account that owns your business calendar. | P |

### 6.6 Styleguide

| String | Status |
|---|---|
| Styleguide (H1) | N |
| Every token and component on the settings pages, in every state. For review only; nothing here saves. | N |
| Panel labels: Light · Dark | N |
| Run · Show toast | N |

---

## 7. Implementation guidance and constraints

### 7.1 Files

**Templates** (`src/text_back/templates/client/`):

| File | Contents |
|---|---|
| `base.html.j2` | head, shell, topbar, nav, menu, toast region, announcer, `tb-data` JSON |
| `auth.html.j2` | auth layout, no nav |
| `login.html.j2` | sign in |
| `verify.html.j2` | enter code |
| `messages.html.j2` | messages page |
| `_message_card.html.j2` | message card |
| `_rail.html.j2` | phone rail |
| `business.html.j2` | business form |
| `confirm_mobile.html.j2` | confirm step |
| `calendar.html.j2` | calendar |
| `styleguide.html.j2` | styleguide |
| `_macros.html.j2` | icon, button, field, pill, notice, status_block, otp, switch, sms, tpill |
| `_icons.svg.j2` | exists; keep |

**Static:**
- `src/text_back/static/client.css`: tokens from §1.1 first, then base, then components in §3 order.
- `src/text_back/static/client.js`: vanilla ES2019, one IIFE, no dependencies, `defer`.
- Fonts already exist.
- Budgets: CSS ≤ 35 KB, JS ≤ 20 KB unminified.

**Mount and versioning:**
- In `create_app`: `app.mount("/client/static", StaticFiles(directory=<pkg>/static), name="client-static")`.
- Asset version `v` = the first 8 hex characters of the sha256 of the CSS + JS contents, computed at startup.

**No inline script and no inline style.** `client.js` swaps `no-js` for `js` on its first line. This keeps a strict CSP possible later. Server data for JS goes in `<script type="application/json" id="tb-data">{{ data|tojson }}</script>` as `{sample, gsm}`. It is non-executable, and `tojson` escapes `<`.

### 7.2 Small server changes (required)

1. **`save_messages`:** for each key, if `" ".join(value.split()) == " ".join(DEFAULT_TEMPLATES[key].split())`, store `""` (standard). Without this, pre-filled editors would pin today's default into every owner's file.
2. **A Python `LAYOUT` constant** (moments → parent keys → branch keys) plus `TRIGGERS` (§3.23 table) and `SCENARIOS` (§3.17 table), shared by the card and rail templates. Rail bubble text comes from `preview_text(key, templates, sample)`, the same as the cards.
3. **Card attributes:** `data-saved` is the effective saved text (custom or default). `data-saved-checked` on each switch is the saved `ask_*` state. After a rejected save, `data-saved` still reflects the **file**, not the submission.
4. **Business errors:** map error to field by exact string (§4.4). Errors stay single (the first error only).
5. **Calendar:** render the picker only when `status == "ready"`. Add an `in_use` flag per choice.
6. **Theme:** read cookie `tb_theme ∈ {light, dark}` and set `data-theme` on `<html>`. Otherwise omit the attribute.
7. **Styleguide route:** `GET /client/styleguide` (session-gated, 303 to login, `include_in_schema=False`).
8. **Avatar initials:** first letters of the first two `[A-Za-z0-9]+` words of the business name, upper-cased, with "TB" as the fallback.

### 7.3 Data hooks (stable for tests and `docs/notes/ui-compare-a/screenshots.py`)

| Hook | Where |
|---|---|
| `#m_{key}`, `[data-card={key}]` | message card |
| `#f_{key}` | textarea |
| `#e_{key}` | inline error |
| `[data-preview={key}]` | bubble, in cards and rail |
| `[data-count]`, `[data-pips]`, `[data-state-pill]`, `[data-dirty-pill]`, `[data-reset]`, `[data-chips]`, `[data-insert]` | card parts |
| `[data-savebar][data-state]` | save bar |
| `#error-summary` | error summary |
| `[data-toast]` | toast |
| `[data-rail]`, `input[name=scenario]`, `.thread[data-scenario]`, `[data-play]` | rail |
| `[data-status]` | calendar status block |
| `[data-otp]` | OTP field |
| `[data-menu]` | account menu |
| `[data-theme-picker]` | Appearance control |

### 7.4 Tests to add or keep

**Keep green:** every security and behaviour test listed in the contract.

**Add:**
- The verify page contains no `0123` and none of the owner or business digits (full response).
- Messages HTML has exactly 21 `<textarea` elements, each `name` in FIELD_KEYS, and no `disabled` inside `form#messages`.
- The hidden `name=save` button is the first submit button in the form.
- `name=csrf value='` appears on every POST form, including logout.
- Posting the default text verbatim stores "" (standard).
- An invalid card renders `<details … open>` with `aria-invalid=true` and an `#e_{key}` reference.
- The calendar picker is absent unless `ready`.
- `/client/styleguide` returns 303 without a session.

**Allowed to go red:** the markup-coupled assertions in `tests/test_client_portal_ui.py` (one `<style>`, no `<link>`, class names). Update them to the new hooks rather than deleting coverage. Keep the strings it checks ("Sign-in codes come to this number", "texts HELP", "Keep my current mobile", `autocomplete=one-time-code`).

### 7.5 Constraints and pitfalls

- **Jinja escaping:** it escapes `'` as `&#39;`. Never build attribute values with the old `&#x27;` assumption. `data-default` and `data-saved` must be escaped with `|e` inside double-quoted attributes.
- **Hidden fields still post:** `display: none` and closed `details` do not stop textareas from posting. Only `disabled` does, so do not "fix" hidden cards by disabling them.
- **`:has()` fallback:** browsers without it show every optional card expanded and only the default thread. JS covers scenario switching. That is acceptable.
- **No horizontal scroll:** bubbles use `overflow-wrap: anywhere`, which matters for long `/a/` links. The OTP wrapper uses `overflow: hidden`. Every grid child gets `min-width: 0`.
- **Hover:** only under `(hover: hover)`.
- **36px controls:** only under `(hover: hover) and (pointer: fine)`.
- **iOS:** inputs ≥ 16px (they are 17). `format-detection` meta stops phone links inside bubbles. Account for `viewport-fit=cover` safe areas on the tab bar, save bar, toast region and topbar sides.
- **No new third-party assets:** fonts and icons are local.
- **Session expiry** (12h) after a long editing session will drop unsaved edits on POST (303 to login). Acceptable for v1; noted in §8.

---

## 8. Unresolved decisions (need Michael's input)

1. **Calendar button wording when already connected.** The server shows "Reconnect Google Calendar" when the status is `ready`, and "Connect Google Calendar" when broken. That means a "Reconnect needed" heading sits above a "Connect…" button. Separately, Michael's next step ("press Connect Google Calendar") happens while the operator's calendar reads `ready`, so he will actually see "Reconnect". Proposal: "Connect a different Google account" when ready, and "Reconnect Google Calendar" when broken. This changes server strings, so it needs a yes.
2. **Picker only when connected.** Today the picker shows whenever more than one calendar is cached, even while disconnected. This spec hides it unless `ready`.
3. **HELP field label.** "Phone number customers should call" becomes "Number in the HELP reply", so the owner page never implies calls are routed to a person. The helper sentence is preserved.
4. **Pre-filled editors.** The editors show the real wording, and the server stores a default-equal value as "standard" (§7.2.1). If server normalisation is not accepted, fall back to blank textareas with the default as placeholder. That works, but the owner must retype to tweak.
5. **Appearance control** (System/Light/Dark, cookie-backed). Ship it, or follow the system setting only? It helps an owner whose phone is in dark mode but who is outdoors in sun.
6. **Fixed sample date.** The server sample "Thursday, Oct 22 at 4:00 PM" reads as a past date from tomorrow. Proposal: compute "next Thursday at 4:00 PM" at render time. This affects `preview_values`, so a product call is needed.
7. **CSRF-expired response.** A CSRF failure currently returns a JSON 400 body, which an arborist sees as raw text. Proposal: an HTML 400 page in the shell, with H1 "This page expired", "Reload the page and try again. Your changes were not saved." and a Reload button. The status code stays 400.
8. **Moment heading.** Keep "You step in" (current server string, second person) rather than "Owner steps in".
9. **"Send the code again" on the confirm step.** It reuses `POST /client/business` with the pending mobile, so there is no new route. Confirm this is acceptable, given the 3-per-15-minutes silent rate limit.
10. **Handoff placement.** It stays on the spine (per direction.md) even though a customer can ask for the owner at any point. Revisit only if testing shows confusion.
