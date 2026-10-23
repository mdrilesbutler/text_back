# Calls made on the design spec's open questions (2026-10-22)

The user brief wins over design-spec.md wherever they differ. These calls were
made by the orchestrating session because the user was not available mid-task.

Overrides from the brief
- Files are `src/text_back/static/portal.css` and `src/text_back/static/portal.js`
  (not client.css / client.js). portal.js is a plain ES module loaded with
  `<script type="module" src=...>`, roughly 300-600 lines, no framework, no bundler.
- Moment headings are the brief's: Missed call, The questions, Booking, No reply,
  Owner steps in, and (off the spine, eyebrow "Any time") START, HELP and STOP.

Spec section 8, decided
1. Calendar button wording stays as the server has it: "Reconnect Google Calendar"
   when connected, "Connect Google Calendar" otherwise. Michael's next real step is
   written against those words.
2. The calendar picker renders only when the status is connected (ready).
3. HELP field label: "Number in the HELP reply"; the helper keeps "texts HELP".
4. Editors are pre-filled with the real wording. save_messages stores a value equal
   to the default (whitespace-collapsed) as standard (""). Accepted.
5. Appearance control (System / Light / Dark, cookie tb_theme on path /client) ships
   in the account menu. It helps an owner whose phone is in dark mode while he works
   in sunlight. It changes presentation only.
6. Sample date stays as the server's preview_values ("Thursday, Oct 22 at 4:00 PM").
7. A CSRF failure renders an HTML 400 page in the shell ("This page expired")
   instead of JSON. Status stays 400.
8. Heading is "Owner steps in" (the brief's word), see above.
9. "Send the code again" on the confirm step re-posts the pending mobile to
   POST /client/business. Accepted; the 3-per-15-minutes limit still applies.
10. Hand-off stays on the spine.

Added hardening
- Portal HTML responses also send
  `Content-Security-Policy: default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`.
  No inline script and no `style=` attributes anywhere in the templates; JS may set
  element.style. No form-action directive, so the Google connect redirect is unaffected.
