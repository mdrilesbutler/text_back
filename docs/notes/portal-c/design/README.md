# Candidate C: the design that was judged (2026-10-26)

The winning mockup is **direction d1 "Spine", round 3**: `docs/notes/portal-c/mockups/d1/`, built from
`mockups/fixture.json` with `d1/build.py`, on candidate A's stylesheet (`mockups/_assets/portal.css`) plus
`d1/d1.css`. Every visible string is in `docs/notes/portal-c/copy-deck.md`.

## How it was judged

Same rubric (`docs/notes/ui-bakeoff-2026-10-26/judge-prompt.md`, unchanged), same blind Claude/Grok/Codex
panel on CLI logins with every `*_API_KEY` unset (Claude on `--model opus`). Each run compared the mockup's
screenshots with A's bake-off screenshots; X/Y labels were re-drawn per judge (`keys.json` in each folder).
Tools: `docs/notes/ui-compare-c/tools/{capture_static,build_packs,run_judges.sh,scores}.py`.

Before the first panel both directions went through design:design-critique, design:accessibility-review
and the anti-ui-slop-reviewer, and every finding was fixed.

## Scores (mockup vs A, /100)

| Round | Direction | Claude | Grok | Codex | Mean | A's mean in that run |
|---|---|---|---|---|---|---|
| 1 | d2 "Ledger" | 86 | 82 | 78 | 82.0 | 63.3 |
| 1 | d1 "Spine" | 88 | 86 | 80 | 84.7 | 63.3 |
| 2 | d1 + d2's best parts | 92 | 80 | 82 | 84.7 | 62.0 |
| 3 | d1 final | 92 | 88 | 88 | **89.3** | 61.3 |

Per criterion, round 3 (1–5):

| Judge | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 5 | 5 | 4 |
| Grok | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 3 |
| Codex | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 |

The loop stopped at the three-round limit, so this is the best design found, not a 100. What still cost points
in round 3, and where it is handled:
- Plain words (a2, 4 from all three): the Messages intro plus the network-notice line is long on a phone. Build.
- Phone navigation (c2, 4 from all three): Messages is still about 12 phone screens; the "Jump to" control helps but
  hides the page structure. Build keeps it; the length is the cost of showing every customer text.
- Honesty (d1): the booking bubble shows link labels while the count includes the full links, and the example
  forwarding check fed the real headline. Both fixed in the build.
- Finish (e2): heading under the bar while unsaved, a clipped bubble in the rail, "This phone" on desktop,
  two save scopes on Phone. Fixed in the build.

Scorecards: `round1-d1/`, `round1-d2/`, `round2-d1/`, `round3-d1/` (raw, as written, under their blind labels).
