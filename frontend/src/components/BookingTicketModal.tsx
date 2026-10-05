import { CheckCircle2, Ticket, QrCode, ArrowRight, X } from "lucide-react";
import { Link } from "react-router-dom";

import type { Movie } from "../types/movie";
import type { Seat, Showtime } from "../types/showtime";
import { formatCurrency, formatDateTime } from "../utils/date";
import { getMovieMeta, getSeatPrice } from "../utils/movieMeta";

interface BookingTicketModalProps {
  isOpen: boolean;
  onClose: () => void;
  movie: Movie | null;
  showtime: Showtime | null;
  selectedSeats: Seat[];
  bookingId: number | null;
}

export function BookingTicketModal({
  isOpen,
  onClose,
  movie,
  showtime,
  selectedSeats,
  bookingId,
}: BookingTicketModalProps) {
  if (!isOpen || !movie || !showtime) return null;

  const meta = getMovieMeta(movie);
  const totalPrice = selectedSeats.reduce(
    (sum, seat) => sum + getSeatPrice(seat.seat_number),
    0
  );

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="ticket-modal-card" onClick={(e) => e.stopPropagation()}>
        <button
          className="modal-close-btn"
          type="button"
          onClick={onClose}
          aria-label="Đóng"
        >
          <X size={20} />
        </button>

        <div className="ticket-modal-header">
          <div className="success-badge-icon">
            <CheckCircle2 size={36} />
          </div>
          <h2>Đặt vé thành công!</h2>
          <p className="muted">
            Vé điện tử của bạn đã được xác nhận. Vui lòng xuất trình mã khi đến rạp.
          </p>
        </div>

        {/* Vé xem phim phong cách Boarding Pass */}
        <div className="cinema-ticket">
          <div className="cinema-ticket__left">
            <div className="ticket-movie-row">
              <img
                src={meta.posterUrl}
                alt={movie.title}
                className="ticket-poster"
              />
              <div className="ticket-movie-info">
                <span className="badge badge--age">{meta.ageRating}</span>
                <h3 className="ticket-movie-title">{movie.title}</h3>
                <span className="ticket-format">{meta.format}</span>
              </div>
            </div>

            <div className="ticket-grid-info">
              <div>
                <span className="ticket-label">Phòng chiếu</span>
                <span className="ticket-val">Phòng {showtime.room_name}</span>
              </div>
              <div>
                <span className="ticket-label">Thời gian</span>
                <span className="ticket-val">
                  {formatDateTime(showtime.start_time)}
                </span>
              </div>
              <div>
                <span className="ticket-label">Ghế đã chọn ({selectedSeats.length})</span>
                <span className="ticket-val ticket-seats">
                  {selectedSeats.map((s) => s.seat_number).join(", ")}
                </span>
              </div>
              <div>
                <span className="ticket-label">Tổng thanh toán</span>
                <span className="ticket-val ticket-price">
                  {formatCurrency(totalPrice)}
                </span>
              </div>
            </div>
          </div>

          <div className="cinema-ticket__divider">
            <span className="notch notch--top" />
            <span className="perforated-line" />
            <span className="notch notch--bottom" />
          </div>

          <div className="cinema-ticket__right">
            <div className="qr-box">
              <QrCode size={80} className="qr-svg" />
            </div>
            <div className="ticket-code-label">
              Mã vé: <strong>#{bookingId ?? "CONFIRMED"}</strong>
            </div>
            <span className="ticket-sub-note">CineVerse E-Ticket</span>
          </div>
        </div>

        {/* Các nút hành động của Modal */}
        <div className="modal-actions">
          <Link to="/my-bookings" className="button button--glow button--wide">
            <Ticket size={18} />
            <span>Xem trong "Vé của tôi"</span>
            <ArrowRight size={16} />
          </Link>
          <button
            type="button"
            className="button button--secondary button--wide"
            onClick={onClose}
          >
            Đóng & Tiếp tục đặt
          </button>
        </div>
      </div>
    </div>
  );
}
