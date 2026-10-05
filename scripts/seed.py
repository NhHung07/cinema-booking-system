"""Tạo dữ liệu demo gồm 6 phim và mang tính idempotent sau khi chạy `alembic upgrade head`."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

# Cho phép lệnh tài liệu `python scripts/seed.py` import được package app.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.infrastructure.database.models import MovieModel, SeatModel, ShowtimeModel
from app.infrastructure.database.session import SessionLocal

DEMO_MOVIES = [
    {
        "title": "Interstellar",
        "description": "Một nhóm nhà thám hiểm du hành qua lỗ sâu không gian để tìm kiếm tương lai cho nhân loại.",
        "duration_minutes": 169,
        "release_date": datetime(2014, 11, 7, tzinfo=UTC).date(),
    },
    {
        "title": "Inception",
        "description": "Một kẻ đánh cắp thông tin xâm nhập tiềm thức con người để cấy ghép ý tưởng qua những giấc mơ.",
        "duration_minutes": 148,
        "release_date": datetime(2010, 7, 16, tzinfo=UTC).date(),
    },
    {
        "title": "Dune: Part Two",
        "description": "Paul Atreides liên minh cùng Chani và tộc người Fremen để trả thù những kẻ đã hủy diệt gia tộc mình.",
        "duration_minutes": 166,
        "release_date": datetime(2024, 3, 1, tzinfo=UTC).date(),
    },
    {
        "title": "Oppenheimer",
        "description": "Câu chuyện về nhà vật lý lý thuyết J. Robert Oppenheimer và dự án Manhattan chế tạo bom nguyên tử.",
        "duration_minutes": 180,
        "release_date": datetime(2023, 7, 21, tzinfo=UTC).date(),
    },
    {
        "title": "The Dark Knight",
        "description": "Hiểm họa Joker trỗi dậy tại Gotham, buộc Người Dơi phải bước qua lằn ranh mỏng manh giữa anh hùng và kẻ trừng phạt.",
        "duration_minutes": 152,
        "release_date": datetime(2008, 7, 18, tzinfo=UTC).date(),
    },
    {
        "title": "Avatar: The Way of Water",
        "description": "Jake Sully và gia đình phải rời bỏ tổ ấm rừng rậm để nương tựa vào các bộ tộc miền biển Pandora trước đợt xâm lăng mới.",
        "duration_minutes": 192,
        "release_date": datetime(2022, 12, 16, tzinfo=UTC).date(),
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
                )
                session.add(movie)
                session.flush()
            else:
                movie.description = m_data["description"]
                movie.duration_minutes = m_data["duration_minutes"]
                movie.release_date = m_data["release_date"]
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

        session.commit()
    print("Seed data is ready (6 movies).")


if __name__ == "__main__":
    main()
