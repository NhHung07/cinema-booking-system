from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Showtime:
    id: int | None
    movie_id: int
    start_time: datetime
    room_name: str
    created_at: datetime | None = None
