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
