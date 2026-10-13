from datetime import UTC, datetime, time, timedelta

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.application.schemas.analytics import (
    AnalyticsOverviewResponse,
    DashboardSummary,
    RecentBookingItem,
    RevenueTimelinePoint,
    RoomOccupancyStats,
    TopMovieStats,
)
from app.infrastructure.database.models import (
    BookingModel,
    BookingSeatModel,
    MovieModel,
    SeatModel,
    ShowtimeModel,
    UserModel,
)


def _is_vip_seat(row: str, number: int) -> bool:
    return row.upper() in ("B", "C") and 2 <= number <= 4


def _get_seat_price(row: str, number: int) -> int:
    return 110_000 if _is_vip_seat(row, number) else 90_000


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_overview(self, days: int | None = 7) -> AnalyticsOverviewResponse:
        now = datetime.now(UTC)
        if days is not None and days > 0:
            today = now.date()
            start_date = today - timedelta(days=days - 1)
            start_cutoff = datetime.combine(start_date, time.min, tzinfo=UTC)
        else:
            start_cutoff = None

        seat_price_expr = case(
            (
                and_(
                    func.upper(SeatModel.row).in_(["B", "C"]),
                    SeatModel.number.between(2, 4),
                ),
                110_000,
            ),
            else_=90_000,
        )

        # 1. Total revenue
        rev_query = (
            select(func.coalesce(func.sum(seat_price_expr), 0))
            .select_from(BookingModel)
            .join(BookingSeatModel, BookingSeatModel.booking_id == BookingModel.id)
            .join(SeatModel, SeatModel.id == BookingSeatModel.seat_id)
            .where(BookingModel.status == "CONFIRMED")
        )
        if start_cutoff is not None:
            rev_query = rev_query.where(BookingModel.created_at >= start_cutoff)
        total_revenue = int(self._session.scalar(rev_query) or 0)

        # 2. Total tickets
        tickets_query = (
            select(func.count(BookingSeatModel.id))
            .select_from(BookingModel)
            .join(BookingSeatModel, BookingSeatModel.booking_id == BookingModel.id)
            .where(BookingModel.status == "CONFIRMED")
        )
        if start_cutoff is not None:
            tickets_query = tickets_query.where(BookingModel.created_at >= start_cutoff)
        total_tickets = int(self._session.scalar(tickets_query) or 0)

        # 3. Total bookings
        bookings_query = (
            select(func.count(BookingModel.id))
            .select_from(BookingModel)
            .where(BookingModel.status == "CONFIRMED")
        )
        if start_cutoff is not None:
            bookings_query = bookings_query.where(BookingModel.created_at >= start_cutoff)
        total_bookings = int(self._session.scalar(bookings_query) or 0)

        # 4. Total customers (non-admin users registered in system)
        cust_query = select(func.count(UserModel.id)).where(UserModel.role != "admin")
        total_customers = int(self._session.scalar(cust_query) or 0)

        # 5. Room Occupancy
        room_names = self._session.scalars(
            select(SeatModel.room_name).distinct().order_by(SeatModel.room_name)
        ).all()
        if not room_names:
            room_names = ["ROOM_1", "ROOM_2"]

        room_stats: list[RoomOccupancyStats] = []
        for room in room_names:
            total_seats = int(
                self._session.scalar(
                    select(func.count(SeatModel.id)).where(SeatModel.room_name == room)
                )
                or 0
            )

            st_query = select(func.count(ShowtimeModel.id)).where(ShowtimeModel.room_name == room)
            if start_cutoff is not None:
                st_query = st_query.where(ShowtimeModel.start_time >= start_cutoff)
            showtimes_count = int(self._session.scalar(st_query) or 0)

            bk_seats_query = (
                select(func.count(BookingSeatModel.id))
                .select_from(BookingModel)
                .join(BookingSeatModel, BookingSeatModel.booking_id == BookingModel.id)
                .join(ShowtimeModel, ShowtimeModel.id == BookingModel.showtime_id)
                .where(ShowtimeModel.room_name == room, BookingModel.status == "CONFIRMED")
            )
            if start_cutoff is not None:
                bk_seats_query = bk_seats_query.where(BookingModel.created_at >= start_cutoff)
            booked_seats = int(self._session.scalar(bk_seats_query) or 0)

            distinct_showtimes_query = (
                select(func.count(func.distinct(BookingModel.showtime_id)))
                .select_from(BookingModel)
                .join(ShowtimeModel, ShowtimeModel.id == BookingModel.showtime_id)
                .where(ShowtimeModel.room_name == room, BookingModel.status == "CONFIRMED")
            )
            if start_cutoff is not None:
                distinct_showtimes_query = distinct_showtimes_query.where(
                    BookingModel.created_at >= start_cutoff
                )
            distinct_booked_st = int(self._session.scalar(distinct_showtimes_query) or 0)

            effective_showtimes = max(showtimes_count, distinct_booked_st, 1 if booked_seats > 0 else 0)
            total_capacity = total_seats * effective_showtimes
            occ_rate = (
                round(min(100.0, (booked_seats / total_capacity * 100)), 1)
                if total_capacity > 0
                else 0.0
            )

            room_stats.append(
                RoomOccupancyStats(
                    room_name=room,
                    total_seats=total_seats,
                    booked_seats=booked_seats,
                    total_capacity=total_capacity,
                    occupancy_rate=occ_rate,
                )
            )

        total_cap_all = sum(r.total_capacity for r in room_stats)
        total_booked_all = sum(r.booked_seats for r in room_stats)
        avg_occupancy_rate = (
            round((total_booked_all / total_cap_all * 100), 1) if total_cap_all > 0 else 0.0
        )

        summary = DashboardSummary(
            total_revenue=total_revenue,
            total_tickets=total_tickets,
            total_bookings=total_bookings,
            total_customers=total_customers,
            average_occupancy_rate=avg_occupancy_rate,
        )

        # 6. Revenue Timeline
        timeline_query = (
            select(
                func.date(BookingModel.created_at).label("booking_date"),
                func.coalesce(func.sum(seat_price_expr), 0).label("revenue"),
                func.count(BookingSeatModel.id).label("tickets"),
            )
            .select_from(BookingModel)
            .join(BookingSeatModel, BookingSeatModel.booking_id == BookingModel.id)
            .join(SeatModel, SeatModel.id == BookingSeatModel.seat_id)
            .where(BookingModel.status == "CONFIRMED")
        )
        if start_cutoff is not None:
            timeline_query = timeline_query.where(BookingModel.created_at >= start_cutoff)
        timeline_query = timeline_query.group_by("booking_date").order_by("booking_date")
        timeline_rows = self._session.execute(timeline_query).all()

        if days is not None and days > 0:
            today_d = now.date()
            date_points: dict[str, dict[str, int]] = {
                (today_d - timedelta(days=i)).isoformat(): {"revenue": 0, "tickets": 0}
                for i in range(days - 1, -1, -1)
            }
            for row in timeline_rows:
                date_key = str(row.booking_date)[:10]
                if date_key in date_points:
                    date_points[date_key]["revenue"] = int(row.revenue or 0)
                    date_points[date_key]["tickets"] = int(row.tickets or 0)
                else:
                    date_points[date_key] = {
                        "revenue": int(row.revenue or 0),
                        "tickets": int(row.tickets or 0),
                    }
            timeline = [
                RevenueTimelinePoint(date=k, revenue=v["revenue"], tickets=v["tickets"])
                for k, v in sorted(date_points.items())
            ]
        else:
            timeline = [
                RevenueTimelinePoint(
                    date=str(row.booking_date)[:10],
                    revenue=int(row.revenue or 0),
                    tickets=int(row.tickets or 0),
                )
                for row in timeline_rows
            ]

        # 7. Top Movies
        top_movies_query = (
            select(
                MovieModel.id.label("movie_id"),
                MovieModel.title.label("title"),
                MovieModel.poster_url.label("poster_url"),
                func.count(BookingSeatModel.id).label("tickets_sold"),
                func.coalesce(func.sum(seat_price_expr), 0).label("total_revenue"),
            )
            .select_from(MovieModel)
            .join(ShowtimeModel, ShowtimeModel.movie_id == MovieModel.id)
            .join(BookingModel, BookingModel.showtime_id == ShowtimeModel.id)
            .join(BookingSeatModel, BookingSeatModel.booking_id == BookingModel.id)
            .join(SeatModel, SeatModel.id == BookingSeatModel.seat_id)
            .where(BookingModel.status == "CONFIRMED")
        )
        if start_cutoff is not None:
            top_movies_query = top_movies_query.where(BookingModel.created_at >= start_cutoff)
        top_movies_query = (
            top_movies_query.group_by(MovieModel.id, MovieModel.title, MovieModel.poster_url)
            .order_by(desc("total_revenue"), desc("tickets_sold"))
            .limit(10)
        )
        top_rows = self._session.execute(top_movies_query).all()
        top_movies = [
            TopMovieStats(
                movie_id=row.movie_id,
                title=row.title,
                poster_url=row.poster_url,
                tickets_sold=int(row.tickets_sold or 0),
                total_revenue=int(row.total_revenue or 0),
            )
            for row in top_rows
        ]

        # 8. Recent Bookings (5 - 10 items)
        recent_models = self._session.scalars(
            select(BookingModel)
            .options(
                selectinload(BookingModel.user),
                selectinload(BookingModel.showtime).selectinload(ShowtimeModel.movie),
                selectinload(BookingModel.booking_seats),
            )
            .order_by(BookingModel.created_at.desc(), BookingModel.id.desc())
            .limit(10)
        ).all()

        seat_ids = [bs.seat_id for b in recent_models for bs in b.booking_seats]
        seats_by_id: dict[int, SeatModel] = {}
        if seat_ids:
            seats_by_id = {
                s.id: s
                for s in self._session.scalars(
                    select(SeatModel).where(SeatModel.id.in_(seat_ids))
                ).all()
            }

        recent_bookings: list[RecentBookingItem] = []
        for b in recent_models:
            labels = [
                f"{seats_by_id[bs.seat_id].row}{seats_by_id[bs.seat_id].number}"
                for bs in b.booking_seats
                if bs.seat_id in seats_by_id
            ]
            total_amount = sum(
                _get_seat_price(seats_by_id[bs.seat_id].row, seats_by_id[bs.seat_id].number)
                for bs in b.booking_seats
                if bs.seat_id in seats_by_id
            )
            recent_bookings.append(
                RecentBookingItem(
                    booking_id=b.id,
                    customer_name=b.user.full_name if b.user else "Khách hàng",
                    customer_email=b.user.email if b.user else "",
                    movie_title=b.showtime.movie.title if b.showtime and b.showtime.movie else "Không rõ",
                    showtime_start=b.showtime.start_time if b.showtime else b.created_at,
                    room_name=b.showtime.room_name if b.showtime else "N/A",
                    seats_count=len(b.booking_seats),
                    seat_labels=labels,
                    total_amount=total_amount,
                    status=b.status,
                    created_at=b.created_at,
                )
            )

        return AnalyticsOverviewResponse(
            summary=summary,
            revenue_timeline=timeline,
            top_movies=top_movies,
            room_occupancy=room_stats,
            recent_bookings=recent_bookings,
        )

