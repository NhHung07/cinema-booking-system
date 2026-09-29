import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Ticket,
  Calendar,
  Clock,
  MapPin,
  QrCode,
  Film,
  AlertCircle,
  CheckCircle,
  XCircle,
  ArrowRight,
} from "lucide-react";

import { cancelBooking, getMyBookings } from "../api/bookingApi";
import { getApiErrorMessage } from "../api/errors";
import { getMovies } from "../api/movieApi";
import { getShowtimes, getShowtimeSeats } from "../api/showtimeApi";
import { ConfirmModal } from "../components/ConfirmModal";
import { Loading } from "../components/Loading";
import type { Booking } from "../types/booking";
import type { Movie } from "../types/movie";
import type { Seat, Showtime } from "../types/showtime";
import { formatCurrency, formatDateTime } from "../utils/date";
import { getMovieMeta, getSeatPrice } from "../utils/movieMeta";

interface ResolvedBooking {
  booking: Booking;
  movie?: Movie;
  showtime?: Showtime;
  seatLabels: string[];
  totalPrice: number;
}

export function MyBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [moviesMap, setMoviesMap] = useState<Map<number, Movie>>(new Map());
  const [showtimesMap, setShowtimesMap] = useState<Map<number, Showtime>>(new Map());
  const [seatsMapByShowtime, setSeatsMapByShowtime] = useState<
    Map<number, Map<number, Seat>>
  >(new Map());

  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Cancellation modal state
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [bookingToCancel, setBookingToCancel] = useState<number | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // Filter tab state
  const [statusFilter, setStatusFilter] = useState<"ALL" | "CONFIRMED" | "CANCELLED">(
    "ALL"
  );

  async function loadData() {
    setError(null);
    setIsLoading(true);
    try {
      const [bookingsData, moviesData, showtimesData] = await Promise.all([
        getMyBookings(),
        getMovies(),
        getShowtimes(),
      ]);

      setBookings(bookingsData);

      const mMap = new Map<number, Movie>();
      moviesData.forEach((m) => mMap.set(m.id, m));
      setMoviesMap(mMap);

      const stMap = new Map<number, Showtime>();
      showtimesData.forEach((st) => stMap.set(st.id, st));
      setShowtimesMap(stMap);

      // Fetch seat maps for each unique showtime in bookings to resolve seat_id -> seat_number
      const uniqueShowtimeIds = Array.from(
        new Set(bookingsData.map((b) => b.showtime_id))
      );

      const seatPromises = uniqueShowtimeIds.map(async (stId) => {
        try {
          const avail = await getShowtimeSeats(stId);
          const seatSubMap = new Map<number, Seat>();
          avail.seats.forEach((s) => seatSubMap.set(s.seat_id, s));
          return [stId, seatSubMap] as const;
        } catch {
          return [stId, new Map<number, Seat>()] as const;
        }
      });

      const seatResults = await Promise.all(seatPromises);
      const mainSeatMap = new Map<number, Map<number, Seat>>();
      seatResults.forEach(([stId, subMap]) => mainSeatMap.set(stId, subMap));
      setSeatsMapByShowtime(mainSeatMap);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải danh sách vé của bạn."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  // Enrich bookings with resolved details
  const resolvedBookings: ResolvedBooking[] = useMemo(() => {
    return bookings.map((booking) => {
      const showtime = showtimesMap.get(booking.showtime_id);
      const movie = showtime ? moviesMap.get(showtime.movie_id) : undefined;
      const seatSubMap = seatsMapByShowtime.get(booking.showtime_id);

      const seatLabels: string[] = [];
      let calculatedTotal = 0;

      for (const seatId of booking.seat_ids) {
        const seatObj = seatSubMap?.get(seatId);
        if (seatObj) {
          seatLabels.push(seatObj.seat_number);
          calculatedTotal += getSeatPrice(seatObj.seat_number);
        } else {
          seatLabels.push(`#${seatId}`);
          calculatedTotal += 90000;
        }
      }

      return {
        booking,
        movie,
        showtime,
        seatLabels,
        totalPrice: calculatedTotal,
      };
    });
  }, [bookings, moviesMap, showtimesMap, seatsMapByShowtime]);

  // Filtered bookings
  const filteredBookings = useMemo(() => {
    if (statusFilter === "ALL") return resolvedBookings;
    return resolvedBookings.filter((rb) => rb.booking.status === statusFilter);
  }, [resolvedBookings, statusFilter]);

  function promptCancel(bookingId: number) {
    setBookingToCancel(bookingId);
    setCancelModalOpen(true);
  }

  async function handleConfirmCancel() {
    if (!bookingToCancel) return;
    setError(null);
    setSuccessNotice(null);
    setIsCancelling(true);
    try {
      await cancelBooking(bookingToCancel);
      setSuccessNotice(`Đã hủy vé #${bookingToCancel} thành công. Ghế đã được giải phóng.`);
      setCancelModalOpen(false);
      setBookingToCancel(null);
      await loadData();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể hủy vé."));
    } finally {
      setIsCancelling(false);
    }
  }

  if (isLoading) {
    return <Loading message="Đang tải danh sách vé của bạn..." />;
  }

  const confirmedCount = resolvedBookings.filter(
    (b) => b.booking.status === "CONFIRMED"
  ).length;
  const cancelledCount = resolvedBookings.filter(
    (b) => b.booking.status === "CANCELLED"
  ).length;

  return (
    <div className="my-bookings-view">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Tài khoản & Đặt vé</p>
          <h1 className="section-title">
            <Ticket size={28} className="title-icon" />
            <span>Vé đã đặt của tôi</span>
          </h1>
        </div>
        <p className="muted">
          Quản lý toàn bộ vé điện tử, kiểm tra phòng chiếu và lịch sử giao dịch.
        </p>
      </div>

      {error ? (
        <div className="alert alert--error">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      ) : null}

      {successNotice ? (
        <div className="alert alert--success">
          <CheckCircle size={20} />
          <div>{successNotice}</div>
        </div>
      ) : null}

      {/* Filter Tabs */}
      <div className="booking-filter-tabs">
        <button
          type="button"
          className={`filter-tab ${statusFilter === "ALL" ? "filter-tab--active" : ""}`}
          onClick={() => setStatusFilter("ALL")}
        >
          <span>Tất cả vé</span>
          <span className="tab-count">{resolvedBookings.length}</span>
        </button>
        <button
          type="button"
          className={`filter-tab ${statusFilter === "CONFIRMED" ? "filter-tab--active" : ""}`}
          onClick={() => setStatusFilter("CONFIRMED")}
        >
          <span className="dot dot--confirmed" />
          <span>Đang hiệu lực</span>
          <span className="tab-count">{confirmedCount}</span>
        </button>
        <button
          type="button"
          className={`filter-tab ${statusFilter === "CANCELLED" ? "filter-tab--active" : ""}`}
          onClick={() => setStatusFilter("CANCELLED")}
        >
          <span className="dot dot--cancelled" />
          <span>Đã hủy</span>
          <span className="tab-count">{cancelledCount}</span>
        </button>
      </div>

      {/* Bookings List */}
      {filteredBookings.length === 0 ? (
        <div className="empty-state">
          <Film size={48} className="empty-icon" />
          <h3 className="empty-state__title">
            {statusFilter === "ALL"
              ? "Bạn chưa có vé nào"
              : statusFilter === "CONFIRMED"
              ? "Bạn không có vé nào đang hiệu lực"
              : "Không có vé nào đã hủy"}
          </h3>
          <p className="muted">
            Khám phá danh sách phim đang chiếu tại CineVerse để chọn cho mình chỗ ngồi ưng ý nhất!
          </p>
          <Link to="/movies" className="button button--glow button--large">
            <Film size={18} />
            <span>Khám phá phim ngay</span>
            <ArrowRight size={16} />
          </Link>
        </div>
      ) : (
        <div className="booking-cards-list">
          {filteredBookings.map(
            ({ booking, movie, showtime, seatLabels, totalPrice }) => {
              const meta = getMovieMeta(movie);
              const isConfirmed = booking.status === "CONFIRMED";

              return (
                <article
                  className={`ticket-pass-card ${!isConfirmed ? "ticket-pass-card--cancelled" : ""}`}
                  key={booking.id}
                >
                  {/* Left Side / Main Ticket Info */}
                  <div className="ticket-pass-main">
                    <div className="ticket-pass-header">
                      <div className="ticket-pass-header__badges">
                        <span className="badge badge--booking-id">
                          Mã vé: #{booking.id}
                        </span>
                        <span className="badge badge--age">{meta.ageRating}</span>
                        <span className="badge badge--format">{meta.format}</span>
                      </div>

                      <div className="ticket-pass-status">
                        {isConfirmed ? (
                          <span className="status-pill status-pill--confirmed">
                            <CheckCircle size={14} />
                            <span>ĐÃ XÁC NHẬN</span>
                          </span>
                        ) : (
                          <span className="status-pill status-pill--cancelled">
                            <XCircle size={14} />
                            <span>ĐÃ HỦY VÉ</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="ticket-pass-movie">
                      <img
                        src={meta.posterUrl}
                        alt={movie?.title ?? "Movie Poster"}
                        className="ticket-pass-poster"
                      />
                      <div className="ticket-pass-movie-details">
                        <h2 className="ticket-pass-title">
                          {movie ? (
                            <Link to={`/movies/${movie.id}`}>{movie.title}</Link>
                          ) : (
                            `Showtime #${booking.showtime_id}`
                          )}
                        </h2>

                        <div className="ticket-pass-meta-grid">
                          <div className="meta-cell">
                            <span className="meta-cell__label">
                              <MapPin size={13} /> Phòng chiếu
                            </span>
                            <span className="meta-cell__value">
                              {showtime ? `Phòng ${showtime.room_name}` : "--"}
                            </span>
                          </div>

                          <div className="meta-cell">
                            <span className="meta-cell__label">
                              <Clock size={13} /> Suất chiếu
                            </span>
                            <span className="meta-cell__value">
                              {showtime ? formatDateTime(showtime.start_time) : "--"}
                            </span>
                          </div>

                          <div className="meta-cell">
                            <span className="meta-cell__label">
                              <Ticket size={13} /> Ghế ngồi ({seatLabels.length})
                            </span>
                            <span className="meta-cell__value meta-cell__seats">
                              {seatLabels.length > 0
                                ? seatLabels.join(", ")
                                : "Đã giải phóng khi hủy"}
                            </span>
                          </div>

                          <div className="meta-cell">
                            <span className="meta-cell__label">
                              <Calendar size={13} /> Ngày đặt vé
                            </span>
                            <span className="meta-cell__value">
                              {formatDateTime(booking.created_at)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Perforated Divider */}
                  <div className="ticket-pass-divider">
                    <span className="cutout cutout--top" />
                    <div className="dashed-line" />
                    <span className="cutout cutout--bottom" />
                  </div>

                  {/* Right Side / Ticket Stub */}
                  <div className="ticket-pass-stub">
                    <div className="stub-qr-wrapper">
                      <QrCode size={72} className="stub-qr" />
                      <span className="stub-serial">TICKET-{booking.id}</span>
                    </div>

                    <div className="stub-price-info">
                      <span className="stub-price-label">Tổng thanh toán:</span>
                      <strong className="stub-price-val">
                        {formatCurrency(totalPrice)}
                      </strong>
                    </div>

                    {isConfirmed ? (
                      <button
                        className="button button--danger button--small button--wide"
                        type="button"
                        onClick={() => promptCancel(booking.id)}
                      >
                        Hủy đặt vé
                      </button>
                    ) : (
                      <span className="stub-cancelled-label">Vé không còn hiệu lực</span>
                    )}
                  </div>
                </article>
              );
            }
          )}
        </div>
      )}

      {/* Confirmation Modal for Ticket Cancellation */}
      <ConfirmModal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        onConfirm={() => void handleConfirmCancel()}
        title="Xác nhận hủy vé đặt"
        message={`Bạn có chắc chắn muốn hủy vé #${bookingToCancel}? Ghế ngồi sẽ được giải phóng ngay lập tức cho các khách hàng khác.`}
        confirmText="Đồng ý hủy vé"
        cancelText="Giữ lại vé"
        isDanger={true}
        isLoading={isCancelling}
      />
    </div>
  );
}
