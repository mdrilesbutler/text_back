Judge: **Codex (GPT-6)**. I opened all **114 images for X** and **37 images for Y** listed in their respective `INDEX.md` files, including desktop, phone, save and additional state screenshots. I also opened both indexes and the desktop page-text files. Confidence is high for visual design and demonstrated coverage, moderate for behavior: screenshots show results, but cannot establish whether integrations, delivery, navigation or persistence actually work. Neither portal is penalized merely for having no Google calendar connected.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 4 | 4 | 86 |
| Y | 4 | 3 | 2 | 3 | 4 | 3 | 4 | 3 | 4 | 2 | 64 |

**Portal X — observations**

- **Broad, findable coverage.** `X/05-schedule-phone-01.png` provides appointment length and time zone; `X/07-phone-phone-01.png` begins business and phone management; `X/08-account-phone-02.png` provides sign-out controls. Together with Home, Messages and Calendar, X supplies a visible place for all six owner jobs. Calendar connection still requires support, preventing full self-service completion.
- **Excellent editing feedback.** `X/state-messages-unsaved-phone.png` shows the change count with persistent Save and Discard actions, while changed wording retains its original “Was” text. `X/save-01-messages-wording-phone.png` confirms the particular change. An owner can review and finish edits without remembering everything changed or scrolling to the page bottom.
- **Useful safety guidance.** `X/state-schedule-any-time-phone.png` explicitly warns that customers could receive 1 AM appointments and offers “Use Mon–Fri, 8 AM–5 PM.” `X/state-phone-carrier-verizon-phone.png` provides forwarding instructions and reversal information. These connect settings to practical consequences.
- **Business-name changes receive follow-through.** `X/save-03-business-name-rename-offer-phone.png` explains that one text still contains the old name and offers to update it. `X/save-04-rename-texts-updated-phone.png` shows the result. The owner is protected from assuming a name change automatically rewrites customized messages.
- **Sensitive changes have visible safeguards.** `X/save-07-owner-mobile-confirm-step-phone.png` requires a code sent to the new number before replacing the current number. `X/state-account-signout-everywhere-phone.png` explains the consequences before confirming sign-out everywhere.
- **Readable but lengthy.** `X/04-messages-phone-01.png` through `X/04-messages-phone-12.png` show a long editing journey. The persistent section selector and bottom navigation help, and controls remain comfortably sized, but extensive explanations and nested spacing make quick scanning slower.
- **Demo labeling is strong, with a confusing summary.** `X/03-home-phone-01.png` labels examples and distinguishes “Needs you” from “Waiting on FluxWorks.” However, “Not working yet: 1 step left” does not clearly distinguish the owner’s remaining action from other unresolved dependencies.

**Portal Y — observations**

- **The central editing purpose is immediately understandable.** `Y/03-messages-phone-01.png` explains that changes start with the next missed call after saving, labels made-up examples and presents recognizable message bubbles. The dotted treatment of the protected STOP wording makes the automatically added text identifiable.
- **Conditional messages are grouped effectively.** `Y/03-messages-phone-03.png` places the unclear-time response beneath the relevant question. `Y/03-messages-phone-04.png` keeps optional-question controls compact. Owners can understand the relationship between a question and its fallback without navigating separate sections.
- **Coverage is substantially incomplete.** `Y/INDEX.md` and the navigation in `Y/05-calendar-phone-01.png` show Messages, Business and Calendar, but no scheduling-rules page, forwarding setup or overall service-status page. `Y/04-business-phone-01.png` and `Y/04-business-phone-02.png` do not provide the full business-line/texting-number/owner-mobile setup. Sign-in is demonstrated; an actual sign-out action is not shown.
- **Some safeguards and feedback are good.** `Y/save-03-owner-mobile-change-desktop.png` retains the current number until verification and offers a cancellation path. `Y/save-01-messages-phone.png` identifies which question was saved, although its toast obscures page content.
- **Calendar setup leaves the owner stranded.** `Y/05-calendar-phone-01.png` honestly states that no calendar is connected and bookings are not recorded. Saying connection is “still being set up by FluxWorks,” without an action or contact route, gives the owner no visible way to advance.
- **Phone navigation loses usefulness on the long page.** `Y/03-messages-phone-01.png` starts with horizontal section chips, but later screenshots lack a persistent section control. The save row appears in `Y/03-messages-phone-10.png`. A persistent unsaved-change save control is not demonstrated, so I cannot credit one.
- **Polish breaks down in customer-facing previews.** `Y/03-messages-phone-12.png` exposes long internal-looking URLs, a stale booking date and an unqualified “on your calendar” badge. The conversation is explicitly labeled sample content, which earns honesty credit, but the preview still needs cleanup.

**Looks broken — visible defects and inconsistencies**

- **X: ambiguous setup count.** `X/03-home-desktop-01.png` says “1 step left” while calendar connection, forwarding and texting approval remain unresolved. If it means one owner action, the heading should say so.
- **X: incomplete message preview.** `X/04-messages-phone-12.png` says every example text starts with the network notice, but the displayed bubbles omit it. Owners cannot inspect the complete text described by the page.
- **X: ambiguous application timing.** `X/state-schedule-custom-length-phone.png` shows an unsaved change alongside “Applies right away.” “After saving” is needed to distinguish editing from activation.
- **X: truncated conversation excerpt.** `X/03-home-phone-03.png` cuts off Dana’s last text with an ellipsis; no expansion affordance is visible. This is a limited-detail issue, not evidence of page overflow.
- **Y: saved-name mismatch.** `Y/save-02-business-phone.png` shows the new business name while the first-text preview retains the old name, without explanation or an update offer. This conflicts with the claim that the business name is used in every customer text.
- **Y: exposed technical URLs.** `Y/03-messages-phone-12.png` displays a hostname, port and opaque paths repeatedly in the booking message, creating a large, difficult-to-read block.
- **Y: stale sample date and misleading local status.** That same file books Thursday, October 22, before the October 26 judging date, and says “Booked · on your calendar” despite the disconnected state in `Y/05-calendar-phone-01.png`. The sample disclaimer mitigates this; it does not demonstrate a real booking failure.
- **Y: calendar dead end.** `Y/05-calendar-phone-01.png` supplies neither connection nor support action.
- **Y: obscuring save feedback.** `Y/save-01-messages-phone.png` places the dismissible success toast over the page heading and introduction. `Y/save-02-business-phone.png` uses the same overlay pattern.
- **Y: partial navigation clipping.** `Y/03-messages-phone-01.png` cuts the right edge of the horizontal chip row. This appears to be horizontal navigation, but its continuation is not clearly explained. The saved-state header also ellipsizes the long business name in `Y/save-01-messages-phone.png`; that is controlled truncation rather than broken layout.

No additional permanent overlap or whole-page horizontal overflow was evident. Normal screenshot boundaries and content passing beneath sticky bars were not counted as defects.

**Three ideas X should adopt from Y**

1. **Attach fallback messages directly to their triggering question**, as in `Y/03-messages-phone-03.png`. This makes conversational branches easier to understand.
2. **Use compact optional-question headers with the toggle beside the label**, as in `Y/03-messages-phone-04.png`. X could reduce scrolling while preserving explanations.
3. **Visually distinguish automatically protected STOP wording inside the bubble**, as in `Y/03-messages-phone-01.png`. This complements X’s explanatory copy and makes the editable boundary clearer.

Choose **Portal X**: it covers the owner’s operating tasks substantially better and provides stronger save, recovery and safety feedback. Its readable phone controls and persistent editing actions make its longer pages manageable. Before release, clarify the setup count and exactly when saved rules take effect, and show the complete network-prefixed customer text in previews. Adopt Y’s compact question grouping to shorten the editing experience while retaining X’s safeguards.

VERDICT: WINNER X