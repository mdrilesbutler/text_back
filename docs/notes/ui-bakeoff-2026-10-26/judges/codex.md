Judge: **Codex (GPT-6)**. I opened **all 91 screenshots: 37 for X and 54 for Y**, covering every PNG listed in `X/INDEX.md` and `Y/INDEX.md`, including all save captures. I also opened both indexes and the 18 page-text files. Confidence is high for visual presentation and visible coverage, moderate for behavior: screenshots cannot establish keyboard handling, validation enforcement, persistence or whether untested controls work. Neither portal loses points merely for having no connected calendar.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 4 | 2 | 4 | 4 | 3 | 4 | 3 | 4 | 3 | 70 |
| Y | 4 | 2 | 4 | 4 | 4 | 3 | 2 | 3 | 4 | 3 | 66 |

**Portal X observations**

- `X/03-messages-phone-01.png`: “Your messages” explains what the page controls, how to edit and when changes begin. Rendered customer texts and “STOP line added for you” let an owner inspect the actual wording without interpreting template syntax.
- `X/03-messages-phone-04.png`: the optional phone question says “Off. Customers skip this question.” This connects the switch directly to customer experience and avoids displaying unnecessary editing controls.
- `X/save-01-messages-desktop.png`: “Saved. Changed: Question 2: the location” identifies the specific successful change. That is more reassuring than an unexplained checkmark.
- `X/save-03-owner-mobile-change-desktop.png` and `X/save-04-keep-mobile-desktop.png`: number changes have a clear confirmation stage, explain that the current mobile remains active and provide “Keep my current mobile,” followed by explicit cancellation feedback.
- `X/03-messages-phone-12.png`: “Sample conversation · nothing is sent · names invented” clearly distinguishes the preview from business activity.
- `X/03-messages-phone-10.png`: the save control appears near the end of a very long editor. The shortcuts in `X/03-messages-phone-01.png` help, but scrolling through messages and then the full conversation still demands substantial effort.
- `X/04-business-desktop-01.png` and `X/05-calendar-desktop-01.png`: coverage is substantially incomplete. Business offers name, HELP number and owner mobile; there is no evidenced scheduling-rules page, business-line/texting-number management, forwarding setup or overall service-status page. An account icon exists, but the supplied evidence does not expose a sign-out action.

**Portal Y observations**

- `Y/03-home-phone-01.png`: the calendar, forwarding and registration cards immediately surface setup problems. “Four checks left” gives the owner a concrete sense of remaining work.
- `Y/05-scheduling-phone-01.png` through `Y/05-scheduling-phone-03.png`: appointment presets, time zone, working hours, quiet hours and reminder delays have real controls. Defaults, Reset actions and the explanation about already-scheduled reminders reduce uncertainty.
- `Y/07-phone-desktop-01.png`: business, texting and owner numbers have distinct labels and verification actions. The forwarding card explicitly warns that forwarding every call would change how answered calls are handled.
- `Y/08-account-phone-01.png`: sign-out and remembered-device settings are plainly available, with a link to the page for changing the sign-in mobile.
- `Y/04-messages-phone-07.png`: an almost complete screen is consumed by insertion tokens such as `{invite_line}`, `{calendar_links}` and `{event_id}`. This makes a routine wording change feel technical.
- `Y/04-messages-phone-01.png`: persistent Save, Preview and navigation controls are useful, but their combined height substantially reduces the editing viewport. There are no visible section shortcuts across twelve captured scroll positions.
- `Y/save-01-messages-phone.png` and `Y/save-02-scheduling-phone.png`: confirmation banners explain that saved settings apply to new conversations. The feedback is prominent and readable.
- `Y/03-home-desktop-01.png` and `Y/07-phone-phone-03.png`: seeded conversations, registration status and test-call evidence are presented without demo labels; the checklist explicitly describes “real calls.” An owner could mistake demonstration content for proof that their service works.

**“Looks broken”**

- **X — misleading saved-name preview:** `X/save-02-business-desktop.png` and `X/save-02-business-phone.png` show the changed business name in the field while “IN THE FIRST TEXT” retains the old name. A customized message may explain this, but the page says the name is “Used in every text” and does not explain the exception.
- **X — notification overlap:** `X/save-01-messages-phone.png` and `X/save-02-business-phone.png` show confirmation toasts covering the page heading and introductory text.
- **X — header truncation:** those same phone save captures truncate the changed business name. The original name fits in the baseline captures.
- **X — exposed infrastructure:** `X/03-messages-phone-06.png` and `X/03-messages-phone-12.png` show long internal-looking HTTP hostnames and ports in booking messages, producing awkward multi-line wrapping.
- **Both — calendar setup dead ends:** `X/05-calendar-desktop-01.png` and `Y/06-calendar-desktop-01.png` say connection is unavailable and provide no actionable connection/contact route. Y’s `Y/03-home-phone-01.png` nevertheless offers “Set up”; its calendar page also says “Ask text_back” without a visible contact action.
- **Y — conflicting calendar explanation:** `Y/save-03-availability-phone.png` calls availability “A real read of the calendar the assistant books on” while stating that no real calendar is connected. The smaller “Test calendar” qualifier does not fully resolve that contradiction.
- **Y — inconsistent checklist state:** `Y/07-phone-phone-03.png` marks a recorded test call Done, then says “No call recorded yet” beneath the next check. It should distinguish missing text evidence from missing call evidence.
- **Y — incorrect weekday/date pairing:** `Y/03-home-desktop-01.png` shows “Thursday, Oct 23” in the booked conversation. October 23, 2026 is Friday.
- **Y — truncation hides information:** `Y/03-home-desktop-01.png` truncates the business name in the sidebar; `Y/03-home-phone-02.png` truncates every conversation excerpt without a visible expand affordance. Whether the rows open cannot be established.
- **Y — cramped spacing:** `Y/05-scheduling-desktop-03.png` places “Close the lead” immediately beneath the preceding Default/Reset line, weakening field separation.
- **Both — unsupported follow-up promises:** `X/03-messages-phone-09.png` and `Y/04-messages-phone-11.png` promise direct owner follow-up. That commitment is not established by the supplied product description or evidence; Y additionally instructs the editor to preserve the promise.
- **Both — stale scheduling examples:** `X/03-messages-phone-03.png` and `Y/04-messages-phone-03.png` suggest October 22 despite the October 26 judging date. These are examples, but unsuitable examples for choosing a future appointment.

No other clear clipping or unintended horizontal page overflow was visible. Content passing beneath fixed bars during scrolling is not, by itself, evidence that it becomes permanently inaccessible.

**Three ideas X should adopt from lower-ranked Y**

1. **A complete Scheduling page:** appointment presets, visible defaults and per-rule Reset actions in `Y/05-scheduling-desktop-01.png`, plus timing consequences in `Y/05-scheduling-phone-03.png`.
2. **A dedicated number-and-forwarding workflow:** distinct number roles, carrier selection and conditional-forwarding guidance in `Y/07-phone-desktop-01.png`, with clearly labelled test evidence.
3. **An actionable setup overview:** calendar and forwarding status cards in `Y/03-home-phone-01.png`, connected to genuine next steps and explicitly labelled when showing demo data.

Choose **Portal X** as the design foundation: it narrowly wins through clearer message presentation, stronger sample labelling and a better-evidenced mobile-number change flow. Y covers substantially more owner jobs, but its template-heavy editing and misleading operational evidence undermine usability and trust. Before an owner sees X, add scheduling, forwarding, service status and an explicit sign-out route, and make calendar setup actionable. Also reconcile business-name previews, replace infrastructure URLs, remove unsupported follow-up promises and keep phone confirmations clear of headings.

VERDICT: WINNER X