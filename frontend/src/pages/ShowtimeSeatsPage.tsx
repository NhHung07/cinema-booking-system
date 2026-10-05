import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  Film,
  MapPin,
  Ticket,
  X,
  AlertCircle,
} from "lucide-react";

import { createBooking } from "../api/bookingApi";
import { getApiErrorMessage, getApiStatus } from "../api/errors";
import { getMovieById } from "../api/movieApi";
import { getShowtimes, getShowtimeSeats } from "../api/showtimeApi";
import { BookingTicketModal } from "../components/BookingTicketModal";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { SeatButton } from "../components/SeatButton";
import type { Movie } from "../types/movie";
import type { Seat, Showtime } from "../types/showtime";
import { formatCurrency, formatDateTime } from "../utils/date";
import { getMovieMeta, getSeatPrice, isVipSeat } from "../utils/movieMeta";

function seatRow(seatNumber: string): string {
  return seatNumber.replace(/\d+$/, "") || "Khác";
}

export function ShowtimeSeatsPage() {
  const { showtimeId: showtimeIdParam } = useParams();
  const showtimeId = Number(showtimeIdParam);

  const [seats, setSeats] = useState<Seat[]>([]);
  const [selectedSeatIds, setSelectedSeatIds] = useState<number[]>([]);
  const [showtime, setShowtime] = useState<Showtime | null>(null);
  const [movie, setMovie] = useState<Movie | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // State của modal thành công
  const [successModalOpen, setSuccessModalOpen] = useState(false);
  const [lastBookingId, setLastBookingId] = useState<number | null>(null);
  const [confirmedSeats, setConfirmedSeats] = useState<Seat[]>([]);

  async function loadData() {
    if (!Number.isInteger(showtimeId) || showtimeId <= 0) {
      setError("Showtime ID không hợp lệ.");
      setIsLoading(false);
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      // Tải danh sách ghế
      const availabilityPromise = getShowtimeSeats(showtimeId);
      // Tải tất cả lịch chiếu để tìm movie_id của lịch chiếu này
      const showtimesPromise = getShowtimes();

      const [availability, allShowtimes] = await Promise.all([
        availabilityPromise,
        showtimesPromise,
      ]);

      setSeats(availability.seats);
      setSelectedSeatIds([]);

      const foundShowtime = allShowtimes.find((st) => st.id === showtimeId);
      if (foundShowtime) {
        setShowtime(foundShowtime);
        const movieData = await getMovieById(foundShowtime.movie_id);
        setMovie(movieData);
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải sơ đồ ghế của suất chiếu."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
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
    // Sắp xếp các ghế trong mỗi hàng theo số thứ tự ghế
    for (const row of Object.keys(grouped)) {
      grouped[row].sort((a, b) =>
        a.seat_number.localeCompare(b.seat_number, undefined, { numeric: true })
      );
    }
    return Object.entries(grouped).sort(([left], [right]) =>
      left.localeCompare(right, "vi")
    );
  }, [seats]);

  // Tính toán giá vé
  const { standardCount, vipCount, totalPrice } = useMemo(() => {
    let standard = 0;
    let vip = 0;
    let total = 0;
    for (const s of selectedSeats) {
      const price = getSeatPrice(s.seat_number);
      total += price;
      if (isVipSeat(s.seat_number)) {
        vip++;
      } else {
        standard++;
      }
    }
    return { standardCount: standard, vipCount: vip, totalPrice: total };
  }, [selectedSeats]);

  function toggleSeat(seat: Seat) {
    if (!seat.available) {
      return;
    }
    setSelectedSeatIds((current) =>
      current.includes(seat.seat_id)
        ? current.filter((seatId) => seatId !== seat.seat_id)
        : [...current, seat.seat_id],
    );
  }

  function removeSeat(seatId: number) {
    setSelectedSeatIds((current) => current.filter((id) => id !== seatId));
  }

  async function handleBooking() {
    if (selectedSeatIds.length === 0) {
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const booking = await createBooking({
        showtime_id: showtimeId,
        seat_ids: selectedSeatIds,
      });

      // Lưu các ghế đã xác nhận cho modal hóa đơn (receipt)
      setConfirmedSeats(selectedSeats);
      setLastBookingId(booking.id);
      setSuccessModalOpen(true);

      // Làm mới trạng thái ghế còn trống
      const availability = await getShowtimeSeats(showtimeId);
      setSeats(availability.seats);
      setSelectedSeatIds([]);
    } catch (requestError) {
      if (getApiStatus(requestError) === 409) {
        // Xung đột ghế (Seat conflict)
        const availability = await getShowtimeSeats(showtimeId);
        setSeats(availability.seats);
        setSelectedSeatIds([]);
        setError(
          "Rất tiếc! Một hoặc nhiều ghế bạn chọn vừa được người khác đặt trước. Vui lòng chọn ghế khác.",
        );
      } else {
        setError(getApiErrorMessage(requestError, "Không thể hoàn tất đặt vé."));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return <Loading message="Đang tải sơ đồ phòng chiếu & ghế ngồi..." />;
  }
  if (error && seats.length === 0) {
    return <ErrorMessage message={error} onRetry={() => void loadData()} />;
  }

  const meta = movie ? getMovieMeta(movie) : null;

  return (
    <div className="seats-page-view">
      {/* Thanh điều hướng Breadcrumb */}
      <div className="back-bar">
        <Link
          className="back-link-v2"
          to={movie ? `/movies/${movie.id}` : "/movies"}
        >
          <ArrowLeft size={18} />
          <span>{movie ? `Quay lại: ${movie.title}` : "Quay lại"}</span>
        </Link>
      </div>

      {/* Banner tiêu đề thông tin suất chiếu */}
      {showtime && movie && meta && (
        <header className="seats-header-banner">
          <img
            src={meta.posterUrl}
            alt={movie.title}
            className="seats-header-banner__poster"
          />
          <div className="seats-header-banner__info">
            <div className="seats-header-banner__badges">
              <span className="badge badge--age">{meta.ageRating}</span>
              <span className="badge badge--format">{meta.format}</span>
            </div>
            <h1 className="seats-header-banner__title">{movie.title}</h1>
            <div className="seats-header-banner__details">
              <span className="header-detail-item">
                <MapPin size={15} />
                <span>Phòng {showtime.room_name}</span>
              </span>
              <span className="header-detail-item">
                <Clock size={15} />
                <span>{formatDateTime(showtime.start_time)}</span>
              </span>
              <span className="header-detail-item">
                <Film size={15} />
                <span>{movie.duration_minutes} phút</span>
              </span>
            </div>
          </div>
        </header>
      )}

      {error ? (
        <div className="alert alert--error">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      ) : null}

      {/* Khu vực phòng chiếu */}
      <section className="cinema-hall">
        {/* Màn chiếu với hiệu ứng ánh sáng máy chiếu */}
        <div className="screen-container">
          <div className="screen-light-beam" />
          <div className="screen-curved">
            <span className="screen-label">MÀN HÌNH CHIẾU</span>
          </div>
        </div>

        {/* Chú thích loại ghế (Legend) */}
        <div className="seat-legend-v2" aria-label="Chú thích loại ghế">
          <div className="legend-item">
            <span className="legend-seat-sample legend-seat--standard" />
            <div className="legend-text">
              <span>Ghế Thường</span>
              <small>90.000 ₫</small>
            </div>
          </div>
          <div className="legend-item">
            <span className="legend-seat-sample legend-seat--vip" />
            <div className="legend-text">
              <span>Ghế VIP</span>
              <small>110.000 ₫</small>
            </div>
          </div>
          <div className="legend-item">
            <span className="legend-seat-sample legend-seat--selected" />
            <div className="legend-text">
              <span>Đang chọn</span>
              <small>Đang giữ</small>
            </div>
          </div>
          <div className="legend-item">
            <span className="legend-seat-sample legend-seat--booked" />
            <div className="legend-text">
              <span>Đã bán</span>
              <small>Không khả dụng</small>
            </div>
          </div>
        </div>

        {/* Sơ đồ bố trí ghế */}
        <div className="seat-grid-container" aria-label="Sơ đồ ghế ngồi">
          <div className="seat-map-v2">
            {seatsByRow.map(([row, rowSeats]) => (
              <div className="seat-row-v2" key={row}>
                <span className="seat-row-v2__label">{row}</span>
                <div className="seat-row-v2__buttons">
                  {rowSeats.map((seat) => (
                    <SeatButton
                      key={seat.seat_id}
                      seat={seat}
                      selected={selectedSeatIds.includes(seat.seat_id)}
                      onToggle={toggleSeat}
                    />
                  ))}
                </div>
                <span className="seat-row-v2__label seat-row-v2__label--right">
                  {row}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Dock tóm tắt đặt vé nổi ở cạnh dưới */}
      <aside className="booking-summary-dock">
        <div className="dock-content">
          <div className="dock-seats-info">
            <span className="dock-label">Ghế đã chọn ({selectedSeats.length})</span>
            {selectedSeats.length === 0 ? (
              <span className="dock-placeholder">Vui lòng chọn ghế trên sơ đồ</span>
            ) : (
              <div className="dock-seat-chips">
                {selectedSeats.map((s) => (
                  <span
                    key={s.seat_id}
                    className={`dock-chip ${isVipSeat(s.seat_number) ? "dock-chip--vip" : ""}`}
                  >
                    <span>{s.seat_number}</span>
                    <button
                      type="button"
                      className="dock-chip-remove"
                      onClick={() => removeSeat(s.seat_id)}
                      aria-label={`Bỏ chọn ghế ${s.seat_number}`}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="dock-pricing">
            <div className="dock-price-breakdown">
              {standardCount > 0 && (
                <span>
                  {standardCount}x Thường ({formatCurrency(standardCount * 90000)})
                </span>
              )}
              {vipCount > 0 && (
                <span>
                  {vipCount}x VIP ({formatCurrency(vipCount * 110000)})
                </span>
              )}
            </div>
            <div className="dock-total-price">
              <span className="total-label">Tổng cộng:</span>
              <strong className="total-number">{formatCurrency(totalPrice)}</strong>
            </div>
          </div>

          <div className="dock-action">
            <button
              className="button button--large button--glow"
              type="button"
              onClick={() => void handleBooking()}
              disabled={selectedSeatIds.length === 0 || isSubmitting}
            >
              <Ticket size={18} />
              <span>
                {isSubmitting ? "Đang xác nhận..." : `Thanh toán (${formatCurrency(totalPrice)})`}
              </span>
            </button>
          </div>
        </div>
      </aside>

      {/* Modal hóa đơn đặt vé thành công */}
      <BookingTicketModal
        isOpen={successModalOpen}
        onClose={() => setSuccessModalOpen(false)}
        movie={movie}
        showtime={showtime}
        selectedSeats={confirmedSeats}
        bookingId={lastBookingId}
      />
    </div>
  );
}
