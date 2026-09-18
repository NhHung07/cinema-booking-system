import { useEffect, useState } from "react";

import { getApiErrorMessage } from "../api/errors";
import { getMovies } from "../api/movieApi";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { MovieCard } from "../components/MovieCard";
import type { Movie } from "../types/movie";

export function MoviesPage() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadMovies() {
    setError(null);
    setIsLoading(true);
    try {
      setMovies(await getMovies());
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải danh sách phim."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMovies();
  }, []);

  if (isLoading) {
    return <Loading message="Đang tải danh sách phim..." />;
  }
  if (error) {
    return <ErrorMessage message={error} onRetry={() => void loadMovies()} />;
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Cinema catalogue</p>
          <h1>Phim đang có</h1>
        </div>
        <p className="muted">Chọn một phim để xem thông tin và suất chiếu.</p>
      </div>
      {movies.length === 0 ? (
        <div className="empty-state">Hiện chưa có phim nào. Hãy chạy seed data ở backend.</div>
      ) : (
        <div className="movie-grid">
          {movies.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      )}
    </section>
  );
}
