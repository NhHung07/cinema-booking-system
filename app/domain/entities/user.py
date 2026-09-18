from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    id: int | None
    email: str
    password_hash: str
    full_name: str
    created_at: datetime | None = None
