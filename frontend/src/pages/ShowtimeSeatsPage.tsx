import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { createBooking } from "../api/bookingApi";
import { getApiErrorMessage, getApiStatus } from "../api/errors";
import { getShowtimeSeats } from "../api/showtimeApi";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { SeatButton } from "../components/SeatButton";
import type { Seat } from "../types/showtime";

function seatRow(seatNumber: string): string {
  return seatNumber.replace(/\d+$/, "") || "Khác";
}

export function ShowtimeSeatsPage() {
  const { showtimeId: showtimeIdParam } = useParams();
  const showtimeId = Number(showtimeIdParam);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [selectedSeatIds, setSelectedSeatIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadSeats() {
    if (!Number.isInteger(showtimeId) || showtimeId <= 0) {
      setError("Showtime ID không hợp lệ.");
      setIsLoading(false);
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      const availability = await getShowtimeSeats(showtimeId);
      setSeats(availability.seats);
      setSelectedSeatIds([]);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải sơ đồ ghế."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadSeats();
  }, [showtimeIdParam]);

  const selectedSeats = useMemo(
    () => seats.filter((seat) => selectedSeatIds.includes(seat.seat_id)),
    [seats, selectedSeatIds],
  );

  const seatsByRow = useMemo(() => {
    const grouped: Record<string, Seat[]> = {};
    for (const seat of seats) {
      const row = seatRow(seat.seat_number);
      grouped[row] = [...(grouped[row] ?? []), seat];
    }
    return Object.entries(grouped).sort(([left], [right]) => left.localeCompare(right, "vi"));
  }, [seats]);

  function toggleSeat(seat: Seat) {
    if (!seat.available) {
      return;
    }
    setSuccess(null);
    setSelectedSeatIds((current) =>
      current.includes(seat.seat_id)
        ? current.filter((seatId) => seatId !== seat.seat_id)
        : [...current, seat.seat_id],
    );
  }

  async function handleBooking() {
    if (selectedSeatIds.length === 0) {
      return;
    }
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      await createBooking({ showtime_id: showtimeId, seat_ids: selectedSeatIds });
      setSuccess("Đặt vé thành công. Ghế của bạn đã được xác nhận.");
      await loadSeats();
    } catch (requestError) {
      if (getApiStatus(requestError) === 409) {
        await loadSeats();
        setError(
          "Một hoặc nhiều ghế bạn chọn vừa được người khác đặt. Vui lòng chọn ghế khác.",
        );
      } else {
        setError(getApiErrorMessage(requestError, "Không thể hoàn tất booking."));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <Loading message="Đang tải sơ đồ ghế..." />;
  }
  if (error && seats.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void loadSeats()} />;
  }

  return (
    <section>
      <Link className="back-link" to="/movies">
        ← Quay lại danh sách phim
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Showtime #{showtimeId}</p>
          <h1>Chọn ghế</h1>
        </div>
        <p className="muted">Ghế màu xám đã được đặt và không thể chọn.</p>
      </div>

      {error ? <ErrorMessage message={error} onRetry={() => void loadSeats()} /> : null}
      {success ? <div className="alert alert--success">{success}</div> : null}

      <div className="seat-legend" aria-label="Chú thích trạng thái ghế">
        <span><i className="legend-dot legend-dot--available" />Available</span>
        <span><i className="legend-dot legend-dot--selected" />Selected</span>
        <span><i className="legend-dot legend-dot--booked" />Booked</span>
      </div>

      <div className="screen">SCREEN</div>
      <div className="seat-map" aria-label="Sơ đồ ghế">
        {seatsByRow.map(([row, rowSeats]) => (
          <div className="seat-row" key={row}>
            <span className="seat-row__label">{row}</span>
            <div className="seat-row__buttons">
              {rowSeats.map((seat) => (
                <SeatButton
                  key={seat.seat_id}
                  seat={seat}
                  selected={selectedSeatIds.includes(seat.seat_id)}
                  onToggle={toggleSeat}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <aside className="booking-panel">
        <div>
          <span className="booking-panel__label">Selected seats</span>
          <strong>{selectedSeats.length ? selectedSeats.map((seat) => seat.seat_number).join(", ") : "Chưa chọn ghế"}</strong>
        </div>
        <button className="button" type="button" onClick={() => void handleBooking()} disabled={!selectedSeatIds.length || isSubmitting}>
          {isSubmitting ? "Đang xác nhận..." : "Confirm Booking"}
        </button>
      </aside>
    </section>
  );
}
