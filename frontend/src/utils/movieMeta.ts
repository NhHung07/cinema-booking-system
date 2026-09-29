import type { Movie } from "../types/movie";

export interface MovieMeta {
  posterUrl: string;
  backdropUrl: string;
  genres: string[];
  rating: number;
  ageRating: string;
  director: string;
  cast: string;
  format: string;
  trailerTitle?: string;
}

const KNOWN_MOVIES: Record<string, Partial<MovieMeta>> = {
  interstellar: {
    posterUrl: "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=700&q=85",
    backdropUrl: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1920&q=85",
    genres: ["Khoa học viễn tưởng", "Phiêu lưu", "Kịch tính"],
    rating: 8.7,
    ageRating: "C13",
    director: "Christopher Nolan",
    cast: "Matthew McConaughey, Anne Hathaway, Jessica Chastain",
    format: "IMAX 2D",
    trailerTitle: "Official Trailer - Interstellar",
  },
  inception: {
    posterUrl: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=700&q=85",
    backdropUrl: "https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&w=1920&q=85",
    genres: ["Hành động", "Khoa học viễn tưởng", "Giật gân"],
    rating: 8.8,
    ageRating: "C16",
    director: "Christopher Nolan",
    cast: "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page",
    format: "Digital 2D Dolby Atmos",
    trailerTitle: "Official Trailer - Inception",
  },
  dune: {
    posterUrl: "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=700&q=85",
    backdropUrl: "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1920&q=85",
    genres: ["Hành động", "Phiêu lưu", "Khoa học viễn tưởng"],
    rating: 8.4,
    ageRating: "C16",
    director: "Denis Villeneuve",
    cast: "Timothée Chalamet, Zendaya, Rebecca Ferguson",
    format: "IMAX 3D",
  },
  oppenheimer: {
    posterUrl: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=700&q=85",
    backdropUrl: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=85",
    genres: ["Lịch sử", "Tiểu sử", "Kịch tính"],
    rating: 8.9,
    ageRating: "C18",
    director: "Christopher Nolan",
    cast: "Cillian Murphy, Emily Blunt, Matt Damon",
    format: "IMAX 2D",
  },
};

const FALLBACK_POSTERS = [
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=700&q=85",
  "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=700&q=85",
  "https://images.unsplash.com/photo-1574267432553-4b4628081c31?auto=format&fit=crop&w=700&q=85",
  "https://images.unsplash.com/photo-1518173946687-a4c8a383392e?auto=format&fit=crop&w=700&q=85",
];

const FALLBACK_BACKDROPS = [
  "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=1920&q=85",
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1920&q=85",
];

export function getMovieMeta(movie: Partial<Movie> | null | undefined): MovieMeta {
  if (!movie || !movie.title) {
    return {
      posterUrl: FALLBACK_POSTERS[0],
      backdropUrl: FALLBACK_BACKDROPS[0],
      genres: ["Phim chiếu rạp"],
      rating: 8.5,
      ageRating: "P",
      director: "Đang cập nhật",
      cast: "Đang cập nhật",
      format: "2D Digital",
    };
  }

  const normalizedTitle = movie.title.toLowerCase().trim();
  const matchedKey = Object.keys(KNOWN_MOVIES).find((key) =>
    normalizedTitle.includes(key)
  );

  const matched = matchedKey ? KNOWN_MOVIES[matchedKey] : undefined;

  const id = Number(movie.id) || 1;
  const posterFallback = FALLBACK_POSTERS[(id - 1) % FALLBACK_POSTERS.length];
  const backdropFallback = FALLBACK_BACKDROPS[(id - 1) % FALLBACK_BACKDROPS.length];

  return {
    posterUrl: matched?.posterUrl ?? posterFallback,
    backdropUrl: matched?.backdropUrl ?? backdropFallback,
    genres: matched?.genres ?? ["Phim điện ảnh", "Hành động"],
    rating: matched?.rating ?? 8.5,
    ageRating: matched?.ageRating ?? "C13",
    director: matched?.director ?? "Đạo diễn xuất sắc",
    cast: matched?.cast ?? "Dàn diễn viên nổi tiếng",
    format: matched?.format ?? "2D Digital Phụ đề",
    trailerTitle: matched?.trailerTitle,
  };
}

export function isVipSeat(seatNumber: string): boolean {
  // Rows B and C, or middle numbers (e.g. 2, 3, 4) can be VIP
  const match = seatNumber.match(/^([A-Z]+)(\d+)$/i);
  if (!match) return false;
  const row = match[1].toUpperCase();
  const num = parseInt(match[2], 10);
  return (row === "B" || row === "C") && num >= 2 && num <= 4;
}

export const SEAT_PRICES = {
  STANDARD: 90000,
  VIP: 110000,
} as const;

export function getSeatPrice(seatNumber: string): number {
  return isVipSeat(seatNumber) ? SEAT_PRICES.VIP : SEAT_PRICES.STANDARD;
}
