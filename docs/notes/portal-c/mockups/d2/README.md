# d2 "Ledger"

One flat settings ledger, GOV.UK task-list style, built for one thumb: full-width rows with hairline dividers, label left, state word right, action at the row end, 16px gutters, no cards.
Borrowed from A: the SMS bubbles (`.sms`, `.phone` frame, `.tpill`), buttons, inputs, switches, pill radios, OTP cells, notices and the FluxWorks tokens in `_assets/portal.css`.
New here: Home as a three-row setup task list under one status sentence, a stat row, callers as ledger rows; Messages as rows (heading, badge with Reset, bubble, receipt) whose only disclosure is "Edit wording", opening a plain `<textarea>` with bracketed insert markers, five sticky jump chips ending at the example conversation (end of page on phone, sticky rail on desktop); Phone, Schedule, Calendar and Account as the same rows; a bottom tab bar that a Save bar naming each changed item replaces while a form is dirty (Messages, Schedule, Phone); a sticky sidebar on desktop.
Signature element: the status tag vocabulary (Done, Needs you, Waiting on phone companies, Not yet, You checked this) rendered as one glyph+word pair, identical on every page.
Build: `../../../../../.venv/bin/python build.py` renders the Jinja2 templates in `templates/` from `../fixture.json` into the 32 HTML files here; `d2.css` links after `../_assets/portal.css` and holds only what differs. No JavaScript.
