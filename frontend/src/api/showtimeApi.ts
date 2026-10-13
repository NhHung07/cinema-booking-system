import api from "./axios";
import type {
  CreateShowtimePayload,
  SeatAvailability,
  Showtime,
  UpdateShowtimePayload,
} from "../types/showtime";

export async function getShowtimes(movieId?: number): Promise<Showtime[]> {
  const response = await api.get<Showtime[]>("/showtimes", {
    params: movieId ? { movie_id: movieId } : undefined,
  });
  return response.data;
}

export async function getShowtime(showtimeId: number): Promise<Showtime> {
  const response = await api.get<Showtime>(`/showtimes/${showtimeId}`);
  return response.data;
}

export async function getShowtimeSeats(showtimeId: number): Promise<SeatAvailability> {
  const response = await api.get<SeatAvailability>(`/showtimes/${showtimeId}/seats`);
  return response.data;
}

export async function createShowtime(payload: CreateShowtimePayload): Promise<Showtime> {
  const response = await api.post<Showtime>("/showtimes", payload);
  return response.data;
}

export async function updateShowtime(
  showtimeId: number,
  payload: UpdateShowtimePayload,
): Promise<Showtime> {
  const response = await api.put<Showtime>(`/showtimes/${showtimeId}`, payload);
  return response.data;
}

export async function deleteShowtime(showtimeId: number): Promise<{ message: string }> {
  const response = await api.delete<{ message: string }>(`/showtimes/${showtimeId}`);
  return response.data;
}
