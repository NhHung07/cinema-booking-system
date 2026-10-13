export interface DashboardSummary {
  total_revenue: number;
  total_tickets: number;
  total_bookings: number;
  total_customers: number;
  average_occupancy_rate: number;
}

export interface RevenueTimelinePoint {
  date: string;
  revenue: number;
  tickets: number;
}

export interface TopMovieStats {
  movie_id: number;
  title: string;
  poster_url: string | null;
  tickets_sold: number;
  total_revenue: number;
}

export interface RoomOccupancyStats {
  room_name: string;
  total_seats: number;
  booked_seats: number;
  total_capacity: number;
  occupancy_rate: number;
}

export interface RecentBookingItem {
  booking_id: number;
  customer_name: string;
  customer_email: string;
  movie_title: string;
  showtime_start: string;
  room_name: string;
  seats_count: number;
  seat_labels: string[];
  total_amount: number;
  status: string;
  created_at: string;
}

export interface AnalyticsOverviewResponse {
  summary: DashboardSummary;
  revenue_timeline: RevenueTimelinePoint[];
  top_movies: TopMovieStats[];
  room_occupancy: RoomOccupancyStats[];
  recent_bookings: RecentBookingItem[];
}

