"""Provider-agnostic calendar layer.

`calendar_stub.CalendarStub` stays in its historical module (15+ import
sites); this package re-exports it for new code alongside the protocol and
factory.
"""

from text_back.calendar_stub import CalendarStub, slot_end
from text_back.calendars.factory import calendar_from_config
from text_back.calendars.protocol import CalendarProvider, CalendarProviderError

__all__ = [
    "CalendarProvider",
    "CalendarProviderError",
    "CalendarStub",
    "calendar_from_config",
    "slot_end",
]
