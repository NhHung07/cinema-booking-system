export interface Movie {
  id: number;
  title: string;
  description: string;
  duration_minutes: number;
  release_date: string;
  poster_url?: string | null;
  created_at: string | null;
}

export interface CreateMoviePayload {
  title: string;
  description: string;
  duration_minutes: number;
  release_date: string;
  poster_url?: string | null;
}

export interface UpdateMoviePayload {
  title: string;
  description: string;
  duration_minutes: number;
  release_date: string;
  poster_url?: string | null;
}
