"""The example conversation on the Messages page, produced by the real policy code.

Nothing here writes a customer-facing sentence. A script of customer replies is
run through ``handle_voice_event`` and ``handle_sms_event`` against an
in-memory store, a fake telecom and the stub calendar, exactly as a webhook
would, and the texts the outbox would send come back as bubbles tagged with
the template key they were rendered from. The page therefore cannot show a
hand-off, a re-prompt or a booking the product would not actually make.

Nothing is sent: the store is in memory, the telecom is ``FakeTelecom`` and
the operator notifier is the in-memory fake.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from text_back.calendar_links import CalendarLinks
from text_back.calendar_stub import CalendarStub
from text_back.calendars.protocol import CalendarProviderError
from text_back.followup import FollowupPolicy, followup_sms
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.handoff import FakeHandoffNotifier
from text_back.messages import FIELD_PROMPT_KEYS, REQUIRED_FIELDS, MessageSet, parse_fields, validate_templates
from text_back.policy import WIRING_MODE_FORWARDED, help_sms
from text_back.store import Store
from text_back.telecom import FakeTelecom, OutboundSms

# Made-up numbers (555 range, never routable): the customer and the business' texting line.
CUSTOMER_NUMBER = "+15550100123"
TEXTING_NUMBER = "+15550100456"
HANDOFF_DESTINATION = "sample-operator"
LINK_SECRET = "sample-secret"
APPOINTMENT_MINUTES = 60

EVENT_MISSED_CALL = "Missed call"
EVENT_BOOKED = "Booked on the calendar"
EVENT_STOPS = "Texting stops here"

# Outbox kind -> template keys it can have been rendered from. A kind with one
# key maps directly; a kind with several is resolved by rendering each candidate
# and comparing it with the body that was actually queued.
KIND_KEYS: dict[str, tuple[str, ...]] = {
    "missed_call_intro": ("intro",),
    "followup": ("followup_1", "followup_2"),
    "field_prompt": tuple(FIELD_PROMPT_KEYS[f] for f in FIELD_PROMPT_KEYS),
    "preferred_time_reprompt": ("preferred_time_reprompt",),
    "phone_reprompt": ("phone_reprompt",),
    "email_reprompt": ("email_reprompt",),
    "slot_unavailable": ("slot_unavailable",),
    "booking_error": ("booking_error",),
    "booking_confirmation": ("booking_confirmation",),
    "handoff_ack": ("handoff_ack", "handoff_ack_safety"),
    "opt_in_ack": ("opt_in",),
    "help": ("help",),
    "opt_out_ack": ("opt_out_ack",),
}


@dataclass(frozen=True)
class Bubble:
    side: str  # "customer" | "textback" | "event"
    text: str
    key: str | None = None


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    script: tuple[str, ...]
    # Parallel to ``script``: the optional question a line answers ("phone" /
    # "email"), or None. Lines for questions the owner does not ask are dropped.
    needs: tuple[str | None, ...] = ()
    calendar_free: bool = True
    calendar_fails: bool = False
    followups: bool = False

    def lines(self, asked: set[str]) -> tuple[str, ...]:
        needs = self.needs or (None,) * len(self.script)
        return tuple(line for line, need in zip(self.script, needs) if need is None or need in asked)


class _BusyCalendar(CalendarStub):
    """Every slot is taken, so a booking is declined and the customer is re-asked."""

    def is_free(self, start: datetime, end: datetime) -> bool:
        return False


class _FailingCalendar(CalendarStub):
    """The calendar cannot be reached, so no booking is made and the customer is told so."""

    def is_free(self, start: datetime, end: datetime) -> bool:
        raise CalendarProviderError("stub calendar unavailable")


def build_messages(templates: dict[str, str], asked: set[str]) -> MessageSet:
    """The MessageSet the app would load from a messages file with these overrides.

    The ``fields`` key decides which questions are asked; it is rebuilt from the
    required questions plus ``asked``, keeping the owner's own order where one
    was saved.
    """
    overrides = dict(templates)
    saved = overrides.get("fields")
    try:
        order = list(parse_fields(saved)) if saved else list(REQUIRED_FIELDS)
    except Exception:  # an unusable saved order falls back to the shipped order
        order = list(REQUIRED_FIELDS)
    wanted = set(REQUIRED_FIELDS) | {f for f in asked if f in FIELD_PROMPT_KEYS}
    order = [f for f in order if f in wanted]
    order += [f for f in FIELD_PROMPT_KEYS if f in wanted and f not in order]
    overrides["fields"] = ", ".join(order)
    return MessageSet(validate_templates(overrides))


def _template_key(sent: OutboundSms, messages: MessageSet, business_name: str) -> str | None:
    candidates = KIND_KEYS.get(sent.kind, ())
    if len(candidates) == 1:
        return candidates[0]
    for key in candidates:
        if key == "help":
            rendered = help_sms(business_name, "", sent.from_number, messages)
        else:
            rendered = messages.render(key, business_name=business_name)
        if rendered == sent.body:
            return key
    return None


def run_script(
    *,
    templates: dict[str, str],
    business_name: str,
    asked: set[str],
    script: tuple[str, ...],
    now: datetime,
    public_base_url: str,
    tz_name: str,
    calendar_free: bool = True,
    calendar_fails: bool = False,
) -> list[Bubble]:
    """Run one missed call and the scripted replies through the real handlers."""
    messages = build_messages(templates, asked)
    store = Store(":memory:")
    store.calendar_links = CalendarLinks(public_base_url, LINK_SECRET)
    telecom = FakeTelecom()
    calendar_class = _FailingCalendar if calendar_fails else CalendarStub if calendar_free else _BusyCalendar
    calendar = calendar_class(timezone_name=tz_name)
    # No quiet hours: the example must show every text whatever the clock says.
    policy = FollowupPolicy(delays_minutes=(120, 1440), expiry_minutes=4320,
                            quiet_start=time(0, 0), quiet_end=time(0, 0), timezone_name=tz_name)
    notifier = FakeHandoffNotifier()

    bubbles: list[Bubble] = [Bubble("event", EVENT_MISSED_CALL)]
    sent_so_far = 0

    def drain() -> None:
        nonlocal sent_so_far
        for sent in telecom.outbound[sent_so_far:]:
            bubbles.append(Bubble("textback", sent.body, _template_key(sent, messages, business_name)))
            if sent.kind == "booking_confirmation":
                bubbles.append(Bubble("event", EVENT_BOOKED))
        sent_so_far = len(telecom.outbound)

    handle_voice_event(
        store=store, telecom=telecom, call_sid="sample", call_status="no-answer",
        from_number=CUSTOMER_NUMBER, to_number=TEXTING_NUMBER, wiring_mode=WIRING_MODE_FORWARDED,
        business_name=business_name, followup_policy=policy, now=now, messages=messages,
    )
    drain()
    for index, line in enumerate(script, start=1):
        bubbles.append(Bubble("customer", line))
        handle_sms_event(
            store=store, calendar=calendar, telecom=telecom, handoff_notifier=notifier,
            handoff_destination=HANDOFF_DESTINATION, message_sid=f"sample-{index}",
            from_number=CUSTOMER_NUMBER, to_number=TEXTING_NUMBER, body=line,
            business_name=business_name, timezone_name=tz_name,
            appointment_duration_minutes=APPOINTMENT_MINUTES, business_contact="",
            now=now, messages=messages,
        )
        drain()
    store.conn.close()
    return bubbles


def followup_bubbles(templates: dict[str, str], business_name: str, asked: set[str]) -> list[Bubble]:
    """The two reminders a silent customer gets, then the point texting stops."""
    messages = build_messages(templates, asked)
    return [
        Bubble("textback", followup_sms(business_name, 1, messages), "followup_1"),
        Bubble("textback", followup_sms(business_name, 2, messages), "followup_2"),
        Bubble("event", EVENT_STOPS),
    ]


def render_scenario(
    name: str,
    *,
    templates: dict[str, str],
    business_name: str,
    asked: set[str],
    now: datetime,
    public_base_url: str,
    tz_name: str,
) -> list[Bubble]:
    scenario = SCENARIOS[name]
    bubbles = run_script(
        templates=templates, business_name=business_name, asked=asked, script=scenario.lines(asked),
        now=now, public_base_url=public_base_url, tz_name=tz_name,
        calendar_free=scenario.calendar_free, calendar_fails=scenario.calendar_fails,
    )
    if scenario.followups:
        bubbles.extend(followup_bubbles(templates, business_name, asked))
    return bubbles


# Customer lines are made up. The preferred time is relative ("Thursday at 10")
# so it parses as a future slot for any ``now``; "10" with no am/pm is morning
# by the product's own rule.
_BOOKING_LINES = ("Tree removal", "12 Oak St, Charlotte", "Thursday at 10", "Dana Lee", "YES", "dana@example.com")
_BOOKING_NEEDS = (None, None, None, None, "phone", "email")

SCENARIOS: dict[str, Scenario] = {
    "booked": Scenario(
        name="booked", label="A customer books", script=_BOOKING_LINES, needs=_BOOKING_NEEDS,
    ),
    "unclear": Scenario(
        name="unclear", label="A reply the assistant cannot use",
        script=("Tree removal", "12 Oak St, Charlotte", "Sometime next week", "Thursday at 10", "Dana Lee",
                "Use my work phone", "YES", "alex at example", "dana@example.com"),
        needs=(None, None, None, None, None, "phone", "phone", "email", "email"),
    ),
    "noreply": Scenario(name="noreply", label="No reply", script=(), followups=True),
    "failed": Scenario(
        name="failed", label="The calendar cannot be reached", script=_BOOKING_LINES, needs=_BOOKING_NEEDS,
        calendar_fails=True,
    ),
    "steps_back": Scenario(
        name="steps_back", label="The customer asks for a call back",
        script=("Tree removal", "Can you have someone call me instead?"),
    ),
    "safety": Scenario(
        name="safety", label="Something dangerous",
        script=("A branch came down on a power line",),
    ),
    "keywords": Scenario(name="keywords", label="START, HELP and STOP", script=("START", "HELP", "STOP")),
}
