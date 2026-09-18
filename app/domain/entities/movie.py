from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Movie:
    id: int | None
    title: str
    description: str
    duration_minutes: int
    release_date: date
    created_at: datetime | None = None
