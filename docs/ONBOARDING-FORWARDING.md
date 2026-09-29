# Client onboarding — wiring an existing number (forwarded mode)

How a client attaches their real business number to text_back without porting:
enable **conditional call forwarding** (busy / no-answer only — never
forward-all) from their phone to their assigned text_back number. One-time,
reversible, no carrier plan change.

Codes verified against first-party carrier pages 2026-08-20 unless marked
UNVERIFIED. Re-verify before onboarding a client on an UNVERIFIED path.
Dial codes from the client's phone, then press Call/Send.

`<TB>` = the client's 10-digit text_back (SignalWire) number.

## Verizon Wireless — VERIFIED

- Activate (covers both busy and no-answer): dial `*71<TB>`
- Deactivate: dial `*73`
- Ring timeout: not adjustable (fixed ~3–4 rings)
- Cost: no monthly fee on current plans; forwarded legs use plan airtime
- Must be set while on Verizon's network (not while roaming internationally)

## T-Mobile US — VERIFIED

- Activate no-answer: `**61*1<TB>#`  — with ring delay: `**61*1<TB>**<seconds>#` (5–30s in 5s steps, e.g. `**61*18055551234**20#`)
- Activate busy: `**67*1<TB>#`  · unreachable: `**62*1<TB>#`
- Deactivate: `##61#` (no-answer), `##67#` (busy), `##62#` (unreachable), `##004#` (reset all forwarding)
- Cost: not stated first-party; current plans are unlimited talk

## AT&T Wireless — device settings, codes UNVERIFIED

AT&T publishes no consumer star codes and forwarding can't be managed online
(support article KM1011513, updated 2025-04-02).

- Android: Phone app → Settings → Call forwarding → set "When busy" and
  "When unanswered" to `<TB>` (this sends the GSM codes under the hood)
- iPhone: the Settings toggle is forward-all only — do NOT use it. Try the
  GSM codes directly (UNVERIFIED on AT&T): `**61*1<TB>#`, `**67*1<TB>#`;
  deactivate `##61#` / `##67#` / `##004#`
- Cost: forwarded calls billed for call length; some plans exclude forwarding
  minutes from plan minutes

## Cricket (AT&T prepaid) — UNVERIFIED, expect friction

Included feature, but no codes published first-party. Try the GSM codes as
for AT&T; conditional forwarding is reported intermittent, and 611 support
sometimes has to clear stuck forwarding. Check status with `*#61#` / `*#67#`;
fall back to 611.

## Verify the wiring (every onboarding, no exceptions)

1. From a phone that is NOT the client's, call the business number and let it
   ring out (don't answer).
2. Confirm the caller receives exactly one intro SMS from `<TB>`.
3. Call again and ANSWER — confirm no SMS is sent.
4. Confirm the original caller ID reached the webhook (`From` = the test
   phone, not the client's number). Caller-ID passthrough is UNDOCUMENTED by
   all four carriers — this live check is the only proof.
5. Show the client the deactivation code for their carrier and leave it in
   their runbook.

## Notes

- The intro SMS arrives from `<TB>`, not the number the caller dialed — intro
  copy must name the business (policy already does).
- Voicemail interplay: conditional forwarding to `<TB>` replaces carrier
  voicemail for missed calls. If the client wants voicemail too, the text_back
  number must provide it (open item).

## Complete the real-phone Recover pilot

Keep `TEXT_BACK_PILOT_RECIPIENTS` explicitly empty until the operator supplies
approved caller mobiles. Record the forwarding phone's carrier and distinguish
that phone from the separate caller phone. Forward unanswered calls **from the
existing cell to the purchased SignalWire number**. Only approved caller numbers
belong in the SMS allowlist; knowing a phone number does not authorize texting it.

Before calling, verify public health, the configured business name/timezone,
Google access, exact POST voice/SMS handlers, and the expected recipient count.
Register the Web OAuth callback and complete browser reconnection through the
operator's normal browser, preserving the existing pilot token until reconnection
succeeds. Confirm the operator actually saw the private Telegram setup alert.
Use `docs/RECOVER-OPERATIONS.md` for configuration and recovery procedures.

1. Record the UTC start time and database/outbox baseline. Keep old stub messages
   and synthetic requests outside the pilot evidence. Check that the approved
   caller has no existing opt-out or active handoff; do not erase either to make
   a test pass.
2. Enable carrier-specific conditional forwarding and perform every wiring check
   above. Record the missed-call provider ID and verify its original `From`
   matches the approved caller. Pair one intro outbox intent and one provider
   message ID with the caller's confirmation of exactly one received intro.
3. For the answered-call check, record its own start/end times, answer the
   forwarding cell, and confirm the caller received no new intro. Check for no
   new Recover voice job or intro intent for that call. An SMS suppressed because
   the caller is opted out or handed off cannot prove correct forwarding.
4. Reply to each prompt separately: service, location, a future date/time in the
   configured timezone, then name. Use a harmless pilot description and a slot
   the calendar owner is willing to reserve. If the slot is occupied, choose
   another future slot through the conversation.
5. Verify the resulting Google event by provider ID and confirm the handset
   received the booking message. If booking instead reaches an asynchronous
   handoff, verify the durable alert and have the operator confirm receipt of
   that specific lead. A setup alert alone does not prove lead delivery. Record
   which outcome occurred; never label a handoff as a booking.
6. Send STOP from the caller phone. Verify persisted opt-out and cancellation of
   pending customer sends. After any in-flight send finishes, make another missed
   call and send a normal reply; neither should start automated scheduling or
   deliver another intro. Distinguish any carrier-generated STOP acknowledgment
   from an application send using provider records.
7. Render the Recovered Revenue Brief for the recorded pilot window using
   `brief.build_brief_data` / `brief.render_brief`. Reconcile its missed calls,
   replies, booking or handoff against provider IDs and the outcome ledger.
   The post-STOP missed call can still count as a missed call; it must not count
   as another contacted lead. Revenue stays zero without explicit attribution.

Record actual results in NOW.md STATE (via `canon_state.py`): UTC window, call/message/event or alert IDs,
handset and operator acknowledgments, failures, and retest results. Keep full
phone numbers, customer content, and credentials out of repository documentation.
Provider SMS acceptance, delivery status callbacks, and human receipt are distinct
evidence. Passing synthetic webhooks or the local suite never completes this
checklist. Leave forwarding deactivation instructions with the operator; agree
whether forwarding remains enabled after the test. Returning the recipient list
to an explicit empty value blocks further customer SMS without changing routing.
