import type { Seat } from "../types/showtime";
import { formatCurrency } from "../utils/date";
import { getSeatPrice, isVipSeat } from "../utils/movieMeta";

interface SeatButtonProps {
  seat: Seat;
  selected: boolean;
  onToggle: (seat: Seat) => void;
}

export function SeatButton({ seat, selected, onToggle }: SeatButtonProps) {
  const isVip = isVipSeat(seat.seat_number);
  const price = getSeatPrice(seat.seat_number);

  let statusClass = "seat-btn--available";
  if (!seat.available) {
    statusClass = "seat-btn--booked";
  } else if (selected) {
    statusClass = "seat-btn--selected";
  } else if (isVip) {
    statusClass = "seat-btn--vip";
  }

  const tooltipText = !seat.available
    ? `Ghế ${seat.seat_number} (Đã được đặt)`
    : selected
    ? `Ghế ${seat.seat_number} (${isVip ? "VIP" : "Thường"}) - ${formatCurrency(price)} [Đang chọn]`
    : `Ghế ${seat.seat_number} (${isVip ? "VIP" : "Thường"}) - ${formatCurrency(price)}`;

  return (
    <button
      className={`seat-btn ${statusClass}`}
      disabled={!seat.available}
      type="button"
      onClick={() => onToggle(seat)}
      title={tooltipText}
      aria-label={tooltipText}
      aria-pressed={selected}
    >
      <span className="seat-btn__label">{seat.seat_number}</span>
      <span className="seat-btn__cushion" />
    </button>
  );
}
