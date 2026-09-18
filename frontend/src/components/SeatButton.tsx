import type { Seat } from "../types/showtime";

interface SeatButtonProps {
  seat: Seat;
  selected: boolean;
  onToggle: (seat: Seat) => void;
}

export function SeatButton({ seat, selected, onToggle }: SeatButtonProps) {
  const className = !seat.available
    ? "seat-button seat-button--booked"
    : selected
      ? "seat-button seat-button--selected"
      : "seat-button";

  return (
    <button
      type="button"
      className={className}
      disabled={!seat.available}
      aria-pressed={selected}
      aria-label={`${seat.seat_number}: ${!seat.available ? "đã được đặt" : selected ? "đang chọn" : "còn trống"}`}
      onClick={() => onToggle(seat)}
    >
      {seat.seat_number}
    </button>
  );
}
