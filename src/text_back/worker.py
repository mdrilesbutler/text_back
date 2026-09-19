"""Lifespan-owned background processing; each lane fails independently."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from text_back.delivery import run_due_deliveries
from text_back.followup import run_due_followups
from text_back.sms import run_due_sms
from text_back.inbox import run_due_inbound
from text_back.reconnect import maintain_credentials
from text_back.booking_jobs import run_due_bookings


def run_once(state):
    now = state.now_provider() if state.now_provider else datetime.now(timezone.utc)
    lanes = {
        'calendar_credentials': lambda: maintain_credentials(state),
        'inbound': lambda: run_due_inbound(state),
        'bookings': lambda: run_due_bookings(state),
        'followups': lambda: run_due_followups(store=state.store, telecom=state.telecom,
            policy=state.followup_policy, business_name=state.business_name,
            business_number=state.business_number, now=now),
        'sms': lambda: run_due_sms(store=state.store, telecom=state.telecom, now=now,
            policy=state.followup_policy, callback_base_url=state.public_base_url),
        'handoffs': lambda: run_due_deliveries(store=state.store, transport=state.delivery_transport,
            policy=state.delivery_policy, now=now),
    }
    errors = []
    for name, run in lanes.items():
        try:
            run()
        except Exception:
            errors.append(name)
            logging.getLogger(__name__).error('Background processing failed in %s', name)
    state.worker_errors = errors
    state.worker_last_run = now.isoformat()


async def _run(state, stop):
    state.worker_running = True
    try:
        while not stop.is_set():
            await asyncio.to_thread(run_once, state)
            try:
                await asyncio.wait_for(stop.wait(), timeout=state.worker_interval_seconds)
            except TimeoutError:
                pass
    finally:
        state.worker_running = False


@asynccontextmanager
async def lifespan(app):
    state = app.state
    stop = asyncio.Event()
    state.worker_task = asyncio.create_task(_run(state, stop))
    try:
        yield
    finally:
        # Do not cancel to_thread: cancellation cannot stop provider I/O.
        # Finish the current bounded request before closing its connection.
        stop.set()
        await state.worker_task
        if state.owns_store:
            state.store.conn.close()
