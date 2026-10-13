import { Link } from "react-router-dom";
import { Clock, Calendar, Star, Ticket, Pencil, Trash2 } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import type { Movie } from "../types/movie";
import { formatDate } from "../utils/date";
import { getMovieMeta } from "../utils/movieMeta";

export function MovieCard({
  movie,
  onDelete,
}: {
  movie: Movie;
  onDelete?: (movie: Movie) => void;
}) {
  const { isAdmin } = useAuth();
  const meta = getMovieMeta(movie);
  const shortDescription =
    movie.description.length > 110 ? `${movie.description.slice(0, 110).trimEnd()}…` : movie.description;

  return (
    <article className="movie-card-v2">
      <Link to={`/movies/${movie.id}`} className="movie-card-v2__poster-wrapper">
        <img
          src={meta.posterUrl}
          alt={movie.title}
          className="movie-card-v2__poster"
          loading="lazy"
        />
        <div className="movie-card-v2__overlay">
          <span className="movie-card-v2__overlay-btn">
            <Ticket size={18} />
            <span>Mua vé ngay</span>
          </span>
        </div>

        {/* Các huy hiệu phía trên (Top Badges) */}
        <div className="movie-card-v2__badges-top">
          <span className="badge badge--age">{meta.ageRating}</span>
          <span className="badge badge--format">{meta.format}</span>
        </div>

        {/* Huy hiệu đánh giá phía dưới (Bottom Rating Badge) */}
        <div className="movie-card-v2__rating">
          <Star size={14} className="star-icon" fill="currentColor" />
          <span>{meta.rating.toFixed(1)}</span>
        </div>
      </Link>

      <div className="movie-card-v2__body">
        <div className="movie-card-v2__genres">
          {meta.genres.slice(0, 2).map((genre) => (
            <span key={genre} className="genre-tag">
              {genre}
            </span>
          ))}
        </div>

        <h3 className="movie-card-v2__title">
          <Link to={`/movies/${movie.id}`} title={movie.title}>
            {movie.title}
          </Link>
        </h3>

        <p className="movie-card-v2__desc">{shortDescription}</p>

        <div className="movie-card-v2__meta">
          <span className="meta-item">
            <Clock size={14} />
            <span>{movie.duration_minutes} phút</span>
          </span>
          <span className="meta-item">
            <Calendar size={14} />
            <span>{formatDate(movie.release_date)}</span>
          </span>
        </div>

        <div className="movie-card-v2__actions">
          <Link to={`/movies/${movie.id}`} className="button button--wide button--glow">
            <Ticket size={16} />
            <span>Chọn suất chiếu</span>
          </Link>
          {isAdmin && onDelete ? (
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", width: "100%" }}>
              <Link
                to={`/admin/movies/${movie.id}/edit`}
                className="button button--secondary button--small"
                style={{
                  flex: 1,
                  display: "inline-flex",
                  justifyContent: "center",
                  alignItems: "center",
                  gap: "0.35rem",
                }}
                title="Sửa phim"
              >
                <Pencil size={14} />
                <span>Sửa</span>
              </Link>
              <button
                type="button"
                onClick={() => onDelete(movie)}
                className="button button--danger button--small"
                style={{
                  flex: 1,
                  display: "inline-flex",
                  justifyContent: "center",
                  alignItems: "center",
                  gap: "0.35rem",
                }}
                title="Xóa phim"
              >
                <Trash2 size={14} />
                <span>Xóa</span>
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}
