# Branch consolidation audit — 2026-10-08

Authorized by Michael: recover pertinent content, independently review and merge through a PR, then remove every branch except main. Baseline main: `9352db2679522540c828da71cde8d473d7052b97`. Agent: codex-hermes-vcn-0.

## Inventory and decisions

Fetched GitHub heads and open PRs, checked local heads/worktrees/stashes, compared ancestry, `git cherry` patch equivalence, branch-tip trees, unique commit patches and historical notes. Initial inventory: main plus seven remote branches, one additional local branch; one worktree and no stashes. PR #3 was the only open PR. Fleet created an eighth remote branch during this work; it was also inspected.

| Ref | Audited tip | Unique commits vs baseline | Content decision |
|---|---|---:|---|
| `local/tdd-core` | `b8cc937fd66401765c4b8a4a64e494c0438c9b90` | 0 | DUPLICATE: local tip and previous integration tip have identical trees to main; all commits already ancestors. |
| `origin/agent/claude-wsl/carrier-keywords` | `6eb4005e3d575562da88dcd76d6704ce1273de68` | 3 | SALVAGE: all three unique keyword/HELP/evidence commits ported; see overlap decisions below. Close PR #3 as superseded only after cleanup PR merges. |
| `origin/agent/codex-hermes-vcn-0/main-integration` | `b8cc937fd66401765c4b8a4a64e494c0438c9b90` | 0 | DUPLICATE: PR #5 merged it; tree identical to main. |
| `origin/canon-state` | `9dee67a780c4b384c30eb78d62e550b67c9b8cf3` | 11 | SALVAGE requirements below; exclude obsolete operational state/claims, old phone-role assumptions and state migration. No NOW.md restored. |
| `origin/local/tdd-core` | `82312fcfa5bf33699c9b3d4c6302d1a8a89e8ab6` | 0 | DUPLICATE: all commits already in main. Main additionally has current project rules, historical reference notes and deployment script. |
| `origin/wip/hermes-cloud` | `8aaf1f2192f4eb74780c1960800fa769e8e03a46` | 1 | DUPLICATE intermediate snapshot of this cleanup, created 07:17 UTC by fleet. Source recovery, diagrams and tests all retained in the final tree; later exact-slot/consent fixes supersede its intermediate code. Fleet omits .env.example; final recovery preserves it. |
| `origin/wip/piclaw` | `3150665d1d34ebbc8e321ff11bb377ed463d5831` | 4 | SALVAGE three workflow-animation files byte-for-byte. Unique substantive patch ca8246a adds only these files; later snapshot merges add no new content. Older runtime tree excluded. |
| `origin/wip/piclaw-text-back-reconcile-20260827` | `bc6b9b86b5f591ab3b08a81f7bcafa28ba9cdd10` | 1 | SALVAGE unfinished plan requirements below. Only unique patch adds docs/plans/2026-08-27-main-reconciliation.md; no unique app/designer code. |
| `origin/wip/piclaw-text_back-tdd-core` | `46f11122f58c4d1da6dee58d30dad4e709d07eac` | 1 | SALVAGE Microsoft adapter/tests and one-time calendar connection design. Unique patch after 68d8ba6 touches six files. Older runtime, state and designer snapshots excluded. |

## Recovery and overlap decisions

- Carrier work: OPTOUT/REVOKE and whole-request opt-out phrases, SUBSCRIBE and bare YES resubscription, idempotent lead.opted_out/lead.opted_in evidence, and configurable HELP contact/rates text. Retain current main’s opt_in API/action and function name, STOP cancellation of pending opt-in acknowledgments, UNSTOP guidance, signed webhook boundary, active handoffs and stopped follow-ups. Retain current quiet-hour treatment for delayed enrollment replies instead of importing the old PR exemption. Use whole-message consent matching so numbers, extra words, Unicode suffixes and underscores cannot become consent through token stripping.
- Microsoft work: calendarView supports delegated personal Outlook and M365; `me` endpoint, unknown showAs fails busy, cancelled events ignored for availability, trusted bounded pagination. Keep current booking/recheck/outbox boundaries. Add exact start/end plus explicit non-cancelled verification on 409 recovery; a merely overlapping moved event is insufficient. Preserve non-UTC request coverage and add loop/limit, page-two duplicate and malformed/cancelled/moved-event regressions.
- Workflow assets: docs/assets/workflow-animations/{README.md,textback.html,textback.svg} recovered exactly. Their original 9/9 quality claim is provenance, not a new production certification. Existing deploy/textback-designer and docs/demo are unchanged, as are landing assets.
- One-time calendar connection design is retained in docs/CALENDAR-PROVIDERS.md as a target with current Google implementation status, not as stale assertions that refresh/reconnect does not exist.

## Retained requirements

Historical requirements are preserved here for future Recover work, not marked implemented by this consolidation. CLAUDE.md keeps the current pilot as NEXT. No product phase or requirement is dropped. Source: canon-state NOW.md at 9dee67a, the August reconciliation plan at bc6b9b8, and TDD notes/PRD at 46f1112.

| Requirement | Retained intent / current distinction |
|---|---|
| Settings file | TEXT_BACK_SETTINGS_FILE TOML at ~/.config/text_back/settings.toml for wording, intro delay, business hours, travel buffer, contact, service area and booking link; secrets remain private environment. New HELP contact env setting does not implement this file. |
| Working hours and slot offers | Restrict bookings to configured hours and travel buffers; offer next three available slots with 1/2/3 selection. |
| Stalled conversations | Three failed time/slot attempts → async handoff; mid-conversation silence → one nudge then lead.expired. Existing no-response follow-up is not equivalent. |
| Event and confirmation details | Request summary plus conversation reference in Google event; remove raw event ID from customer confirmation. Existing event ID truth gate remains. |
| Managed dialing | Optional managed mode Dial timeout/action with terminal-status missed trigger. Forwarded mode and existing business cell remain the pilot default. |
| Spend guard | Configured monthly outbound SMS/cost limit, operator warning at 80%, block at cap; preserve $15/month ceiling. |
| Operations logs/backups | Structured JSON logs and daily SQLite backup API snapshots with retention via user timer. |
| Speed metrics | Brief medians for call → initial SMS → reply → qualified → booked. |
| Lead status/operator API | Derived new/engaged/qualified/booked/handed_off/opted_out/expired projection and status/brief endpoints; preserve existing job.completed and revenue.attributed write paths. |
| Reschedule/cancel | Move/delete actual calendar event with verified SMS outcome. Existing CANCEL opt-out behavior needs explicit design reconciliation before appointment-cancellation phrases are introduced. |
| Reminders | Day-before reminder with quiet hours and opt-out cancellation. |
| Operator summary/context | Booking summary to operator and known-caller prior context, beyond current handoff alerts. |
| Value estimates | Per-service default job value and source tags; pipeline estimate separate from evidence-backed attributed revenue. |
| Monthly brief | Worker sends operator Revenue Brief on first of month for TB-CARE. |
| Voice direction | Reject non-inbound voice callbacks before recovery side effects. Still an unfinished reconciliation-plan item. |
| SignalWire origin validation | Validate intended Space origins and reject URL userinfo/path/query/fragment. Current HTTPS check is narrower than this planned contract. |
| Customer calendar onboarding | Connect existing Google/Outlook/M365/iCloud once, select calendar, secure per-business connection store, silent refresh/rotation, exceptional reconnect. See current provider doc for shipped versus missing portions. |
| Pilot | Physical missed/answered-call, STOP → YES123 → START → HELP, booking/handoff and brief evidence still required; supported approved test recipient only. Existing cell remains public, existing SignalWire number backend, business FluxWorks, LLC. |

## Exclusions documented before deletion

- No wholesale snapshot tree merge: older trees would erase newer Google intake, durable outboxes, tests, deployment docs, landing work and Grok designer assets. Code/content comparison, not absence of matching commit IDs, decides recovery. The older Microsoft implementation is the one substantive adapter delta to port.
- Old designer HTML and render differences are ancestor versions, not unique changes on audited WIP commits. Main’s 3717060 assets win; byte/tree checks verify no edits to owned paths.
- Stale root PRD, IMPLEMENTATION-PLAN, NEXT-SESSION and SESSION-NOTES are not restored as competing active state. Unique connection requirements and unfinished reconciliation items were extracted above; already shipped feature descriptions are represented by current code/tests/docs.
- Old runtime-not-live, missing signing key, pending LLC, missing CI, inactive operator delivery, missing Google refresh, expired deployment authorization and branch-specific test counts are superseded by current CLAUDE.md evidence. Old service-account and Cal.com setup, credential rotation, trial role swaps and requests for an additional business number conflict with locked requirements and are excluded.
- The original follow-up claim-before-send defect and proposed release_event workaround are superseded by durable SMS intents/reconciliation plus crash-shaped tests already in main. No obsolete retry path is restored.
- Historical state branch claim/owner/init records and migration to NOW.md are not current requirements. The relevant requirements were extracted; CLAUDE.md remains canonical.
- All audited source tips will be recorded as parents of an explicit provenance merge after manual recovery. This preserves original commits and excluded historical versions in main’s ancestry without allowing their trees to overwrite the reviewed result. Branch deletion therefore removes names, not access to original work.

## Fleet automation and permanent workflow

Inspected canon_fleet.py, canon_sync.py and canon_wrapup.sh. Fleet selects repositories with a remote canon-state branch, with a local cached-ref fallback if GitHub is unavailable. It snapshots dirty/ahead work to wip/<host>. This behavior reproduced during the audit as wip/hermes-cloud at 8aaf1f2.

Repository-only GitHub ruleset **text-back-no-automation-branches** (24703349) now blocks creation and update of refs/heads/wip/*, nested WIP refs and refs/heads/canon-state, with no bypass actors. Deletion is allowed. Main’s existing PR/canon-review protections are unchanged. Deleting/pruning canon-state removes text_back from online snapshot discovery; stale fleet caches cannot recreate these refs even if an older host has not pulled. Non-canon clean-main fast-forward pulls continue. No global fleet script/config or unrelated repository was modified.

AGENTS.md requires temporary PR branches to be merged and deleted, main checked out clean and synchronized, state in CLAUDE.md, and no state-branch init/claim/handoff. Wrap-up still runs the required fleet command after delivery. Historical remote clones may retain local names until they fetch/prune; this task’s local inventory is /home/ubuntu/projects/text_back on hermes-vcn-0, plus all GitHub heads.

## Validation

- Initial focused keyword/policy/outbox/copy/Microsoft suite: **109 passed**.
- Combined suite: **445 passed**. Added the independent reviewer’s signed HELP configuration test afterward: tests/test_sms_policy.py **16 passed**. CI validates the final combined 446-test suite.
- Independent source/implementation review: no blocking findings; suggested HELP wiring coverage added.
- Workflow assets are byte-identical to source; SVG parses, two inline JavaScript scripts pass node --check, and two JSON payloads parse. Designer/demo/landing tree diff is empty.
- git diff --check passes. Final review/merge/deletion/deployment evidence is attached to the cleanup PR.
- Generic canon checker reports its pre-existing CLAUDE.md state-file objection. Explicit repository instruction requires retaining that file; no migration performed.
- No telecom send, purchase, forwarding change, credential edit or runtime allowlist change is part of this cleanup.
