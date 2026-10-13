import api from "./axios";
import type { Movie } from "../types/movie";

export interface CreateMoviePayload {
  title: string;
  description: string;
  duration_minutes: number;
  release_date: string;
  poster_url?: string | null;
}

export async function getMovies(): Promise<Movie[]> {
  const response = await api.get<Movie[]>("/movies");
  return response.data;
}

export async function getMovieById(movieId: number): Promise<Movie> {
  const response = await api.get<Movie>(`/movies/${movieId}`);
  return response.data;
}

export async function createMovie(payload: CreateMoviePayload): Promise<Movie> {
  const response = await api.post<Movie>("/movies", payload);
  return response.data;
}

export async function uploadMovieImage(filename: string, imageData: string): Promise<string> {
  const response = await api.post<{ image_url: string }>("/movies/upload-image", {
    filename,
    image_data: imageData,
  });
  return response.data.image_url;
}

export async function updateMovie(movieId: number, payload: CreateMoviePayload): Promise<Movie> {
  const response = await api.put<Movie>(`/movies/${movieId}`, payload);
  return response.data;
}

export async function deleteMovie(movieId: number): Promise<{ message: string }> {
  const response = await api.delete<{ message: string }>(`/movies/${movieId}`);
  return response.data;
}

