"""Tạo dữ liệu demo gồm 6 phim và mang tính idempotent sau khi chạy `alembic upgrade head`."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

# Cho phép lệnh tài liệu `python scripts/seed.py` import được package app.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.core.security import hash_password
from app.infrastructure.database.models import MovieModel, SeatModel, ShowtimeModel, UserModel
from app.infrastructure.database.session import SessionLocal

DEMO_MOVIES = [
    {
        "title": "Interstellar",
        "description": "Một nhóm nhà thám hiểm du hành qua lỗ sâu không gian để tìm kiếm tương lai cho nhân loại.",
        "duration_minutes": 169,
        "release_date": datetime(2014, 11, 7, tzinfo=UTC).date(),
        "poster_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=700&q=85",
    },
    {
        "title": "Inception",
        "description": "Một kẻ đánh cắp thông tin xâm nhập tiềm thức con người để cấy ghép ý tưởng qua những giấc mơ.",
        "duration_minutes": 148,
        "release_date": datetime(2010, 7, 16, tzinfo=UTC).date(),
        "poster_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=700&q=85",
    },
    {
        "title": "Dune: Part Two",
        "description": "Paul Atreides liên minh cùng Chani và tộc người Fremen để trả thù những kẻ đã hủy diệt gia tộc mình.",
        "duration_minutes": 166,
        "release_date": datetime(2024, 3, 1, tzinfo=UTC).date(),
        "poster_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=700&q=85",
    },
    {
        "title": "Oppenheimer",
        "description": "Câu chuyện về nhà vật lý lý thuyết J. Robert Oppenheimer và dự án Manhattan chế tạo bom nguyên tử.",
        "duration_minutes": 180,
        "release_date": datetime(2023, 7, 21, tzinfo=UTC).date(),
        "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=700&q=85",
    },
    {
        "title": "The Dark Knight",
        "description": "Hiểm họa Joker trỗi dậy tại Gotham, buộc Người Dơi phải bước qua lằn ranh mỏng manh giữa anh hùng và kẻ trừng phạt.",
        "duration_minutes": 152,
        "release_date": datetime(2008, 7, 18, tzinfo=UTC).date(),
        "poster_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=700&q=85",
    },
    {
        "title": "Avatar: The Way of Water",
        "description": "Jake Sully và gia đình phải rời bỏ tổ ấm rừng rậm để nương tựa vào các bộ tộc miền biển Pandora trước đợt xâm lăng mới.",
        "duration_minutes": 192,
        "release_date": datetime(2022, 12, 16, tzinfo=UTC).date(),
        "poster_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=700&q=85",
    },
]


def main() -> None:
    with SessionLocal() as session:
        movie_map: dict[str, MovieModel] = {}
        for m_data in DEMO_MOVIES:
            movie = session.scalar(select(MovieModel).where(MovieModel.title == m_data["title"]))
            if movie is None:
                movie = MovieModel(
                    title=m_data["title"],
                    description=m_data["description"],
                    duration_minutes=m_data["duration_minutes"],
                    release_date=m_data["release_date"],
                    poster_url=m_data.get("poster_url"),
                )
                session.add(movie)
                session.flush()
            else:
                movie.description = m_data["description"]
                movie.duration_minutes = m_data["duration_minutes"]
                movie.release_date = m_data["release_date"]
                movie.poster_url = m_data.get("poster_url")
            movie_map[m_data["title"]] = movie

        for room in ("ROOM_1", "ROOM_2"):
            if not session.scalar(select(SeatModel.id).where(SeatModel.room_name == room).limit(1)):
                session.add_all(
                    [SeatModel(room_name=room, row=row, number=number) for row in "ABC" for number in range(1, 6)]
                )

        session.flush()

        day1 = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        day2 = day1 + timedelta(days=1)

        planned_showtimes = [
            # Ngày 1
            ("Interstellar", "ROOM_1", day1 + timedelta(hours=1)),
            ("Inception", "ROOM_1", day1 + timedelta(hours=5)),
            ("Oppenheimer", "ROOM_1", day1 + timedelta(hours=9)),
            ("Dune: Part Two", "ROOM_2", day1 + timedelta(hours=1, minutes=30)),
            ("The Dark Knight", "ROOM_2", day1 + timedelta(hours=5, minutes=30)),
            ("Avatar: The Way of Water", "ROOM_2", day1 + timedelta(hours=9, minutes=30)),
            # Ngày 2
            ("The Dark Knight", "ROOM_1", day2 + timedelta(hours=1)),
            ("Dune: Part Two", "ROOM_1", day2 + timedelta(hours=5)),
            ("Interstellar", "ROOM_1", day2 + timedelta(hours=9)),
            ("Avatar: The Way of Water", "ROOM_2", day2 + timedelta(hours=1)),
            ("Inception", "ROOM_2", day2 + timedelta(hours=5, minutes=30)),
            ("Oppenheimer", "ROOM_2", day2 + timedelta(hours=9)),
        ]

        for title, room, st_time in planned_showtimes:
            movie = movie_map.get(title)
            if movie is not None:
                exists = session.scalar(
                    select(ShowtimeModel.id)
                    .where(
                        ShowtimeModel.movie_id == movie.id,
                        ShowtimeModel.room_name == room,
                        ShowtimeModel.start_time == st_time,
                    )
                    .limit(1)
                )
                if not exists:
                    session.add(ShowtimeModel(movie_id=movie.id, room_name=room, start_time=st_time))

        # Seed demo users (idempotent)
        demo_users = [
            ("admin@cinema.com", "admin123", "Quản Trị Viên", "admin"),
            ("demo@gmail.com", "password123", "Người Dùng Thử Nghiệm", "user"),
            ("nguyenvana@gmail.com", "password123", "Nguyễn Văn A", "user"),
            ("tranthib@gmail.com", "password123", "Trần Thị B", "user"),
            ("lequangc@gmail.com", "password123", "Lê Quang C", "user"),
            ("phamthid@gmail.com", "password123", "Phạm Thị D", "user"),
        ]
        user_map: dict[str, UserModel] = {}
        for email, pwd, name, role in demo_users:
            user = session.scalar(select(UserModel).where(UserModel.email == email))
            if user is None:
                user = UserModel(
                    email=email,
                    password_hash=hash_password(pwd),
                    full_name=name,
                    role=role,
                )
                session.add(user)
                session.flush()
            else:
                user.role = role
                user.password_hash = hash_password(pwd)
                user.full_name = name
            user_map[email] = user

        # Seed past showtimes & realistic bookings across the last 7 days (idempotent)
        now = datetime.now(UTC)
        past_showtime_specs = [
            # (days_ago, hour, minute, movie_title, room_name, [(user_email, [seat_row_num]), ...])
            (
                6, 14, 0, "Interstellar", "ROOM_1",
                [("demo@gmail.com", [("A", 1), ("A", 2)]), ("nguyenvana@gmail.com", [("B", 3)])]
            ),
            (
                5, 18, 30, "Dune: Part Two", "ROOM_2",
                [("tranthib@gmail.com", [("B", 2), ("B", 3), ("A", 1)])]
            ),
            (
                4, 19, 0, "Oppenheimer", "ROOM_1",
                [("lequangc@gmail.com", [("B", 2), ("B", 4)]), ("phamthid@gmail.com", [("A", 3)])]
            ),
            (
                3, 15, 30, "The Dark Knight", "ROOM_2",
                [("nguyenvana@gmail.com", [("C", 2), ("C", 3)]), ("demo@gmail.com", [("A", 1), ("A", 2)])]
            ),
            (
                2, 20, 0, "Avatar: The Way of Water", "ROOM_1",
                [("tranthib@gmail.com", [("B", 3), ("C", 3)]), ("lequangc@gmail.com", [("A", 4)])]
            ),
            (
                1, 17, 0, "Dune: Part Two", "ROOM_2",
                [("phamthid@gmail.com", [("B", 2), ("B", 3), ("B", 4)]), ("nguyenvana@gmail.com", [("A", 2), ("A", 3)])]
            ),
            (
                0, 11, 0, "Inception", "ROOM_1",
                [("demo@gmail.com", [("B", 3), ("C", 2)]), ("tranthib@gmail.com", [("A", 1)])]
            ),
            (
                0, 19, 30, "Oppenheimer", "ROOM_2",
                [("lequangc@gmail.com", [("C", 3), ("C", 4)]), ("phamthid@gmail.com", [("A", 5)])]
            ),
        ]

        from app.infrastructure.database.models import BookingModel, BookingSeatModel

        for days_ago, hour, minute, m_title, room, bookings_info in past_showtime_specs:
            movie = movie_map.get(m_title)
            if not movie:
                continue
            st_date = (now - timedelta(days=days_ago)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            st = session.scalar(
                select(ShowtimeModel).where(
                    ShowtimeModel.movie_id == movie.id,
                    ShowtimeModel.room_name == room,
                    ShowtimeModel.start_time == st_date,
                )
            )
            if not st:
                st = ShowtimeModel(movie_id=movie.id, room_name=room, start_time=st_date)
                session.add(st)
                session.flush()

            # Create bookings for this showtime if not already created
            for u_email, seat_tuples in bookings_info:
                target_user = user_map.get(u_email)
                if not target_user:
                    continue

                existing_booking = session.scalar(
                    select(BookingModel).where(
                        BookingModel.user_id == target_user.id,
                        BookingModel.showtime_id == st.id,
                    )
                )
                if not existing_booking:
                    booking_time = st_date - timedelta(hours=3)
                    new_booking = BookingModel(
                        user_id=target_user.id,
                        showtime_id=st.id,
                        status="CONFIRMED",
                        created_at=booking_time,
                    )
                    session.add(new_booking)
                    session.flush()

                    for row_code, num in seat_tuples:
                        seat_obj = session.scalar(
                            select(SeatModel).where(
                                SeatModel.room_name == room,
                                SeatModel.row == row_code,
                                SeatModel.number == num,
                            )
                        )
                        if seat_obj:
                            session.add(
                                BookingSeatModel(
                                    booking_id=new_booking.id,
                                    showtime_id=st.id,
                                    seat_id=seat_obj.id,
                                )
                            )

        session.commit()
    print("Seed data is ready (6 movies, demo accounts, showtimes, and recent bookings).")



if __name__ == "__main__":
    main()
