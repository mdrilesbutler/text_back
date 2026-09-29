# text_back landing page — design sources

Working sources for the marketing landing page, saved from the 2026-09-11/12
design session. Not part of the service; nothing here is imported by code.

- `Main.dc.html` / `Mobile.dc.html` — current page (v6), design-canvas format
- `V1..V5.dc.html` — every earlier iteration, kept on purpose (Michael: keep all iterations)
- `DirectionA/B/C.dc.html` — the three original directions
- `Workflow.dc.html` — animated pipeline diagram
- `canvas.json` — artboard layout for the Claude Design canvas
- `site/` — plain-HTML build deployed to https://text-back-landing.vercel.app
  (`site/versions/` holds every version; gallery at `/versions/`)

Canvas: https://claude.ai/code/artifact/f21b8c65-5b67-4e27-9130-cbbfd09b991b
Vercel project: `text-back-landing` (mdrilesbutler). Deploy = `vercel deploy --prod --yes` from `site/`.
Rule: a new pass is ADDED as vN+1, never replaces the previous version.
