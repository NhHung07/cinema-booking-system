import { useEffect, useState } from "react";

import { cancelBooking, getMyBookings } from "../api/bookingApi";
import { getApiErrorMessage } from "../api/errors";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import type { Booking } from "../types/booking";
import { formatDateTime } from "../utils/date";

export function MyBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  async function loadBookings() {
    setError(null);
    setIsLoading(true);
    try {
      setBookings(await getMyBookings());
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải booking của bạn."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadBookings();
  }, []);

  async function handleCancel(bookingId: number) {
    if (!window.confirm("Bạn có chắc muốn hủy booking này không? Ghế sẽ được giải phóng.")) {
      return;
    }
    setError(null);
    setCancellingId(bookingId);
    try {
      await cancelBooking(bookingId);
      await loadBookings();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể hủy booking."));
    } finally {
      setCancellingId(null);
    }
  }

  if (isLoading) {
    return <Loading message="Đang tải booking của bạn..." />;
  }
  if (error && bookings.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void loadBookings()} />;
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Your tickets</p>
          <h1>My Bookings</h1>
        </div>
        <p className="muted">Backend hiện trả về Showtime ID và Seat ID; movie title/room không có trong booking response.</p>
      </div>
      {error ? <ErrorMessage message={error} onRetry={() => void loadBookings()} /> : null}
      {bookings.length === 0 ? (
        <div className="empty-state">Bạn chưa có booking nào.</div>
      ) : (
        <div className="booking-list">
          {bookings.map((booking) => (
            <article className="booking-card" key={booking.id}>
              <div className="booking-card__top">
                <div>
                  <span className="eyebrow">Booking #{booking.id}</span>
                  <h2>Showtime #{booking.showtime_id}</h2>
                </div>
                <span className={booking.status === "CONFIRMED" ? "status status--confirmed" : "status status--cancelled"}>
                  {booking.status}
                </span>
              </div>
              <dl className="booking-card__details">
                <div>
                  <dt>Seat IDs</dt>
                  <dd>{booking.seat_ids.length ? booking.seat_ids.join(", ") : "Đã giải phóng khi cancel"}</dd>
                </div>
                <div>
                  <dt>Created at</dt>
                  <dd>{formatDateTime(booking.created_at)}</dd>
                </div>
              </dl>
              {booking.status === "CONFIRMED" ? (
                <button
                  className="button button--danger button--small"
                  type="button"
                  disabled={cancellingId === booking.id}
                  onClick={() => void handleCancel(booking.id)}
                >
                  {cancellingId === booking.id ? "Đang hủy..." : "Cancel Booking"}
                </button>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
