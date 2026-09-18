import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiErrorMessage } from "../api/errors";
import { getMovieById } from "../api/movieApi";
import { getShowtimes } from "../api/showtimeApi";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import type { Movie } from "../types/movie";
import type { Showtime } from "../types/showtime";
import { formatDate, formatDateTime } from "../utils/date";

export function MovieDetailPage() {
  const { movieId: movieIdParam } = useParams();
  const movieId = Number(movieIdParam);
  const [movie, setMovie] = useState<Movie | null>(null);
  const [showtimes, setShowtimes] = useState<Showtime[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadMovieDetail() {
    if (!Number.isInteger(movieId) || movieId <= 0) {
      setError("Movie ID không hợp lệ.");
      setIsLoading(false);
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      const [movieData, showtimeData] = await Promise.all([getMovieById(movieId), getShowtimes(movieId)]);
      setMovie(movieData);
      setShowtimes(showtimeData);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải chi tiết phim."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMovieDetail();
  }, [movieIdParam]);

  if (isLoading) {
    return <Loading message="Đang tải chi tiết phim..." />;
  }
  if (error) {
    return <ErrorMessage message={error} onRetry={() => void loadMovieDetail()} />;
  }
  if (!movie) {
    return <ErrorMessage message="Không tìm thấy phim." />;
  }

  return (
    <section>
      <Link className="back-link" to="/movies">
        ← Quay lại danh sách phim
      </Link>
      <div className="movie-detail">
        <div className="movie-detail__content">
          <p className="eyebrow">Movie detail</p>
          <h1>{movie.title}</h1>
          <p className="movie-detail__description">{movie.description}</p>
          <div className="movie-detail__facts">
            <span>{movie.duration_minutes} phút</span>
            <span>Khởi chiếu {formatDate(movie.release_date)}</span>
          </div>
        </div>
      </div>

      <div className="section-heading">
        <div>
          <p className="eyebrow">Showtimes</p>
          <h2>Chọn suất chiếu</h2>
        </div>
      </div>
      {showtimes.length === 0 ? (
        <div className="empty-state">Phim này chưa có suất chiếu.</div>
      ) : (
        <div className="showtime-grid">
          {showtimes.map((showtime) => (
            <article className="showtime-card" key={showtime.id}>
              <div>
                <strong>{formatDateTime(showtime.start_time)}</strong>
                <span>Phòng {showtime.room_name}</span>
              </div>
              <Link className="button button--small" to={`/showtimes/${showtime.id}/seats`}>
                Chọn ghế
              </Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
