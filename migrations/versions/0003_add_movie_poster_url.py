"""Thêm cột poster_url cho bảng movies

Revision ID: 0003_add_movie_poster_url
Revises: 0002_add_user_role
Create Date: 2026-10-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_movie_poster_url"
down_revision: str | None = "0002_add_user_role"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("poster_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "poster_url")

