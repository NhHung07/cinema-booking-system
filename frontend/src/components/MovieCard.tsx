import { Link } from "react-router-dom";

import type { Movie } from "../types/movie";
import { formatDate } from "../utils/date";

export function MovieCard({ movie }: { movie: Movie }) {
  const shortDescription =
    movie.description.length > 150 ? `${movie.description.slice(0, 150).trimEnd()}…` : movie.description;

  return (
    <article className="movie-card">
      <div className="movie-card__eyebrow">Now showing</div>
      <h2>{movie.title}</h2>
      <p className="movie-card__description">{shortDescription}</p>
      <dl className="movie-card__meta">
        <div>
          <dt>Thời lượng</dt>
          <dd>{movie.duration_minutes} phút</dd>
        </div>
        <div>
          <dt>Khởi chiếu</dt>
          <dd>{formatDate(movie.release_date)}</dd>
        </div>
      </dl>
      <Link className="button" to={`/movies/${movie.id}`}>
        Xem chi tiết
      </Link>
    </article>
  );
}
