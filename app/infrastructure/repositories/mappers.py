from app.domain.entities import Booking, BookingStatus, Movie, Seat, Showtime, User
from app.infrastructure.database.models import BookingModel, MovieModel, SeatModel, ShowtimeModel, UserModel


def to_user(model: UserModel) -> User:
    return User(model.id, model.email, model.password_hash, model.full_name, model.created_at)


def to_movie(model: MovieModel) -> Movie:
    return Movie(model.id, model.title, model.description, model.duration_minutes, model.release_date, model.created_at)


def to_showtime(model: ShowtimeModel) -> Showtime:
    return Showtime(model.id, model.movie_id, model.start_time, model.room_name, model.created_at)


def to_seat(model: SeatModel) -> Seat:
    return Seat(model.id, model.room_name, model.row, model.number)


def to_booking(model: BookingModel) -> Booking:
    return Booking(
        id=model.id,
        user_id=model.user_id,
        showtime_id=model.showtime_id,
        status=BookingStatus(model.status),
        created_at=model.created_at,
        seat_ids=[item.seat_id for item in model.booking_seats],
    )
