# text_back GTM model — Koerner / “easiest way to sell AI”

**Status:** Adopted as commercial packaging for text_back (Fluxworks catalog)
**Source video (requested):** https://www.youtube.com/watch?v=g4-3AxelI_Y
**Title:** *This Might Be the Easiest Way to Sell AI to Businesses* — Chris Koerner on The Koerner Office Podcast (oEmbed; ~71k views; ~4 months before 2026-08-20)
**Transcript note:** Full captions blocked from hermes-cloud IP. This doc is grounded in **matching public Koerner materials** (newsletters + related episode writeups), mapped onto text_back. Revisit when a full transcript is available.

## Thesis (what we are stealing)

SMB owners already feel the AI FOMO. They will not buy “an agent.” They buy **one painful hole plugged this week** — especially **speed-to-lead after hours**.[1][2]

text_back *is* that hole-plug for field-service: missed call → one SMS → book the job → calendar truth.

Do **not** sell “AI.” Sell: **“Never lose another after-hours call.”**

## The ladder (commercial model)

Adapted from the Koerner/Corey assessment ladder and the speed-to-lead upsell language in public writeups.[1][2]

| Stage | Offer | Price band (starting point) | What they get | text_back role |
|---|---|---|---|---|
| 0 | Free 15-min pain call / door knock | $0 | Listen only; capture 3 pains | Discovery |
| 1 | **AI ops assessment** | $500 → $1,000 | 45-min call → polished report in 48h | Report always includes missed-call / after-hours lead path |
| 2 | **Recover install** (flagship product) | $1,500 → $3,000 one-time | Number wiring (forwarded), SMS recovery, calendar book, STOP/HELP | Product delivery |
| 3 | **Managed monthly** | $200 → $500 / client / mo | Monitoring, hours tweaks, copy tweaks, monthly “leads recovered” report | Retainer |
| 4 | Adjacent upsells | $1k–$5k | Process cleanup, extra automations, knowledge GPT | Only after #2 is live |

**Rule:** Assessment is the foot in the door. text_back is the default Stage-2 SKU for field-service (arborists, guides, home services). Do not invent custom agents in Stage 2.

### Why this fits text_back economics

- COGS target stays inside Michael’s **$15/mo telecom ceiling** for pilot; client MRR ($200–$500) carries margin.[PRD]
- Product is config-reproducible (Fluxworks catalog) — sell the same engine, stamp client identity.[PRD]
- Deterministic policy (STOP/HELP/booking truth) keeps “AI” from becoming a liability story in sales.

## Positioning one-liners

**Owner-facing**
> When you miss a call, we text them back in under a minute, gather what they need, and put a real appointment on your calendar — without a new app.

**Agency-facing (Fluxworks)**
> One catalog SKU: missed-call recovery + booking. Attach to the client’s existing number. Recurring manage fee.

**Anti-positioning (never say)**
- “Custom AI agent platform”
- “We replace your receptionist with AGI”
- “Chatbot for your website” (different product)

## Discovery script (15–45 min)

Steal the question set from the public assessment playbook; bias to phone/leads.[1]

1. What does a typical Tuesday look like start to finish?
2. What’s the single biggest headache right now?
3. How do new jobs come in (phone / form / DM)?
4. What happens the moment a call is missed after 5pm or on Saturday?
5. How many calls do you think you miss per week? (guess is fine)
6. What’s a job worth on average?
7. Who answers the phone today? What happens when they’re on a job?
8. Do you use Google Calendar (or something else)?

**Close the assessment**
> I’ll send a one-page plan in 48 hours with one quick win you can run this week. If the missed-call math is ugly, the quick win is text_back.

## Assessment report skeleton (always)

1. Executive summary — their words on missed calls / chaos
2. Effort × impact matrix — missed-call recovery top-right for phone-led businesses
3. Recommended stack — **text_back** as primary; optional adjacencies only
4. 4-day quick-win plan
   - Day 1: forward/wiring mode decision + hours
   - Day 2: calendar share / SA
   - Day 3: live test call checklist
   - Day 4: go-live + STOP/HELP verify
5. Financial impact — `missed_calls/week × close_rate × job_value`
6. Next step CTA — install quote

## Math slide (use every time)

```
Missed calls / week:     ____
Close rate if reached:   ____%
Avg job value:           $____
Weekly leak:             missed × close × value
Monthly leak:            weekly × 4
text_back install:       $____ one-time
Managed:                 $____ / mo
Payback:                 often < 1 recovered job
```

## Sales objections → product truths

| Objection | Answer (product-backed) |
|---|---|
| “I don’t want a new phone number” | Default `wiring_mode=forwarded` — keep their number; CF only missed calls. |
| “I hate chatbots” | Deterministic field collect + human handoff; booking only with Calendar event ID. |
| “What about spam / compliance?” | STOP/HELP, quiet hours, 10DLC, no marketing in this flow. |
| “Will it double-text people?” | Idempotent webhooks on `call_sid`. |
| “Can AI go rogue and book junk?” | Policy engine owns booking truth; confirmation requires event ID. |

## Channel plan (cheap, local)

From the public “find first clients” playbook, adapted:[1][2]

1. **Door knock / job-site walk-up** field-service shops (best for Michael’s sales muscle).
2. **Free local “AI for small business” meetup** — 20 min value, no pitch; capture emails; book assessments.
3. **2–3 free pilot assessments** for testimonials, then $500 → $1k.
4. Peer groups / FB local entrepreneur groups.
5. After 3 live installs: case study one-pager (“X jobs recovered in 30 days”).

## Packaging for Fluxworks catalog

| Config field | Sold as |
|---|---|
| business_name, voice, SMS copy | Brand |
| wiring_mode | “Keep your number” vs “new number” |
| operator_phone | Owner mobile |
| calendar_id | Booking calendar |
| hours / quiet hours | When AI may text |
| appointment_duration + buffer | Job slot rules |
| handoff_destination | Human escape hatch |

SKU names (internal):
- `TB-ASSESS` — assessment
- `TB-RECOVER` — Recover go-live
- `TB-CARE` — monthly managed

## What we are NOT copying

- White-label HighLevel as the product (sponsor motion in Koerner content; different stack).[2]
- Corporate OpenClaw install retainers as the primary SKU (different ICP).[2][3]
- Building random custom agents before text_back is live for the client.

## Implementation hooks (product)

Already true in PRD/code and must stay true for this GTM:
- Deterministic STOP/HELP/consent/booking
- `wiring_mode` forwarded default
- Confirmation gated on Calendar event ID
- Catalog = config only

**Sales enablement artifacts to produce next**
- [ ] One-page leave-behind PDF
- [ ] Assessment Markdown template (`docs/gtm/assessment-template.md`)
- [ ] Stripe/payment links (Michael) for TB-ASSESS / TB-RECOVER / TB-CARE
- [ ] Case-study template after first pilot

## Sources

[1] Chris Koerner newsletter — *Easiest Way to Make Money with AI* (Corey assessment ladder, $1k assessment, speed-to-lead upsell $1.5k–$3k): https://newsletter.chrisjkoerner.com/p/easiest-way-to-make-money-with-ai-1d32
[2] Chris Koerner newsletter — *Easiest Way to Profit from AI Right Now* (after-hours lead death; AI employee answers calls/texts; white-label $200–$500/mo language): https://newsletter.chrisjkoerner.com/p/easiest-way-to-profit-from-ai-right-now-1534
[3] Chris Koerner newsletter — *Ways to Cash In on AI Agents Right Now* (local AI consulting $500/mo stack; AI support for SMBs): https://newsletter.chrisjkoerner.com/p/ways-to-cash-in-on-ai-agents-right-now
[4] Source video (captions unavailable here): https://www.youtube.com/watch?v=g4-3AxelI_Y

**Confidence:** High that the commercial pattern matches Koerner’s public “easiest sell AI to businesses” family of content. Medium that every beat of video `g4-3AxelI_Y` matches [1] until full captions land.
