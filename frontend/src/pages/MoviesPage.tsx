import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Sparkles, Film, Ticket, Star, Clock, X, Filter } from "lucide-react";

import { getApiErrorMessage } from "../api/errors";
import { getMovies } from "../api/movieApi";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { MovieCard } from "../components/MovieCard";
import type { Movie } from "../types/movie";
import { getMovieMeta } from "../utils/movieMeta";

export function MoviesPage() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState<string>("Tất cả");
  const [sortBy, setSortBy] = useState<"default" | "duration" | "title">("default");

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

  // Collect all unique genres across movies
  const availableGenres = useMemo(() => {
    const genreSet = new Set<string>();
    genreSet.add("Tất cả");
    movies.forEach((m) => {
      const meta = getMovieMeta(m);
      meta.genres.forEach((g) => genreSet.add(g));
    });
    return Array.from(genreSet);
  }, [movies]);

  // Filtered & Sorted movies
  const filteredMovies = useMemo(() => {
    return movies
      .filter((movie) => {
        const matchesQuery =
          movie.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          movie.description.toLowerCase().includes(searchQuery.toLowerCase());

        if (!matchesQuery) return false;

        if (selectedGenre !== "Tất cả") {
          const meta = getMovieMeta(movie);
          return meta.genres.includes(selectedGenre);
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "duration") return b.duration_minutes - a.duration_minutes;
        if (sortBy === "title") return a.title.localeCompare(b.title, "vi");
        return a.id - b.id;
      });
  }, [movies, searchQuery, selectedGenre, sortBy]);

  const featuredMovie = movies[0];
  const featuredMeta = featuredMovie ? getMovieMeta(featuredMovie) : null;

  if (isLoading) {
    return <Loading message="Đang tải danh sách phim chiếu rạp..." />;
  }
  if (error) {
    return <ErrorMessage message={error} onRetry={() => void loadMovies()} />;
  }

  return (
    <div className="movies-page">
      {/* Hero Spotlight Banner */}
      {featuredMovie && featuredMeta && !searchQuery && selectedGenre === "Tất cả" && (
        <section className="hero-spotlight">
          <div
            className="hero-spotlight__backdrop"
            style={{ backgroundImage: `url(${featuredMeta.backdropUrl})` }}
          />
          <div className="hero-spotlight__gradient" />

          <div className="hero-spotlight__content">
            <div className="hero-spotlight__badge">
              <Sparkles size={16} />
              <span>Phim nổi bật hôm nay</span>
            </div>

            <h1 className="hero-spotlight__title">{featuredMovie.title}</h1>

            <div className="hero-spotlight__meta">
              <span className="badge badge--age">{featuredMeta.ageRating}</span>
              <span className="badge badge--format">{featuredMeta.format}</span>
              <span className="hero-meta-item">
                <Star size={16} className="star-icon" fill="currentColor" />
                <strong>{featuredMeta.rating}</strong>/10
              </span>
              <span className="hero-meta-item">
                <Clock size={16} />
                <span>{featuredMovie.duration_minutes} phút</span>
              </span>
            </div>

            <p className="hero-spotlight__desc">{featuredMovie.description}</p>

            <div className="hero-spotlight__actions">
              <Link
                to={`/movies/${featuredMovie.id}`}
                className="button button--large button--glow"
              >
                <Ticket size={20} />
                <span>Đặt vé ngay</span>
              </Link>
              <Link
                to={`/movies/${featuredMovie.id}`}
                className="button button--large button--secondary"
              >
                <span>Xem chi tiết</span>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* Catalog Section Header */}
      <section className="catalog-section">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Lịch chiếu tại rạp</p>
            <h2 className="section-title">
              <Film size={26} className="title-icon" />
              <span>Phim đang chiếu</span>
            </h2>
          </div>
          <div className="catalog-stat">
            <span className="count-number">{filteredMovies.length}</span>
            <span className="count-label">phim có sẵn</span>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="toolbar">
          <div className="toolbar__search">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Tìm phim theo tên hoặc nội dung..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => setSearchQuery("")}
                aria-label="Xóa tìm kiếm"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <div className="toolbar__filters">
            {/* Genre Filter Pills */}
            <div className="genre-pills">
              {availableGenres.map((genre) => (
                <button
                  key={genre}
                  type="button"
                  onClick={() => setSelectedGenre(genre)}
                  className={`pill ${selectedGenre === genre ? "pill--active" : ""}`}
                >
                  {genre}
                </button>
              ))}
            </div>

            {/* Sort Select */}
            <div className="sort-wrapper">
              <Filter size={15} />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "default" | "duration" | "title")}
                className="sort-select"
                aria-label="Sắp xếp phim"
              >
                <option value="default">Mặc định</option>
                <option value="duration">Thời lượng dài nhất</option>
                <option value="title">Tên phim A-Z</option>
              </select>
            </div>
          </div>
        </div>

        {/* Movies Grid */}
        {filteredMovies.length === 0 ? (
          <div className="empty-state">
            <Film size={44} className="empty-icon" />
            <p className="empty-state__title">Không tìm thấy phim phù hợp</p>
            <p className="muted">
              {searchQuery
                ? `Không có kết quả nào cho "${searchQuery}". Hãy thử tìm kiếm từ khóa khác.`
                : "Hiện chưa có phim nào trong danh mục này."}
            </p>
            {(searchQuery || selectedGenre !== "Tất cả") && (
              <button
                className="button button--secondary button--small"
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setSelectedGenre("Tất cả");
                }}
              >
                Xóa tất cả bộ lọc
              </button>
            )}
          </div>
        ) : (
          <div className="movie-grid-v2">
            {filteredMovies.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
