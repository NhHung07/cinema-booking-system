import asyncio
import json
import threading

import pytest

from app.api.booking_admission import BookingAdmissionMiddleware


@pytest.mark.parametrize("termination", ["complete", "exception", "cancel"])
def test_booking_gate_rejects_before_handler_and_releases_slot(termination):
    async def exercise():
        entered, finish = asyncio.Event(), asyncio.Event()
        calls, messages = [], []

        async def downstream(scope, receive, send):
            calls.append(scope["path"])
            if len(calls) == 1:
                entered.set()
                await finish.wait()
                if termination == "exception":
                    raise RuntimeError("handler failed")

        async def send(message):
            messages.append(message)

        gate = BookingAdmissionMiddleware(downstream, limit=1)
        async def request(method, path):
            await gate({"type": "http", "method": method, "path": path}, None, send)

        first = asyncio.create_task(request("POST", "/bookings"))
        await entered.wait()
        await request("POST", "/bookings/")
        assert calls == ["/bookings"]
        assert messages[0]["status"] == 503
        assert (b"retry-after", b"1") in messages[0]["headers"]
        assert json.loads(messages[1]["body"])["code"] == "booking_overloaded"
        await request("GET", "/bookings")
        assert len(calls) == 2
        if termination == "cancel":
            first.cancel()
            finish.set()
            with pytest.raises(asyncio.CancelledError):
                await first
        elif termination == "exception":
            finish.set()
            with pytest.raises(RuntimeError):
                await first
        else:
            finish.set()
            await first
        await request("POST", "/bookings")
        assert len(calls) == 3
        assert gate.in_flight == 0

    asyncio.run(exercise())


def test_disabled_gate_does_not_hold_or_reject_a_request():
    calls = []

    async def downstream(scope, receive, send):
        calls.append(scope["method"])

    gate = BookingAdmissionMiddleware(downstream, limit=0)
    asyncio.run(gate({"type": "http", "method": "POST", "path": "/bookings"}, None, None))
    assert calls == ["POST"]
    assert gate.in_flight == 0


def test_cancelled_caller_keeps_slot_until_sync_work_and_cleanup_end():
    async def exercise():
        entered = asyncio.Event()
        finish = threading.Event()
        loop = asyncio.get_running_loop()
        calls, replies = [], []

        def blocking_work():
            loop.call_soon_threadsafe(entered.set)
            assert finish.wait(timeout=5)

        async def downstream(scope, receive, send):
            calls.append("start")
            try:
                await asyncio.to_thread(blocking_work)
            finally:
                calls.append("cleanup")

        async def send(message):
            replies.append(message)

        gate = BookingAdmissionMiddleware(downstream, limit=1)
        def request():
            return gate({"type": "http", "method": "POST", "path": "/bookings"}, None, send)

        caller = asyncio.create_task(request())
        await entered.wait()
        caller.cancel()
        try:
            await asyncio.sleep(0)
            assert calls == ["start"]
            await request()
            assert replies[0]["status"] == 503
            assert gate.in_flight == 1
        finally:
            finish.set()
            with pytest.raises(asyncio.CancelledError):
                await caller
        assert calls == ["start", "cleanup"]
        assert gate.in_flight == 0

    asyncio.run(exercise())
