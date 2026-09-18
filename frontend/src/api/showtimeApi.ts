import api from "./axios";
import type { SeatAvailability, Showtime } from "../types/showtime";

export async function getShowtimes(movieId?: number): Promise<Showtime[]> {
  const response = await api.get<Showtime[]>("/showtimes", {
    params: movieId ? { movie_id: movieId } : undefined,
  });
  return response.data;
}

export async function getShowtimeSeats(showtimeId: number): Promise<SeatAvailability> {
  const response = await api.get<SeatAvailability>(`/showtimes/${showtimeId}/seats`);
  return response.data;
}
