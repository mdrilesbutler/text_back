# {{Business Name}} — Recovered Revenue Brief

### {{Reporting period}}

**Bottom line first:** text_back contacted **{{contacted}}** missed callers, engaged **{{engaged}}**, qualified **{{qualified}}**, booked **{{booked}}** appointments, and has **{{completed}}** jobs verified complete. Verified recovered revenue is **${{verified_revenue}}**; booked-but-unverified pipeline is reported separately.

## Recovery Snapshot

| Outcome | Count | Rate | Evidence |
|---|---:|---:|---|
| Missed calls received | {{missed}} | — | unique `call_sid` |
| Initial texts sent | {{contacted}} | {{contact_rate}} | provider message IDs |
| Customers replied | {{engaged}} | {{reply_rate}} | inbound message IDs |
| Qualified leads | {{qualified}} | {{qualification_rate}} | required fields |
| Appointments booked | {{booked}} | {{booking_rate}} | Calendar event IDs |
| Human handoffs | {{handoffs}} | {{handoff_rate}} | handoff event IDs |
| Jobs completed | {{completed}} | {{completion_rate}} | CRM/manual proof |
| Verified recovered revenue | ${{verified_revenue}} | — | invoice/job-value source |

## Speed

- Median missed call → first SMS: **{{median_first_sms_seconds}} sec**
- Median first SMS → customer reply: **{{median_reply_minutes}} min**
- Median first reply → booking/handoff: **{{median_resolution_minutes}} min**
- After-hours share: **{{after_hours_percent}}%**

## What Drove Results

- **Best converting service:** {{service}}
- **Best converting time window:** {{time_window}}
- **Most common drop-off:** {{drop_off_stage}}
- **Most common handoff reason:** {{handoff_reason}}

## Conversations Needing Attention

1. {{lead reference}} — {{reason}} — {{recommended action}}
2. {{lead reference}} — {{reason}} — {{recommended action}}
3. {{lead reference}} — {{reason}} — {{recommended action}}

## What to Watch Next

- {{example: reply rate after 7 p.m.}}
- {{example: slots unavailable within requested window}}
- {{example: repeat handoffs for emergency language}}

## Recommended Adjustment

**One change only:** {{specific configuration/script/hours change}}
**Expected effect:** {{metric expected to improve}}
**Approval needed:** {{yes/no and owner}}

## Bottom Line

{{Two-to-four sentences: outcome, strongest evidence, largest leak, one next action. Never equate bookings with revenue.}}

## Evidence Appendix

- Calls: {{call event IDs / export path}}
- Messages: {{provider message IDs / export path}}
- Bookings: {{Calendar event IDs}}
- Completed jobs: {{CRM/manual evidence references}}
- Revenue values: {{invoice/job-value source references}}
- Generated: {{timestamp and version}}

*Transactional operational report. Revenue is counted only when completion and value are supported by client evidence.*
