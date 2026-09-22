"""Compatibility entrypoint; benchmark chính nằm trong benchmark/locustfile.py."""

from benchmark.locustfile import BookingJourneyUser, CatalogueUser, ConcurrentBookingUser

__all__ = ["BookingJourneyUser", "CatalogueUser", "ConcurrentBookingUser"]
