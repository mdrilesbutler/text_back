# text_back Main Reconciliation Implementation Plan

> **For Hermes:** Execute this plan with focused tests, independent review, and the Michael quality-control gate.

**Goal:** Make the tested `origin/local/tdd-core` implementation the verified canonical `main` branch without enabling live telecom traffic.

**Architecture:** Preserve the existing FastAPI/SQLite/SignalWire Compatibility core and its deterministic policy boundaries. Fix only merge-blocking reliability/compliance defects found during review, refresh canonical handoffs, then fast-forward `main` after all local gates pass.

**Tech Stack:** Python 3.13, FastAPI, SQLite, httpx, pytest, SignalWire Compatibility API.

---

### Task 1: Establish the branch baseline

**Objective:** Prove the remote feature branch is intact and reproducible on piclaw.

**Files:** No tracked changes.

1. Fetch `origin` and verify `origin/main..origin/local/tdd-core` topology.
2. Create an isolated worktree from `origin/local/tdd-core`.
3. Install `.[dev]` in `.venv`.
4. Run `.venv/bin/pytest tests/` and require the historical 142-test baseline.
5. Run `git diff --check`, package/import smoke checks, and a redacted secret scan.

### Task 2: Close deterministic opt-in and retry gaps

**Objective:** Fix bounded compliance/reliability defects without adding live infrastructure.

**Files:**
- Modify: `src/text_back/policy.py`
- Modify: `src/text_back/handlers.py`
- Modify: `src/text_back/store.py`
- Modify: `src/text_back/followup.py`
- Modify: `src/text_back/app.py`
- Modify: `src/text_back/telecom.py`
- Test: `tests/test_sms_policy.py`
- Test: `tests/test_followup.py`
- Test: `tests/test_webhooks.py`
- Test: `tests/test_signalwire_telecom.py`

1. Add failing tests proving `START` reverses opt-out and allows later transactional messaging.
2. Implement deterministic START handling and an accurate opt-in acknowledgement.
3. Add failing tests proving a failed initial/follow-up transport does not permanently poison its idempotency claim.
4. Add a bounded `release_event` path and release only claims whose provider send definitely failed before acceptance.
5. Add failing tests proving non-inbound voice callbacks cannot trigger a missed-call SMS.
6. Fail closed on non-inbound voice directions.
7. Add failing tests for SignalWire Space URL origin restrictions, then reject non-SignalWire hosts and URL credentials/path/query/fragment.
8. Run focused tests, then the full suite.

### Task 3: Incorporate independent review findings

**Objective:** Resolve any additional blocking security/spec/hygiene findings from two read-only reviewers.

**Files:** Exact paths depend on evidence.

1. Triage every reviewer finding as blocking, important, or non-blocking.
2. Add a failing regression test for each accepted code defect.
3. Apply the smallest safe fix.
4. Re-run focused and full tests.
5. Record deferred production-only gaps explicitly; do not represent the local core as deploy-ready.

### Task 4: Refresh canonical project state

**Objective:** Remove stale branch/path/test-count claims before promoting to `main`.

**Files:**
- Modify: `PRD-text_back.md`
- Modify: `README.md`
- Modify: `NEXT-SESSION.md`
- Modify: `SESSION-NOTES.md`
- Modify: `/home/mdriles/Obsidian/Hermes Command Center/18_Projects/text_back — PRD.md` if present
- Append: `/home/mdriles/Obsidian/Hermes Command Center/09_Agent_Logs/Hermes Work Log.md`

1. Set piclaw `/home/mdriles/projects/text_back` and branch `main` as canonical after promotion.
2. Replace stale 111/142 counts with the final verified count.
3. State precisely that no credentials, webhook attachment, deployment, live message, or customer traffic was added.
4. Add the 2026-08-27 reconciliation evidence and remaining human/live gates.
5. Keep secrets and the purchased number out of Git and Obsidian.

### Task 5: Final verification and promotion

**Objective:** Make local and remote `main` identical with proof.

1. Run `.venv/bin/pytest tests/`.
2. Run `git diff --check`, `pip check`, `compileall`, package/import smoke, demo JavaScript syntax validation, and a redacted secret scan.
3. Inspect the complete final diff and repository status.
4. Commit the reconciliation fixes on the isolated branch.
5. Fast-forward `/home/mdriles/projects/text_back/main` to the verified branch; never force-push.
6. Push `main` to `origin`.
7. Verify `local main HEAD == origin/main` and report the origin URL and matching hashes.

**Hard stop:** Do not add credentials, attach webhooks, deploy, send SMS, route calls, change the purchased number, or incur telecom spend during this plan.
