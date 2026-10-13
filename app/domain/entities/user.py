from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    id: int | None
    email: str
    password_hash: str
    full_name: str
    role: str = "user"
    created_at: datetime | None = None
