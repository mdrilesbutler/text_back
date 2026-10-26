"""Private copy of the candidate C preview whose calendar reports a connected Google account.

usage (from the worktree root): .venv/bin/python <this> <fresh data dir> 127.0.0.1 <port>
Imports docs/notes/ui-compare-c/preview.py (which seeds through the stub calendar), then swaps
app.state.calendar for a Google-shaped fake and patches calendar_status. Never contacts Google.
"""
import importlib.util, json, sys
from datetime import datetime, timezone

data, host, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
assert port not in (8000, 8443, 8765, 8003, 8766, 443)
sys.argv = ["preview.py", data, host, str(port)]
spec = importlib.util.spec_from_file_location(
    "c_preview", "/home/ubuntu/projects/text_back-ui-c/docs/notes/ui-compare-c/preview.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

from text_back import client_settings, portal_status  # noqa: E402


class FakeGoogleCalendar:
    provider_name = "google"

    def __init__(self):
        self.calendar_id = "owner@example.com"
        self.reads = 0

    def busy_intervals(self, time_min, time_max):
        self.reads += 1
        return []


state = mod.state
state.calendar = FakeGoogleCalendar()
now = datetime.now(timezone.utc)
state.store.set_setting("calendar_choices", json.dumps([
    {"id": "owner@example.com", "summary": "Oak & Pine jobs", "primary": True},
    {"id": "crew@example.com", "summary": "Crew schedule"}]), now=now)
state.store.set_setting("google_calendar_id", "owner@example.com", now=now)


def fake_status(st):
    return {"provider": "google", "status": "ready", "calendar_id": getattr(st.calendar, "calendar_id", ""),
            "can_connect": True}


client_settings.calendar_status = fake_status
portal_status.calendar_status = fake_status

# The connected account is a demo: tag the calendar cards Example like every other seeded item.
mod.state.preview_example_setup = set(getattr(mod.state, "preview_example_setup", ()) or ()) | {"calendar"}

if __name__ == "__main__":
    mod.uvicorn.run(mod.wrapper, host=host, port=port, log_level="warning")
