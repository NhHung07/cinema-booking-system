"""Các router cho API routes (analytics, auth, bookings, movies, showtimes)."""

from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.bookings import router as bookings_router
from app.api.routes.movies import router as movies_router
from app.api.routes.showtimes import router as showtimes_router

__all__ = [
    "analytics_router",
    "auth_router",
    "bookings_router",
    "movies_router",
    "showtimes_router",
]