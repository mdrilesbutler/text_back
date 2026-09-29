# NOW — text_back

## STATE (as of 2026-09-29)
- PR #1 merged into `local/tdd-core` (followup crash tests). PR #2 open, review SAFE: moves app code into `main`, AGENTS.md "how it works", `scripts/deploy.sh`.
- Until #2 merges, app code is on `local/tdd-core`; after it, `main` is the only working branch and deploy = merge + `bash scripts/deploy.sh`.
- hermes-vcn-0 (ubuntu@100.124.192.46): text-back.service healthy on `local/tdd-core` @ 3a7faa3, clean tree, SignalWire + Google live, pilot_recipient_count 0.
- Reconciled 2026-09-29 against docs/: built+tested = forwarded/managed triggers, signatures, STOP/HELP basics, 4-field slot filling, booking with recheck, handoff→Telegram, follow-ups, outboxes, brief, operator revenue writes. 370 tests green.
- Missing = NEXT below (PRD + PRODUCT-MODEL Recover P0/P1). Excluded by locked roadmap: Answer/Grow (P2).
- Settings decision: non-secret tunables (wording, delays, hours, buffer, contact, booking link) move to one TOML file at `~/.config/text_back/settings.toml` (`TEXT_BACK_SETTINGS_FILE`); secrets stay in runtime.env.
- Pilot phones: client (business) phone = client's real number, 980-428-5452 for the pilot; SignalWire +17045695600 = text number. Live test texts go only to Riles's verified number.
- 10DLC Brand+Campaign: Riles's job in his browser; build as if approved.

## NOW
Merge PR #2 and run `bash scripts/deploy.sh`; confirm hermes-vcn-0 is on `main` and healthy.

## BLOCKED
BLOCKED · merge PR #2 · Claude's auto-mode guard refuses `gh pr merge` even with a SAFE review · NEED YOU: merge #2 (or allow `gh pr merge` for Claude), then say "go"

## OWNER
claude-wsl#f8fe · 2026-09-29T01:32Z

## NEXT
- carrier-keywords: exact-match STOP/STOPALL/UNSUBSCRIBE/CANCEL/END/QUIT/OPTOUT/REVOKE; START/UNSTOP re-opt-in; HELP names business + contact number; tests
- settings-file: TEXT_BACK_SETTINGS_FILE TOML with Hatch-like defaults for all customer wording, intro delay, business hours, contact phone, service area, booking link; env keeps secrets
- working-hours: bookings only inside configured working hours with a travel buffer around existing events (PRD calendar reqs)
- offer-slots: when the requested time is taken or outside hours, text the next 3 open slots; customer replies 1/2/3 to book
- stalled-conversation: repeated failures (3 bad times/slots) → async handoff; mid-conversation silence → one nudge then lead.expired
- event-details: Google event description carries request summary + conversation reference; confirmation text drops raw event ID
- managed-dial: managed mode rings the operator with <Dial timeout=ring_timeout action=…>; missed = terminal status
- spend-guard: monthly outbound SMS/cost cap from settings; operator alert at 80%; sends blocked at cap (PRD ops)
- ops-logs-backup: structured JSON logs; daily SQLite backup (backup API) with retention via systemd user timer
- speed-metrics: brief reports call→first SMS→first reply→qualified→booked medians (PRODUCT-MODEL)
- lead-status: derived lead status projection (new→engaged→qualified→booked/handed_off/opted_out/expired) + operator HTTP endpoints for status, brief, job.completed, revenue.attributed
- reschedule-cancel: RESCHEDULE / "cancel appointment" flow moves or deletes the Google event, confirms by SMS (P1)
- reminders: day-before appointment reminder SMS, quiet hours respected, cancelled on opt-out (P1)
- operator-summary: operator gets a concise lead summary on every booking (not only handoffs) + known-caller prior context (P1)
- value-estimate: per-service default job value + lead-source tag; brief shows estimated pipeline separate from attributed revenue (P1)
- monthly-brief: worker sends the Recovered Revenue Brief to the operator channel on the 1st of each month (TB-CARE)
- real-phone-pilot: allowlist Riles's verified mobile, run docs/ONBOARDING-FORWARDING.md checklist — needs Riles on a physical phone
