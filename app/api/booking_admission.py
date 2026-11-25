import asyncio
import logging
import os

from fastapi.responses import JSONResponse

from app.infrastructure.observability import BOOKING_ADMISSION, BOOKING_IN_FLIGHT, is_booking_post

logger = logging.getLogger(__name__)


class BookingAdmissionMiddleware:
    def __init__(self, app, limit: int, metrics: bool = False):
        self.app = app
        self.limit = limit
        self.metrics = metrics
        self.in_flight = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.limit or not is_booking_post(scope):
            return await self.app(scope, receive, send)
        # A worker's event loop cannot interleave the test and increment.
        if self.in_flight >= self.limit:
            scope["cinema.booking_overloaded"] = True
            if self.metrics:
                BOOKING_ADMISSION.labels("rejected", os.getpid()).inc()
            response = JSONResponse({"detail": "Booking capacity is full", "code": "booking_overloaded"},
                                    status_code=503, headers={"Retry-After": "1"})
            return await response(scope, receive, send)
        self.in_flight += 1
        try:
            if self.metrics:
                BOOKING_ADMISSION.labels("accepted", os.getpid()).inc()
                BOOKING_IN_FLIGHT.inc()
            handler = asyncio.create_task(self.app(scope, receive, send))
            try:
                return await asyncio.shield(handler)
            except asyncio.CancelledError:
                # Cancelling a request task cannot stop a running synchronous DB operation.
                # Keep its session and permit alive until the inner ASGI call has cleaned up.
                while not handler.done():
                    try:
                        await asyncio.shield(handler)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if not handler.cancelled() and (error := handler.exception()) is not None:
                    logger.error("Booking failed while the request was cancelled", exc_info=error)
                raise
        finally:
            self.in_flight -= 1
            if self.metrics:
                BOOKING_IN_FLIGHT.dec()

