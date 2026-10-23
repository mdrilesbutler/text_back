# Visual direction (settled 2026-10-22 with superpowers:brainstorming)

Subject: the owner of a field-service business (an arborist) opens /client on a
375px phone, outdoors, from the sign-in text. The job of the portal: show him
exactly what his customers get texted, let him change it safely, and confirm
his business details and the calendar that receives bookings.

## Directions considered

1. **Conversation spine (chosen).** Messages reads top to bottom in the order a
   customer meets them. Moment groups sit on a thin vertical spine that starts
   at the brand's red missed-call dot. Every card leads with the SMS bubble
   exactly as the customer sees it. A phone frame on the right replays the whole
   conversation with sample data and updates as he types.
2. Linear-style dense rows with inline editors. Rejected: generic, and an
   arborist reads bubbles faster than a table of strings.
3. Two-pane list/detail editor. Rejected: poor at 375px and with JS off.
4. Illustrated "story" moments. Rejected: the brand forbids illustration and
   decoration.

Checked against the three AI-default looks (cream + serif + terracotta, black +
acid accent, hairline broadsheet): none applies. The palette is the brand's
white, stone neutrals, #171717 ink and #166534 forest green.

## Precedence

The user's brief wins, then fluxworks-design, then generic skills. Two brief
items extend the brand on purpose: a dark token set (the brand is light-only)
and semantic status colors (the brand allows one red dot). Status hues are kept
muted and always travel with an icon and a word, which is the one thing taken
from the dark designer's feel, along with dense tabular metadata.

## Signature

The spine plus the bubble. Structure encodes truth: the spine is the real order
of the conversation, and START/HELP/STOP sit off the spine under "Any time"
because those replies can arrive at any point. Everything else stays quiet:
white cards, 1px stone borders, no shadows except the phone frame, popovers,
toasts and the sticky save bar.

## Shell

- Full-width header on every size: TextBack wordmark, business name, account
  menu (native details/summary, Sign out is a POST).
- Phone: bottom tab bar (Messages, Business, Calendar), 64px plus safe area.
- 1024px and up: left sidebar nav; Messages adds a sticky right rail.

## Type and size

Archivo 600 for headings only; Source Sans 3 400/500/600 for everything else.
Body is 17px for sunlight reading; nothing below 13px; inputs 17px (no iOS
zoom); controls 44px minimum, 48px for primary actions on phone. Counts use
tabular figures.

## Key interaction decisions

- Each message card shows label, when it is sent, status (Standard wording /
  Customized, icon + word), the rendered bubble with business name filled and
  the opt-out line appended, and count + segments. The editor sits in a native
  disclosure ("Edit wording") so the page stays scannable at 375px and works
  with JS off. A card with a server error renders open.
- Placeholder chips show plain names ("Business name") and insert the raw token
  at the cursor.
- One sticky save bar for the whole Messages form: "All changes saved" or
  "N unsaved changes", Discard, Save changes. Reset to standard wording is local
  with JS (undoable via Discard) and a server POST without JS.
- A rejected save renders an error summary with links to each offending card
  and the reason beside the message that caused it.
- OTP is one real input (autocomplete=one-time-code, numeric) drawn as six
  cells with CSS, so paste and SMS autofill work natively.
