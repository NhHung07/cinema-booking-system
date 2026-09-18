import api from "./axios";
import type { Booking, CreateBookingPayload } from "../types/booking";

export async function createBooking(payload: CreateBookingPayload): Promise<Booking> {
  const response = await api.post<Booking>("/bookings", payload);
  return response.data;
}

export async function getMyBookings(): Promise<Booking[]> {
  const response = await api.get<Booking[]>("/bookings/me");
  return response.data;
}

export async function cancelBooking(bookingId: number): Promise<Booking> {
  const response = await api.delete<Booking>(`/bookings/${bookingId}`);
  return response.data;
}
