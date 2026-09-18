from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class SeatModel(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("room_name", "row", "number", name="uq_seats_room_row_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    row: Mapped[str] = mapped_column(String(8), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
