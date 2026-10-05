import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Star,
  Ticket,
  MapPin,
  Film,
  Sparkles,
} from "lucide-react";

import { getApiErrorMessage } from "../api/errors";
import { getMovieById } from "../api/movieApi";
import { getShowtimes } from "../api/showtimeApi";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import type { Movie } from "../types/movie";
import type { Showtime } from "../types/showtime";
import {
  calculateEndTime,
  formatDate,
  formatDayOfWeek,
  formatTimeOnly,
} from "../utils/date";
import { getMovieMeta } from "../utils/movieMeta";

export function MovieDetailPage() {
  const { movieId: movieIdParam } = useParams();
  const movieId = Number(movieIdParam);

  const [movie, setMovie] = useState<Movie | null>(null);
  const [showtimes, setShowtimes] = useState<Showtime[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDateKey, setSelectedDateKey] = useState<string>("ALL");

  async function loadMovieDetail() {
    if (!Number.isInteger(movieId) || movieId <= 0) {
      setError("Movie ID không hợp lệ.");
      setIsLoading(false);
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      const [movieData, showtimeData] = await Promise.all([
        getMovieById(movieId),
        getShowtimes(movieId),
      ]);
      setMovie(movieData);
      setShowtimes(showtimeData);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải thông tin chi tiết phim."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMovieDetail();
  }, [movieIdParam]);

  const meta = movie ? getMovieMeta(movie) : null;

  // Gom nhóm các lịch chiếu theo chuỗi ngày (YYYY-MM-DD)
  const showtimesByDate = useMemo(() => {
    const map = new Map<string, Showtime[]>();
    for (const st of showtimes) {
      const dateKey = st.start_time.split("T")[0];
      const list = map.get(dateKey) ?? [];
      list.push(st);
      map.set(dateKey, list);
    }
    return map;
  }, [showtimes]);

  // Danh sách ngày duy nhất đã sắp xếp
  const availableDates = useMemo(() => {
    return Array.from(showtimesByDate.keys()).sort();
  }, [showtimesByDate]);

  // Thiết lập ngày mặc định được chọn
  useEffect(() => {
    if (availableDates.length > 0 && selectedDateKey === "ALL") {
      setSelectedDateKey(availableDates[0]);
    }
  }, [availableDates, selectedDateKey]);

  const displayedShowtimes = useMemo(() => {
    if (selectedDateKey === "ALL") return showtimes;
    return showtimesByDate.get(selectedDateKey) ?? [];
  }, [selectedDateKey, showtimes, showtimesByDate]);

  if (isLoading) {
    return <Loading message="Đang tải thông tin phim & suất chiếu..." />;
  }
  if (error) {
    return <ErrorMessage message={error} onRetry={() => void loadMovieDetail()} />;
  }
  if (!movie || !meta) {
    return <ErrorMessage message="Không tìm thấy dữ liệu phim." />;
  }

  return (
    <div className="movie-detail-view">
      {/* Nút quay lại */}
      <div className="back-bar">
        <Link className="back-link-v2" to="/movies">
          <ArrowLeft size={18} />
          <span>Danh sách phim</span>
        </Link>
      </div>

      {/* Backdrop rạp chiếu phim Hero */}
      <section className="detail-hero">
        <div
          className="detail-hero__backdrop"
          style={{ backgroundImage: `url(${meta.backdropUrl})` }}
        />
        <div className="detail-hero__overlay" />

        <div className="detail-hero__container">
          <div className="detail-poster-card">
            <img
              src={meta.posterUrl}
              alt={movie.title}
              className="detail-poster-img"
            />
            <div className="detail-poster-badges">
              <span className="badge badge--age">{meta.ageRating}</span>
              <span className="badge badge--format">{meta.format}</span>
            </div>
          </div>

          <div className="detail-info-block">
            <div className="detail-genre-list">
              {meta.genres.map((g) => (
                <span key={g} className="genre-pill">
                  {g}
                </span>
              ))}
            </div>

            <h1 className="detail-title">{movie.title}</h1>

            <div className="detail-metrics">
              <span className="metric-chip metric-chip--rating">
                <Star size={16} fill="currentColor" />
                <strong>{meta.rating}</strong> / 10
              </span>
              <span className="metric-chip">
                <Clock size={16} />
                <span>{movie.duration_minutes} phút</span>
              </span>
              <span className="metric-chip">
                <Calendar size={16} />
                <span>Khởi chiếu {formatDate(movie.release_date)}</span>
              </span>
            </div>

            <div className="detail-synopsis">
              <h3>Nội dung phim</h3>
              <p>{movie.description}</p>
            </div>

            <div className="detail-credits">
              <div className="credit-row">
                <span className="credit-label">Đạo diễn:</span>
                <span className="credit-value">{meta.director}</span>
              </div>
              <div className="credit-row">
                <span className="credit-label">Diễn viên:</span>
                <span className="credit-value">{meta.cast}</span>
              </div>
              <div className="credit-row">
                <span className="credit-label">Định dạng:</span>
                <span className="credit-value">{meta.format} • Âm thanh vòm Dolby 7.1</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Phần chọn lịch chiếu */}
      <section className="showtimes-section">
        <div className="section-heading-v2">
          <div>
            <p className="eyebrow">Lịch chiếu phim</p>
            <h2 className="section-title">
              <Ticket size={24} className="title-icon" />
              <span>Chọn suất chiếu & đặt vé</span>
            </h2>
          </div>
        </div>

        {showtimes.length === 0 ? (
          <div className="empty-state">
            <Film size={44} className="empty-icon" />
            <p className="empty-state__title">Chưa có suất chiếu</p>
            <p className="muted">
              Phim hiện đang được cập nhật lịch chiếu. Vui lòng quay lại sau!
            </p>
          </div>
        ) : (
          <>
            {/* Các tab lọc theo ngày */}
            <div className="date-tabs-bar">
              {availableDates.map((dateStr) => {
                const isActive = selectedDateKey === dateStr;
                const dayLabel = formatDayOfWeek(`${dateStr}T12:00:00`);
                const formattedDate = formatDate(dateStr);
                return (
                  <button
                    key={dateStr}
                    type="button"
                    onClick={() => setSelectedDateKey(dateStr)}
                    className={`date-tab ${isActive ? "date-tab--active" : ""}`}
                  >
                    <span className="date-tab__day">{dayLabel}</span>
                    <span className="date-tab__date">{formattedDate}</span>
                  </button>
                );
              })}
            </div>

            {/* Lưới thẻ lịch chiếu */}
            <div className="showtime-cards-grid">
              {displayedShowtimes.map((showtime) => {
                const startTimeFormatted = formatTimeOnly(showtime.start_time);
                const endTimeFormatted = calculateEndTime(
                  showtime.start_time,
                  movie.duration_minutes
                );

                return (
                  <article className="showtime-card-v2" key={showtime.id}>
                    <div className="showtime-card-v2__header">
                      <span className="room-badge">
                        <MapPin size={14} />
                        <span>Phòng {showtime.room_name}</span>
                      </span>
                      <span className="format-sub-badge">2D Phụ đề</span>
                    </div>

                    <div className="showtime-card-v2__times">
                      <div className="time-primary">{startTimeFormatted}</div>
                      <div className="time-secondary">
                        Đến ~{endTimeFormatted}
                      </div>
                    </div>

                    <div className="showtime-card-v2__footer">
                      <div className="price-hint">
                        <span>Giá vé từ:</span>
                        <strong>90.000 ₫</strong>
                      </div>
                      <Link
                        className="button button--glow button--small"
                        to={`/showtimes/${showtime.id}/seats`}
                      >
                        <Sparkles size={15} />
                        <span>Chọn ghế</span>
                      </Link>
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
