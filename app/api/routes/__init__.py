from app.api.routes.auth import router as auth_router
from app.api.routes.bookings import router as bookings_router
from app.api.routes.movies import router as movies_router
from app.api.routes.showtimes import router as showtimes_router

__all__ = ["auth_router", "bookings_router", "movies_router", "showtimes_router"]
