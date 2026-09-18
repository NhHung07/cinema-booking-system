from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class BookingModel(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONFIRMED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["UserModel"] = relationship(back_populates="bookings")
    showtime: Mapped["ShowtimeModel"] = relationship(back_populates="bookings")
    booking_seats: Mapped[list["BookingSeatModel"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )


class BookingSeatModel(Base):
    __tablename__ = "booking_seats"
    __table_args__ = (
        UniqueConstraint("showtime_id", "seat_id", name="uq_booking_seats_showtime_seat"),
        Index("ix_booking_seats_showtime_id", "showtime_id"),
        Index("ix_booking_seats_seat_id", "seat_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id", ondelete="RESTRICT"), nullable=False)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False)

    booking: Mapped[BookingModel] = relationship(back_populates="booking_seats")
