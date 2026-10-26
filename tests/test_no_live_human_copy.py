"""Product principle (Michael, 2026-08-29): customers never get a live human.

The product exists because the operator cannot answer the phone. Customer-facing
copy must never promise a person or route the caller back to the business line
(the number that went unanswered in the first place). Escalation copy promises a
follow-up instead; the safety ack must still direct emergencies to 911.
"""

from text_back import policy
from text_back.cxml import forwarded_call_response
from text_back.followup import followup_sms

FORBIDDEN = (
    "business line",
    "reach a person",
    "for a person",
    "speak to a person",
    "talk to a human",
    "representative",
)


def _all_customer_copy() -> list[str]:
    return [
        policy.intro_sms("Mike's Tree Care"),
        policy.help_sms("Mike's Tree Care"),
        policy.help_sms("Mike's Tree Care", "", "+15553334444"),
        policy.opt_in_sms("Mike's Tree Care"),
        policy.handoff_ack_sms("safety"),
        policy.handoff_ack_sms("customer_requested"),
        policy.booking_error_sms(),
        followup_sms("Mike's Tree Care", 1),
        followup_sms("Mike's Tree Care", 2),
        forwarded_call_response("Mike's Tree Care", text_will_follow=True),
        forwarded_call_response("Mike's Tree Care", text_will_follow=False),
    ]


def test_no_customer_copy_promises_a_person_or_the_business_line():
    for copy in _all_customer_copy():
        lowered = copy.lower()
        for phrase in FORBIDDEN:
            assert phrase not in lowered, f"{phrase!r} found in: {copy}"


def test_handoff_acks_promise_a_follow_up_not_a_person():
    for reason in ("safety", "customer_requested"):
        assert "follow up" in policy.handoff_ack_sms(reason).lower()


def test_safety_ack_still_directs_emergencies_to_911():
    assert "911" in policy.handoff_ack_sms("safety")


def test_booking_error_keeps_the_customer_in_the_text_thread():
    copy = policy.booking_error_sms().lower()
    assert "no booking was made" in copy
    assert "call" not in copy


def test_default_handoff_acks_promise_only_the_business_not_a_named_person():
    # Hand-off details go to the configured operator destination, not necessarily the owner,
    # so the standard wording must not promise that "the owner" personally follows up.
    from text_back.messages import DEFAULT_TEMPLATES
    for key in ("handoff_ack", "handoff_ack_safety"):
        text = DEFAULT_TEMPLATES[key].lower()
        assert "the owner" not in text and "we'll follow up" in text, key
