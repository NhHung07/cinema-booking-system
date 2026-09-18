"""create cinema booking schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-18 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_name", sa.String(length=100), nullable=False),
        sa.Column("row", sa.String(length=8), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.UniqueConstraint("room_name", "row", "number", name="uq_seats_room_row_number"),
    )
    op.create_index("ix_seats_room_name", "seats", ["room_name"], unique=False)

    op.create_table(
        "showtimes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("room_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_showtimes_movie_id", "showtimes", ["movie_id"], unique=False)
    op.create_index("ix_showtimes_start_time", "showtimes", ["start_time"], unique=False)
    op.create_index("ix_showtimes_room_name", "showtimes", ["room_name"], unique=False)
    op.create_index("ix_showtimes_movie_id_start_time", "showtimes", ["movie_id", "start_time"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("showtime_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["showtime_id"], ["showtimes.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)
    op.create_index("ix_bookings_showtime_id", "bookings", ["showtime_id"], unique=False)

    op.create_table(
        "booking_seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("showtime_id", sa.Integer(), nullable=False),
        sa.Column("seat_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["showtime_id"], ["showtimes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seat_id"], ["seats.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("showtime_id", "seat_id", name="uq_booking_seats_showtime_seat"),
    )
    op.create_index("ix_booking_seats_booking_id", "booking_seats", ["booking_id"], unique=False)
    op.create_index("ix_booking_seats_showtime_id", "booking_seats", ["showtime_id"], unique=False)
    op.create_index("ix_booking_seats_seat_id", "booking_seats", ["seat_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_booking_seats_seat_id", table_name="booking_seats")
    op.drop_index("ix_booking_seats_showtime_id", table_name="booking_seats")
    op.drop_index("ix_booking_seats_booking_id", table_name="booking_seats")
    op.drop_table("booking_seats")
    op.drop_index("ix_bookings_showtime_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_showtimes_movie_id_start_time", table_name="showtimes")
    op.drop_index("ix_showtimes_room_name", table_name="showtimes")
    op.drop_index("ix_showtimes_start_time", table_name="showtimes")
    op.drop_index("ix_showtimes_movie_id", table_name="showtimes")
    op.drop_table("showtimes")
    op.drop_index("ix_seats_room_name", table_name="seats")
    op.drop_table("seats")
    op.drop_table("movies")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
