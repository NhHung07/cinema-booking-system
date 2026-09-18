# Cinema Booking System Backend

Backend FastAPI hoạt động đầy đủ cho bài tập lớn hệ thống đặt vé rạp phim. Project hỗ trợ user, JWT login, movie/showtime catalogue, seat availability, booking theo transaction, cancellation, Alembic migration, test, Docker và Locust scenario cơ bản.

## Kiến trúc

```text
API (FastAPI routes)
        ↓
Application / Business services
        ↓
Domain repository interfaces
        ↓
Infrastructure SQLAlchemy repositories
        ↓
PostgreSQL
```

Business layer không có import FastAPI hoặc SQLAlchemy. Xem [architecture.md](docs/architecture.md) để hiểu trách nhiệm từng layer, dependency direction, transaction flow, cùng input/output của booking use case.

## Cấu trúc project

```text
app/
  api/                 HTTP routes và authentication dependency dùng chung
  application/         Use-case services và request/response schemas
  domain/              Dataclass entities và repository interfaces
  infrastructure/      SQLAlchemy models, session và repository adapters
  core/                Settings, JWT/password security và typed errors
migrations/            Alembic schema migrations
scripts/seed.py        Demo catalogue tùy chọn
tests/unit/            BookingService test không dùng database
tests/integration/     API test với SQLite database độc lập
locust/                Read-heavy load scenario cơ bản
docs/                  Tài liệu kiến trúc và database
```

## Database

Các relationship chính là `Movie → Showtime`, `User → Booking`, và `Booking ↔ Seat` thông qua `BookingSeat`. Database rule quan trọng nhất là `UNIQUE(showtime_id, seat_id)`: PostgreSQL, thay vì Python pre-check có race condition, là tầng cuối cùng chống double booking. Xem [database.md](docs/database.md) để biết fields, foreign keys, ERD, constraints và lý do của các indexes.

## Authentication

`POST /auth/register` hash password bằng **Argon2** thông qua `pwdlib`. Argon2 được chọn thay vì bcrypt integration trực tiếp vì đây là password-hashing algorithm hiện đại, memory-hard và `pwdlib` cung cấp API đơn giản, được duy trì. Plaintext password không bao giờ được persist.

`POST /auth/login` trả về JWT đã ký, trong đó `sub` là user id và có expiry. Các protected route dùng chung một FastAPI `get_current_user()` dependency; Swagger hiển thị HTTP Bearer security và route không lặp lại token-decoding logic.

## Chạy local

Yêu cầu Python 3.12 trở lên.

```bash
python -m venv .venv
```

Trên PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Đặt `JWT_SECRET_KEY` khác giá trị mặc định trong `.env`, khởi động PostgreSQL, sau đó migration và chạy API:

```bash
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Swagger ở <http://localhost:8000/docs>; ReDoc ở <http://localhost:8000/redoc>.

## Chạy bằng Docker

```bash
docker compose up --build
```

API đợi PostgreSQL healthcheck, chạy `alembic upgrade head`, rồi khởi động tại <http://localhost:8000>. Để thêm demo catalogue data:

```bash
docker compose exec api python scripts/seed.py
```

## Tổng quan API

| Method | Endpoint | Authentication | Kết quả |
| --- | --- | --- | --- |
| POST | `/auth/register` | Không | Tạo account |
| POST | `/auth/login` | Không | Nhận Bearer JWT |
| GET | `/movies`, `/movies/{id}` | Không | Đọc movie |
| GET | `/showtimes?movie_id=&date=` | Không | Đọc showtime |
| GET | `/showtimes/{id}/seats` | Không | Đọc availability snapshot |
| POST | `/bookings` | Bearer JWT | Book các seat duy nhất theo transaction |
| GET | `/bookings/me`, `/bookings/{id}` | Bearer JWT | Chỉ đọc booking của caller |
| DELETE | `/bookings/{id}` | Bearer JWT | Cancel và release seat |

Create booking response là `201`; seat conflict là `409`; thiếu hoặc không hợp lệ Bearer authentication là `401`; truy cập booking của user khác là `403`.

## Tests

```bash
pytest
```

Unit test dùng fake repository và không tạo database. Integration test dùng FastAPI test client cùng isolated in-memory SQLite database để chạy được không cần Docker. Production sử dụng PostgreSQL; Alembic migration là schema source of truth.

## Load test

Sau khi service chạy và có seed data:

```bash
locust -f locust/locustfile.py --host http://localhost:8000
```

Phase 1 scenario gọi `GET /movies`, `GET /showtimes`, và `GET /showtimes/{id}/seats`.

## Frontend MVP

Frontend React + Vite + TypeScript nằm trong [`frontend/`](frontend/). Frontend gọi trực tiếp REST API hiện có, dùng JWT Bearer token qua `AuthContext`, và hỗ trợ register, login, movies, showtimes, chọn ghế, booking, cancellation và logout.

Xem [hướng dẫn frontend](frontend/README.md) để chạy toàn hệ thống với backend ở `http://localhost:8000` và frontend ở `http://localhost:5173`.
