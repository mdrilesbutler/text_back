# text_back product model — Recovery OS for field-service calls

**Decision date:** 2026-08-20
**Owner:** Michael Riley / Fluxworks
**Inputs:** Chris Koerner video/playbook, Podium, Hatch, Goodcall, and Tra’s Morning Macro Brief format
**Positioning:** Sell recovered jobs and faster response—not “AI agents.”

## One-sentence product

**text_back recovers missed and after-hours calls, qualifies the customer by text, books only against real availability, routes exceptions to a human, and proves the revenue recovered in a short evidence-backed brief.**

## The best parts we are taking

### 1. Koerner — sell the diagnosis, then the outcome

The assessment is the entry point; speed-to-lead is the high-ROI implementation offer.[2] For text_back this becomes:

1. `TB-ASSESS` — quantify the missed-call leak.
2. `TB-RECOVER` — install missed-call SMS recovery and calendar booking.
3. `TB-CARE` — monitor, tune, and report recovered outcomes.

**Keep:** pain-first discovery, fast written diagnosis, clear implementation upsell, recurring care.
**Reject:** generic “we build any AI agent” consulting.

### 2. Podium — missed-call rescue + conversation continuity

Podium automatically texts missed callers and continues the conversation 24/7.[3] It also keeps call transcripts/summaries for team context.[3] Its broader automation suite adds appointment reminders, review requests, referrals, and re-engagement.[4]

**Take now:**
- Instant missed-call text.
- One continuous customer timeline.
- Conversation summary for the operator.
- Simple lead status: `new → engaged → qualified → booked → handed_off → lost`.

**Take later:**
- Appointment reminders.
- Review request only after a completed job and explicit transactional basis.
- Referral request after a verified positive review.

**Reject for MVP:** payments, marketing blasts, website retargeting, and “all-in-one inbox” sprawl.

### 3. Hatch — speed to conversion, not merely speed to reply

Hatch’s strongest product idea is that the bar is no longer fast first contact; it is **lead arrival to booked appointment**.[5] It uses persistent, event-triggered sequences across channels until the customer responds.[5] Its call-handling product combines real-time availability, booking/rescheduling, scripts, tone, rules, and escalation paths.[6]

**Take now:**
- Measure `call_missed_at → first_sms_at → first_reply_at → qualified_at → booked_at`.
- Continue a bounded follow-up sequence when a missed caller does not reply.
- Stop instantly on response, opt-out, booking, handoff, expiry, or max attempts.
- Human handles nuance; automation handles speed and consistency.

**Take next:**
- Estimate follow-up and no-show recovery as separate, consent-safe journeys.
- CRM / lead-source adapters through a narrow event interface.

**Reject for MVP:** email campaigns, aged-lead marketing, large command center, and multi-channel orchestration before the missed-call wedge works.

### 4. Goodcall — structured voice intake + logic + routing

Goodcall’s useful product patterns are structured form/logic flows, human routing, calendar integration, reminders, and reschedule/cancel paths.[9][10][11] Goodcall also demonstrates a transparent, scalable small-business price ladder rather than enterprise-only custom pricing.[9]

**Take now (SMS):**
- Deterministic form fields and logic branches.
- Explicit human handoff destinations by issue type.
- Reschedule/cancel paths after booking.
- Known-caller lookup and prior-context summary.

**Take later (Voice add-on):**
- After-hours/overflow AI voice receptionist.
- Directory routing (sales / service / emergency / existing appointment).
- Voice transcript + concise operator summary.

**Reject for MVP:** replacing every inbound call. text_back begins with missed-call recovery because it is cheaper, safer, and easier to prove.

### 5. Tra’s brief — outcome reporting with evidence, not a vanity dashboard

The supplied *Tra’s Morning Macro Brief* is unrelated in subject matter, but its **reporting structure is excellent**:

- Snapshot first.
- Explain the drivers, not just totals.
- “What to watch” next.
- Bottom line.
- Source appendix / evidence trail.

text_back will use that structure for a **Recovered Revenue Brief** instead of building a dashboard owners never open.

## The combined product

### Product name

**text_back — Missed-Call Recovery OS**

### Core promise

> Missed call to qualified customer in under a minute—then a real booking or a clean human handoff.

### Core workflow

```text
Existing business number
        ↓ (conditional forward after no-answer/busy)
text_back claims call_sid exactly once
        ↓
Immediate branded SMS
        ↓
Deterministic qualification (one question at a time)
        ↓
┌────────────────┬───────────────────┬────────────────┐
│ Real slot found│ Complex/urgent    │ No response    │
│ Calendar event │ Human handoff     │ Bounded follow │
│ + confirmation │ + concise summary │ up then expire │
└────────────────┴───────────────────┴────────────────┘
        ↓
Outcome event + Recovered Revenue Brief
```

## Product editions

| Edition | Buyer outcome | Included | Launch posture |
|---|---|---|---|
| **Recover** | Rescue missed calls | Missed-call SMS, qualification, booking, handoff, timeline, outcome brief | **MVP / flagship** |
| **Answer** | Cover after-hours/overflow calls | Voice intake, routing, transcript, SMS continuation | Later add-on |
| **Grow** | Recover existing demand | Estimate follow-up, reminders, no-show recovery, review requests | Later, consent-scoped |

Do not build **Answer** or **Grow** until **Recover** passes real-phone verification and can prove outcomes.

## Launch packaging

| SKU | Deliverable | Recommended launch price |
|---|---|---:|
| `TB-ASSESS` | 45-minute leak assessment + 48-hour plan | $500 (credit toward install) |
| `TB-RECOVER` | Forwarding setup, SMS flow, Calendar, live test | $1,500 one-time |
| `TB-CARE` | Monitoring, adjustments, monthly outcome brief | $299/month |
| `TB-ANSWER` | Voice receptionist add-on | Price after pilot cost data |
| `TB-GROW` | Follow-up journeys add-on | Price after consent + efficacy data |

Why $299/month: Goodcall’s self-serve voice plans establish a low-cost software anchor, while text_back is a **managed, installed outcome service** with number wiring, calendar integration, monitoring, and reporting.[9] We must earn the premium by proving recovered jobs—not by adding feature count.

## Required MVP capabilities (Recover)

### P0 — before pilot

- [x] Local fail-closed Twilio-compatible webhook signature validation and tests.
- [x] Local SignalWire Compatibility boundary: validate `X-SignalWire-Signature` against the exact public URL and return cXML where required. Live attachment/testing remains gated.
- [x] Exactly-once missed-call trigger (`call_sid`).
- [x] Forwarded and managed wiring modes.
- [x] STOP / HELP deterministic policy.
- [x] One-question-at-a-time field collection.
- [x] Voicemail-style forwarded-call response (`<Say>` + `<Hangup>`; no retained recording).
- [x] Parse explicit requested times and book only after a free/busy recheck (local Calendar stub; live Google adapter remains gated).
- [x] Human handoff state + operator alert payload (local in-memory notifier; external delivery remains gated).
- [x] Append-only outcome events for the implemented lead lifecycle, with stable evidence IDs and retry idempotency.
- [ ] Bounded no-response sequence (suggested: immediate, +15m, next business morning; configurable).
- [ ] Recovered Revenue Brief generator.

### P1 — after first live client

- [ ] Customer reschedule/cancel via deterministic keywords/flow.
- [ ] Appointment reminders.
- [ ] Operator-facing conversation summary.
- [ ] Lead-source tag and job-value estimate.
- [ ] Monthly value attribution with evidence links/IDs.

### P2 — only after Recover proves conversion

- [ ] AI voice overflow / after-hours answering.
- [ ] Directory routing.
- [ ] Estimate follow-up and no-show recovery.
- [ ] Review/referral journey.
- [ ] ServiceTitan / Jobber / Housecall Pro adapters.

## Lead outcome model

Every contact has a current state and an append-only event history:

```text
missed
  → contacted
  → engaged
  → qualified
  → booked
  → completed (external/manual proof)

Any state may → handed_off | opted_out | expired | lost
```

### Minimum event vocabulary

- `call.missed`
- `sms.initial_sent`
- `sms.customer_replied`
- `lead.field_captured`
- `lead.qualified`
- `lead.handoff_requested`
- `calendar.slot_checked`
- `calendar.event_created`
- `appointment.confirmed`
- `followup.sent`
- `lead.expired`
- `job.completed` (external/manual evidence only)
- `revenue.attributed` (requires job value source)

## Reporting model — Recovered Revenue Brief

Do **not** claim revenue from messages or bookings alone.

### Evidence levels

| Label | Evidence |
|---|---|
| **Contacted** | Initial SMS provider message ID |
| **Engaged** | Inbound reply provider ID |
| **Qualified** | Required fields captured |
| **Booked** | Google Calendar event ID |
| **Completed** | Client CRM/manual completion proof |
| **Revenue recovered** | Completed + client-supplied invoice/job value |

The monthly brief must separate these levels. A booked appointment is pipeline, not revenue.

## Guardrails / differentiation

1. **Keep the existing number** — conditional forwarding default.
2. **Booking truth is deterministic** — no event ID, no booked claim.
3. **Human handoff is a first-class outcome**, not a failure.
4. **No infinite nurture** — bounded attempts, consent, quiet hours, expiry.
5. **No marketing in the transactional flow.** Grow journeys require separate consent/policy.
6. **No fake ROI.** Report evidence tier and source IDs.
7. **No platform sprawl.** Integrate with the calendar/CRM; do not replace them.

## Competitive position

| Product | Their strength | text_back answer |
|---|---|---|
| Podium | Broad all-in-one local-business lead platform | Narrower, cheaper managed missed-call wedge; keep current stack |
| Hatch | Deep AI CSR + persistent multichannel journeys | Recovery-first for small operators; add journeys only after proof |
| Goodcall | Self-serve AI phone receptionist + logic flows | SMS-first safety/cost; optional managed voice later |
| text_back | Existing number + deterministic booking + evidence-backed ROI | Own this wedge completely |

## Decision

Build **Recover**, report it like Tra’s brief, sell it through Koerner’s assessment ladder. Borrow Podium/Hatch/Goodcall mechanics only where they improve **missed call → booked or handed off**. Everything else waits.

## Sources

[2] https://newsletter.chrisjkoerner.com/p/easiest-way-to-make-money-with-ai-1d32
    > "Speed-to-lead agents ($1,500 to $3,000)."
    > "The assessment is your foot in the door and already a huge money maker in itself."
[3] https://www.podium.com/product/phones
    > "When you miss a call, the customer will automatically get a text and our AI Employee will then keep the conversation going, any time of day or night."
    > "Record and transcribe calls automatically with AI, so your team has all the context they need to provide a great customer experience."
[4] https://www.podium.com/product/automations
    > "Send a text automatically to missed callers, re-engaging them and saving a proven 58% of leads from moving on to the next business."
    > "From appointment and payment reminders to review invites, set them up once, and watch them work while you tackle the rest of your tasks."
[5] https://www.usehatchapp.com/solutions/speed-to-lead
    > "The new bar is form fill to booked—and AI handles that complete conversation."
    > "Campaigns trigger the moment leads arrive—SMS, email, calls—and persist until they respond. No manual chasing required."
[6] https://www.usehatchapp.com/solutions/call-handling
    > "AI checks real-time availability, presents options, and books or reschedules appointments instantly—no callbacks or delays."
    > "AI follows your scripts, tone, rules, and escalation paths—delivering professional, brand-aligned communication at any volume."
[9] https://www.goodcall.com/pricing
    > "Flexible pricing built for businesses of all sizes. Start small and scale as your operations grow."
    > "Handle calls without worrying about minutes or token limits."
[10] https://www.goodcall.com/voice-ai/ai-voice-agent-for-appointment-booking
    > "Call routing when human assistance is required"
    > "Allows customers to reschedule or cancel if needed"
[11] https://www.goodcall.com/post/introducing-goodcall-3-speed-accuracy-and-enhanced-call-automation
    > "Enhanced Logic Flows for Customized Call Handling"
    > "Directory-Based Call Routing"
