import re
from urllib.parse import urlsplit


def validate_database_name(name: str, owner: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+", owner):
        raise ValueError("Invalid experiment owner")
    if not re.fullmatch(r"cinema_phase2_" + re.escape(owner) + r"_[a-z0-9_]+", name) or len(name) > 63:
        raise ValueError("Database is not owned by this experiment")
    return name


def validate_admin_url(url: str) -> str:
    parsed = urlsplit(url.replace("postgresql+psycopg:", "postgresql:", 1))
    if parsed.scheme not in {"postgresql", "postgres"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.path != "/postgres":
        raise ValueError("Use a loopback PostgreSQL admin URL pointing to /postgres")
    # libpq query parameters can override host/dbname, so disallow them.
    if parsed.query or parsed.fragment:
        raise ValueError("Admin URL must not override connection parameters")
    return url
