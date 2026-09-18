export interface Showtime {
  id: number;
  movie_id: number;
  start_time: string;
  room_name: string;
  created_at: string | null;
}

export interface Seat {
  seat_id: number;
  seat_number: string;
  available: boolean;
}

export interface SeatAvailability {
  showtime_id: number;
  seats: Seat[];
}
