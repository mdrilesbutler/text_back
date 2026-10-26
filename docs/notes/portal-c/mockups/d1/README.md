# d1 — Spine

Idea: every page is one vertical story read top to bottom. A thin stone spine runs down the left with one node per thing that matters: a setup item on Home, a step of the conversation on Messages, a rule on Schedule, a forwarding check on Phone, a connection state on Calendar. The node's glyph is the status (filled green tick = Done, empty ring = Needs you / Not yet, dashed ring = You checked this) and the word beside it says the same thing, so nothing is colour-only.
Borrowed from A: the full stylesheet (portal.css) and its component anatomy: message card (head, rules, green bubble band, receipt line, Edit wording / Reset foot), amber cost warning,
one-input six-cell code entry, switch rows, pill radios, choice cards, and the phone frame and thread of the example conversation.
New: the spine itself on all five pages, with the red missed-call dot on the first node of Home and Messages; Home's three setup nodes with one action each and a plain "Not working yet: N steps left" headline;
Phone's five forwarding checks as numbered nodes with evidence dates; START/HELP/STOP collapsed into one node; sticky jump chips naming the five steps; a Save bar that takes the bottom-nav slot while a change is unsaved; a desktop preview rail that scrolls its own thread beside a 44rem column.
Signature element: the spine with its red missed-call dot at the top, the same mark that opens the example thread, so the settings page and the customer's phone are visibly the same story.
Chrome budget: header 56, jump chips 44 (Messages only), bottom nav 56 = 156; `html { scroll-padding-top/bottom }` set from these.
Everything renders from ../fixture.json through build.py; no JavaScript; 27 HTML files; capture check clean at 390 and 1280 and at 320 for sideways scroll.
