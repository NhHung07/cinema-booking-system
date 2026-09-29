import { Link } from "react-router-dom";
import { Clock, Calendar, Star, Ticket } from "lucide-react";

import type { Movie } from "../types/movie";
import { formatDate } from "../utils/date";
import { getMovieMeta } from "../utils/movieMeta";

export function MovieCard({ movie }: { movie: Movie }) {
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

        {/* Top Badges */}
        <div className="movie-card-v2__badges-top">
          <span className="badge badge--age">{meta.ageRating}</span>
          <span className="badge badge--format">{meta.format}</span>
        </div>

        {/* Bottom Rating Badge */}
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
        </div>
      </div>
    </article>
  );
}
