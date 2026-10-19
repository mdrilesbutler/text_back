# Recover requirements from Michael, 2026-10-19

Captured verbatim-in-spirit from the live pilot session so nothing is lost.
Each item becomes its own small layer, in this order, after the pilot proof.

1. **No allowlist in the product.** Every caller gets the recovery text; the
   only exclusion is the STOP list. Done 2026-10-19: `TEXT_BACK_PILOT_RECIPIENTS`
   was removed from the runtime config (the code already treated "unset" as
   "everyone"); the empty allowlist had been a pilot safety setting.
2. **Natural day-and-time replies** ("this wednesday at 2", "next thursday at
   4:00"). Done 2026-10-19 in PR #13 (`preferred_time.py`), deployed as 41cf1ca.
3. **Message copy must be customizable per client**, including the first
   text. Michael asked for "Reply STOP to opt out" to be removed; carriers and
   the 10DLC reviewers require opt-out wording in the first automated text, so
   the suffix text becomes editable but the word STOP stays mandatory.
   "[SignalWire Free Trial]" is stamped by the carrier until the number is
   registered (needs the EIN) and cannot be removed in code.
4. **Client GUI with login** where the client types their own message copy.
5. **Calendar links in the confirmation text**: Google, Outlook and an iCal
   (.ics) link.
6. **Information gathering** collects name, address, phone and email (today:
   service, location, time, name).
7. **A calendar invite emailed to the customer** after booking.
8. Everything above is customizable per client (copy, fields, links).

Open decisions recorded with the layer that needs them, not here.
