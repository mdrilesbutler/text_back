# TextBack client portal bake-off — identical blind judge prompt — 2026-10-26

You are an independent judge on a Claude/Grok/Codex panel. Judge TWO candidate designs, labelled only
**Portal X** and **Portal Y**, from the screenshots and page-text files in this folder. Labels were
shuffled per judge; the letters say nothing about origin, order or authorship. Do not try to identify
which team or branch built either one, and do not look outside this folder: no git, no repositories,
no web, no other judges' work. READ ONLY: no edits, installs, API calls, keys, sign-ins or form
submissions. Return your entire scorecard as your final response; the caller captures stdout.
This is a bounded judging task, not implementation: no need to ask permission, plan, create goals,
rank skills, run handoffs or update memory/logs.

## What the product is
TextBack is a missed-call recovery service for small field-service businesses (tree care, guides).
When a call goes unanswered, the customer gets a text conversation that collects the job, location,
preferred time and name, then books a real free slot on the owner's calendar. Customers never reach a
live human. The **client portal** is where the business owner (non-technical, usually on a phone,
between jobs) signs in with a texted code and adjusts settings. The owner needs to be able to:
1. sign in and sign out;
2. read and change the texts customers get;
3. set scheduling rules (appointment length, working hours, quiet hours, reminder timing);
4. connect and check the calendar bookings go to;
5. manage the business name and phone numbers (business line, texting number, owner mobile) and set
   up call forwarding;
6. see whether the service is set up and working.
A portal that lacks a page for one of these jobs scores lower on task completion; do not invent
features you cannot see.

## Evidence (all inside this folder)
- `X/` and `Y/`: one folder per portal. `INDEX.md` in each lists every file.
- `NN-<page>-desktop-MM.png`: Chromium, 1280×900 viewport, light theme. `NN-<page>-phone-MM.png`: 390×844,
  device scale 2, mobile user agent. MM numbers successive scroll positions of the same page (each
  screen overlaps the previous one by 120 px), so sticky bars appear where a person would see them.
- `NN-<page>-<view>.txt`: the page's visible text (convenience only; the screenshots are authoritative).
- `save-*.png`: the screen right after saving a change on that page (taken on a private copy of the
  same build with the same test client), showing the confirmation the owner gets.
- You must actually open the images. If your tools cannot view an image, say exactly that and lower
  your confidence; never pretend to have seen one.

## Fairness notes (apply equally to both)
- Both run the same test client: "Oak & Pine Tree Care", owner mobile 980 555 0123, fake phone
  service (no texts are sent), and no Google account connected, so both Calendar pages show their
  not-connected / test state. Do not penalise either for that state itself; judge how it is explained.
- Any customer names, conversations, counts or registration status visible on a portal come from
  preview demo data seeded by the test harness, not from real customers. Judge how the design presents
  such data, not how much of it there is. A portal that shows invented examples should label them.
- Pages that exist on only one portal are a real difference in scope; score it under task completion.

## Identical rubric — integers 1 to 5 for every criterion, both portals
1 poor/absent · 2 weak · 3 adequate · 4 strong · 5 excellent. Use the same scale for both.
- **a1 Orientation** — within 5 seconds an owner knows where they are, what this page controls, and what to do next.
- **a2 Plain language** — words a non-technical owner uses; no jargon, internal names, code-like tokens or vendor plumbing.
- **b1 Coverage** — how many of owner jobs 1–6 above have a real, findable place in the portal.
- **b2 Friction and feedback** — steps to finish a change, defaults and reset, save confirmation, error and empty states.
- **c1 Phone layout** — at 390 px: readable type, no clipping or sideways scroll, comfortable tap targets, sensible field widths.
- **c2 Phone navigation** — moving between pages and through long pages on a phone (nav placement, page length, sticky save, jump links).
- **d1 Honesty** — sample/demo content labelled, no invented numbers, clear about what is and is not set up or working.
- **d2 Safety cues** — makes consequences clear before saving (what changes, when, for whom), protects STOP/opt-out, verifies number changes, does not over-promise.
- **e1 Visual coherence** — hierarchy, spacing, type and colour feel like one deliberate system on both widths.
- **e2 Finish** — detail polish: truncation, alignment, consistency between pages, typos, awkward wraps, leftover dev text.

**Total /100 = 2 × (a1+a2+b1+b2+c1+c2+d1+d2+e1+e2).** (Five equal areas: clarity a, task completion b,
mobile c, trust d, polish e — 20 points each.)

## Mandatory output
1. Judge identity (model), the files you actually opened (count of images per portal at least), and
   confidence/limitations.
2. ONE Markdown score table with EXACT columns:
   `Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100` and exactly two rows, `X` and `Y`.
3. For EACH portal, at least FOUR specific observations, each anchored to a real file name from this
   folder plus the element you mean (heading, button, card): strengths, failures/friction, and what an
   owner would actually experience. No vague praise. Do not cite files that do not exist.
4. "Looks broken": every visual or functional defect you can see on either portal (clipping,
   truncation, overlap, wrong date, inconsistent state, dead end), with the file name. Say "none seen"
   if so.
5. The THREE best ideas from the portal you rank LOWER that the winner should adopt, each with the
   file name that shows it.
6. One decisive recommendation in 3–5 sentences: why the winner wins and what it must fix before an
   owner sees it. No option menu.
7. End with EXACTLY ONE line: `VERDICT: WINNER X` or `VERDICT: WINNER Y`.
