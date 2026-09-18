import api from "./axios";
import type { Movie } from "../types/movie";

export async function getMovies(): Promise<Movie[]> {
  const response = await api.get<Movie[]>("/movies");
  return response.data;
}

export async function getMovieById(movieId: number): Promise<Movie> {
  const response = await api.get<Movie>(`/movies/${movieId}`);
  return response.data;
}
