"""Thêm cột role cho bảng users

Revision ID: 0002_add_user_role
Revises: 0001_initial
Create Date: 2026-10-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_user_role"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=32), server_default="user", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "role")

