from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class ShowtimeModel(Base):
    __tablename__ = "showtimes"
    __table_args__ = (
        Index("ix_showtimes_movie_id_start_time", "movie_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    room_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    movie: Mapped["MovieModel"] = relationship(back_populates="showtimes")
    bookings: Mapped[list["BookingModel"]] = relationship(back_populates="showtime")
