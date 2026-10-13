from datetime import datetime
from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_revenue: int = Field(description="Tổng doanh thu từ các vé đã bán (VNĐ)")
    total_tickets: int = Field(description="Tổng số vé bán thành công")
    total_bookings: int = Field(description="Tổng số đơn đặt vé CONFIRMED")
    total_customers: int = Field(description="Tổng số khách hàng đăng ký")
    average_occupancy_rate: float = Field(default=0.0, description="Tỷ lệ lấp đầy ghế trung bình (%)")


class RevenueTimelinePoint(BaseModel):
    date: str = Field(description="Ngày định dạng YYYY-MM-DD")
    revenue: int = Field(description="Doanh thu trong ngày (VNĐ)")
    tickets: int = Field(description="Số vé bán ra trong ngày")


class TopMovieStats(BaseModel):
    movie_id: int
    title: str
    poster_url: str | None = None
    tickets_sold: int
    total_revenue: int


class RoomOccupancyStats(BaseModel):
    room_name: str
    total_seats: int
    booked_seats: int
    total_capacity: int
    occupancy_rate: float


class RecentBookingItem(BaseModel):
    booking_id: int
    customer_name: str
    customer_email: str
    movie_title: str
    showtime_start: datetime
    room_name: str
    seats_count: int
    seat_labels: list[str]
    total_amount: int
    status: str
    created_at: datetime


class AnalyticsOverviewResponse(BaseModel):
    summary: DashboardSummary
    revenue_timeline: list[RevenueTimelinePoint]
    top_movies: list[TopMovieStats]
    room_occupancy: list[RoomOccupancyStats]
    recent_bookings: list[RecentBookingItem]

