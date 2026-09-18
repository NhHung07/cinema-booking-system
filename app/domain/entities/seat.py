from dataclasses import dataclass


@dataclass(slots=True)
class Seat:
    id: int | None
    room_name: str
    row: str
    number: int

    @property
    def label(self) -> str:
        return f"{self.row}{self.number}"
