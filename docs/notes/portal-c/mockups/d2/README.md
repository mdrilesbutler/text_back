# d2 "Ledger"

One flat settings ledger, GOV.UK task-list style, built for one thumb: full-width rows with hairline dividers, label left, state word right, action at the row end, 16px gutters, no cards.
Borrowed from A: the SMS bubbles (`.sms`, `.phone` frame, `.tpill`), buttons, inputs, switches, pill radios, OTP cells, notices and the FluxWorks tokens in `_assets/portal.css`.
New here: Home as a three-row setup task list under one status sentence, a four-up stat row, callers as ledger rows; Messages as rows that expand into their editor (`details`/`summary`) with the bubble preview inside the row, five sticky jump chips, and the example conversation at the end on phone or a sticky scrolling rail on desktop; Phone, Schedule, Calendar and Account as the same rows; a bottom tab bar the Save bar replaces while a text is unsaved; a sticky sidebar on desktop.
Signature element: the status tag vocabulary (Done, Needs you, Waiting on phone companies, Not yet, You checked this) rendered as one glyph+word pair, identical on every page.
Build: `../../../../../.venv/bin/python build.py` renders the Jinja2 templates in `templates/` from `../fixture.json` into the 29 HTML files here; `d2.css` links after `../_assets/portal.css` and holds only what differs. No JavaScript.
