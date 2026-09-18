export type BookingStatus = "CONFIRMED" | "CANCELLED";

export interface CreateBookingPayload {
  showtime_id: number;
  seat_ids: number[];
}

export interface Booking {
  id: number;
  user_id: number;
  showtime_id: number;
  status: BookingStatus;
  created_at: string | null;
  seat_ids: number[];
}
