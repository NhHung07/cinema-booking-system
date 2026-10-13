from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Movie:
    id: int | None
    title: str
    description: str
    duration_minutes: int
    release_date: date
    poster_url: str | None = None
    created_at: datetime | None = None
