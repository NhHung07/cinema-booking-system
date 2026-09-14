# TASKS — Cinema Booking System

## 1. Mục tiêu dự án

Xây dựng backend cho hệ thống đặt vé xem phim bằng Python, theo kiến trúc phân tầng rõ ràng:

```text
Client
  ↓
API Layer
  ↓
Business / Application Layer
  ↓
Repository / Data Access Layer
  ↓
PostgreSQL
```

Stack đề xuất:

- Python 3.12+
- FastAPI
- Pydantic
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- JWT Authentication
- pytest
- Docker + Docker Compose
- Locust
- Redis (chỉ xem xét ở Pha 2 nếu benchmark cho thấy cần)

Quy ước sử dụng tài liệu này:

- Đây là nguồn theo dõi phạm vi và Definition of Done chung của nhóm.
- Mỗi checkbox chỉ được đánh dấu hoàn thành sau khi có code hoặc tài liệu tương ứng và đã được kiểm tra.
- Công việc hằng ngày được tách thành GitHub Issues; không dùng một branch dài hạn cho từng thành viên.

---

# 2. Quy ước phân công

- Thành viên 1: API + Authentication
- Thành viên 2: Business / Domain
- Thành viên 3: Database + Infrastructure
- Các phần kiến trúc, integration, review, benchmark và Pha 2: cả nhóm cùng tham gia
- Không chia code hoàn toàn độc lập theo kiểu “ai làm phần người đó và không biết phần còn lại”
- Mỗi thành viên là primary owner của phần mình phụ trách nhưng phải review code chéo

### Ranh giới ownership

| Khu vực | Primary owner | Điểm tích hợp bắt buộc |
|---|---|---|
| `app/api/`, `app/schemas/`, `app/core/security.py` | Thành viên 1 | Dùng service và dependency đã thống nhất |
| `app/application/`, `app/domain/` | Thành viên 2 | Repository interface không import SQLAlchemy |
| `app/infrastructure/`, `alembic/`, Docker, `load_tests/` | Thành viên 3 | Implement đúng interface của Thành viên 2 |
| `app/core/config.py`, `.env.example` | Thành viên 3 primary; cả nhóm review | Là contract cấu hình dùng chung, không được định nghĩa lại ở layer khác |
| Tests tích hợp, tài liệu, benchmark | Cả nhóm | Có ít nhất một reviewer ngoài tác giả |

Thay đổi vào API contract, domain contract, database schema hoặc environment contract phải được ghi trong Issue và review trước khi merge.

---

# 3. Thành viên 1 — API + Authentication

## 3.1. Trách nhiệm chính

Phụ trách tầng giao tiếp giữa client và backend.

### Nhiệm vụ

- [ ] Thiết lập FastAPI application
- [ ] Tạo `app/main.py`
- [ ] Cấu hình router
- [ ] Tổ chức thư mục `app/api/`
- [ ] Tổ chức `app/schemas/`
- [ ] Tạo request/response schemas bằng Pydantic
- [ ] Viết REST API endpoints
- [ ] Xử lý HTTP status code
- [ ] Xử lý validation
- [ ] Viết exception handler ở tầng API
- [ ] Cấu hình OpenAPI / Swagger
- [ ] Implement authentication flow
- [ ] Implement password hashing
- [ ] Implement JWT generation
- [ ] Implement JWT verification
- [ ] Implement authentication dependency/middleware dùng chung
- [ ] Đảm bảo authentication không bị viết lặp trong từng endpoint
- [ ] Bảo vệ ít nhất 1 GET endpoint
- [ ] Bảo vệ ít nhất 1 POST endpoint
- [ ] Viết integration test cơ bản cho API do mình phụ trách

---

## 3.2. API cần triển khai

### Authentication

- [ ] `POST /auth/register`
- [ ] `POST /auth/login`

### Movie

- [ ] `GET /movies`
- [ ] `GET /movies/{movie_id}`

### Showtime

- [ ] `GET /showtimes`
- [ ] `GET /showtimes/{showtime_id}`
- [ ] `GET /showtimes/{showtime_id}/seats`

### Booking

- [ ] `POST /bookings` — yêu cầu đăng nhập
- [ ] `GET /bookings/me` — yêu cầu đăng nhập
- [ ] `GET /bookings/{booking_id}` — yêu cầu đăng nhập
- [ ] `DELETE /bookings/{booking_id}` — yêu cầu đăng nhập

---

## 3.3. Quy tắc kiến trúc phải tuân thủ

Không đặt business logic vào API layer.

Không viết kiểu:

```python
@router.post("/bookings")
def create_booking(...):
    if seat.is_booked:
        ...
```

API layer chỉ nên:

1. Nhận request
2. Validate request
3. Lấy current user nếu cần
4. Gọi service
5. Convert kết quả thành response
6. Map domain exception thành HTTP response

Ví dụ luồng đúng:

```text
POST /bookings
      ↓
Booking Router
      ↓
BookingService
      ↓
BookingRepository
```

---

## 3.4. Deliverable của Thành viên 1

- [ ] FastAPI app chạy được
- [ ] Swagger hoạt động
- [ ] Register hoạt động
- [ ] Login hoạt động
- [ ] JWT hoạt động
- [ ] Password được hash, không lưu plaintext
- [ ] Protected GET hoạt động
- [ ] Protected POST hoạt động
- [ ] Request validation hoạt động
- [ ] HTTP error response rõ ràng
- [ ] API không chứa business logic
- [ ] Có integration test cho các API quan trọng

---

# 4. Thành viên 2 — Business / Domain

## 4.1. Trách nhiệm chính

Phụ trách logic nghiệp vụ và phần kiến trúc cốt lõi của hệ thống.

### Nhiệm vụ

- [ ] Thiết kế domain model
- [ ] Tạo domain entities
- [ ] Thiết kế business rules
- [ ] Tạo service layer
- [ ] Tạo repository interfaces
- [ ] Tạo domain exceptions
- [ ] Viết unit test cho business logic
- [ ] Dùng Fake/Mock Repository để test
- [ ] Đảm bảo business layer không import FastAPI
- [ ] Đảm bảo business layer không import SQLAlchemy
- [ ] Đảm bảo business layer không phụ thuộc PostgreSQL
- [ ] Review dependency direction của toàn project

---

## 4.2. Domain entities

Tối thiểu cần xem xét:

- [ ] `User`
- [ ] `Movie`
- [ ] `Showtime`
- [ ] `Seat`
- [ ] `Booking`

Có thể bổ sung:

- [ ] `BookingSeat`
- [ ] `Theater`
- [ ] `Room`

Chỉ thêm entity nếu thật sự cần cho scope.

---

## 4.3. Service layer

### AuthService

- [ ] Register user
- [ ] Kiểm tra username/email đã tồn tại hay chưa
- [ ] Xác thực thông tin đăng nhập
- [ ] Không chứa code HTTP

### MovieService

- [ ] Lấy danh sách movie
- [ ] Lấy thông tin movie theo id

### ShowtimeService

- [ ] Lấy danh sách showtime
- [ ] Lấy showtime theo id
- [ ] Lấy trạng thái ghế theo showtime

### BookingService

- [ ] Tạo booking
- [ ] Kiểm tra showtime tồn tại
- [ ] Kiểm tra showtime chưa kết thúc
- [ ] Kiểm tra danh sách ghế hợp lệ
- [ ] Kiểm tra ghế chưa được đặt
- [ ] Tạo booking
- [ ] Lấy booking của user hiện tại
- [ ] Lấy booking theo id
- [ ] Chỉ cho phép user xem booking của chính mình
- [ ] Hủy booking
- [ ] Chỉ cho phép user hủy booking của chính mình

---

## 4.4. Business rules tối thiểu

- [ ] Không được đặt ghế đã được đặt
- [ ] Không được đặt ghế không thuộc showtime
- [ ] Booking phải có ít nhất một ghế
- [ ] Không được đặt showtime đã kết thúc
- [ ] User chỉ được xem booking của mình
- [ ] User chỉ được hủy booking của mình
- [ ] Không cho phép tạo dữ liệu nghiệp vụ không hợp lệ

Nếu nhóm thống nhất thêm rule:

- [ ] Không cho phép hủy vé sau thời điểm X
- [ ] Giới hạn số ghế tối đa trong một booking

---

## 4.5. Repository interfaces

Tạo interface/protocol cho tối thiểu:

### UserRepository

- [ ] `find_by_id`
- [ ] `find_by_username` hoặc `find_by_email`
- [ ] `create`

### MovieRepository

- [ ] `find_all`
- [ ] `find_by_id`

### ShowtimeRepository

- [ ] `find_all`
- [ ] `find_by_id`
- [ ] `get_available_seats`

### BookingRepository

- [ ] `create`
- [ ] `find_by_id`
- [ ] `find_by_user_id`
- [ ] `is_seat_booked`
- [ ] `delete` hoặc `cancel`

Repository interface không được chứa SQLAlchemy-specific type.

---

## 4.6. Unit test bắt buộc nên có

- [ ] Tạo booking thành công khi ghế available
- [ ] Không tạo booking khi ghế đã được đặt
- [ ] Không tạo booking nếu showtime không tồn tại
- [ ] Không tạo booking nếu showtime đã kết thúc
- [ ] Không tạo booking khi seat list rỗng
- [ ] User không được xem booking của user khác
- [ ] User không được hủy booking của user khác
- [ ] Hủy booking thành công với owner hợp lệ

---

## 4.7. Deliverable của Thành viên 2

- [ ] Domain entities rõ ràng
- [ ] Services hoạt động
- [ ] Repository interfaces đầy đủ
- [ ] Domain exceptions rõ ràng
- [ ] Business rules được test
- [ ] Unit tests chạy pass
- [ ] Business/Application layer không import FastAPI
- [ ] Business/Application layer không import SQLAlchemy
- [ ] Có thể test service mà không cần database thật

---

# 5. Thành viên 3 — Database + Infrastructure

## 5.1. Trách nhiệm chính

Phụ trách toàn bộ phần persistence, infrastructure, container và load testing.

### Nhiệm vụ

- [ ] Thiết kế database schema
- [ ] Cấu hình PostgreSQL
- [x] Tạo cấu hình SQLAlchemy engine/session nền tảng
- [ ] Tạo SQLAlchemy models
- [x] Tạo database session lifecycle
- [ ] Implement repository interfaces
- [x] Khởi tạo cấu trúc Alembic và kết nối metadata
- [ ] Viết migration
- [ ] Tạo seed data nếu cần
- [ ] Tạo Dockerfile
- [ ] Tạo docker-compose.yml
- [x] Chốt contract environment variables
- [x] Tạo `.env.example`
- [ ] Viết Locust load test
- [ ] Chuẩn bị benchmark script
- [ ] Hỗ trợ chạy benchmark trên Kaggle CPU

---

## 5.2. Database schema

Tối thiểu cần thiết kế:

- [ ] `users`
- [ ] `movies`
- [ ] `showtimes`
- [ ] `seats`
- [ ] `bookings`
- [ ] `booking_seats`

Xem xét thêm nếu cần:

- [ ] `theaters`
- [ ] `rooms`

---

## 5.3. Database constraints

Cần cân nhắc:

- [ ] Primary key
- [ ] Foreign key
- [ ] Unique constraint
- [ ] NOT NULL
- [ ] Index
- [ ] Referential integrity

Đặc biệt cần nghiên cứu cách chống duplicate booking cho cùng ghế và showtime.

---

## 5.4. SQLAlchemy

- [x] Cấu hình engine
- [x] Cấu hình session
- [x] Declarative base
- [ ] User model
- [ ] Movie model
- [ ] Showtime model
- [ ] Seat model
- [ ] Booking model
- [ ] BookingSeat model
- [ ] Relationship
- [ ] Repository implementation

Quyết định kỹ thuật:

- Dùng SQLAlchemy synchronous API và Psycopg 3 trong Pha 1 để giữ scope đơn giản.
- `app/infrastructure/database/session.py` tạo engine và session factory.
- Không tạo thêm database config module hoặc đọc `DATABASE_URL` trực tiếp ở repository.
- Unit test business logic dùng fake/mock repository và không cần database thật.

Ví dụ dependency:

```text
BookingService
      ↓
BookingRepository
      ↑
SQLAlchemyBookingRepository
      ↓
SQLAlchemy
      ↓
PostgreSQL
```

---

## 5.5. Alembic

- [x] Init Alembic
- [x] Kết nối metadata
- [ ] Migration tạo users
- [ ] Migration tạo movies
- [ ] Migration tạo showtimes
- [ ] Migration tạo seats
- [ ] Migration tạo bookings
- [ ] Migration tạo booking_seats
- [ ] Kiểm tra upgrade
- [ ] Kiểm tra downgrade cơ bản

---

## 5.6. Docker

### Dockerfile

- [ ] Build được FastAPI image
- [ ] Cài dependencies
- [ ] Chạy app đúng command
- [ ] Expose đúng port

### Docker Compose

Tối thiểu:

```text
docker-compose
├── api
└── postgres
```

- [ ] API container chạy được
- [ ] PostgreSQL container chạy được
- [ ] API kết nối được DB
- [ ] Environment variables đúng
- [ ] Volume cho PostgreSQL nếu cần
- [ ] Healthcheck nếu nhóm có thời gian

---

## 5.7. Load Testing

Dùng Locust.

Test tối thiểu:

- [ ] `GET /movies`
- [ ] `GET /showtimes`
- [ ] `GET /showtimes/{id}/seats`
- [ ] `POST /bookings`

Thu thập:

- [ ] Requests per second
- [ ] Average latency
- [ ] P95 latency
- [ ] P99 latency
- [ ] Error rate
- [ ] Concurrent users

Kịch bản gợi ý:

- [ ] 10 users
- [ ] 50 users
- [ ] 100 users
- [ ] 200 users nếu môi trường cho phép

---

## 5.8. Deliverable của Thành viên 3

- [ ] Database chạy ổn định
- [ ] SQLAlchemy models đầy đủ
- [ ] Repository implementations đầy đủ
- [ ] Alembic migrations hoạt động
- [ ] Docker image build được
- [ ] Docker Compose chạy được toàn hệ thống
- [ ] Load test script chạy được
- [ ] Có baseline benchmark
- [ ] Có dữ liệu benchmark phục vụ Pha 2

---

# 6. Nhiệm vụ chung của cả 3 thành viên

Các phần sau không giao hoàn toàn cho một người.

## 6.1. Trước khi code

- [ ] Thống nhất scope
- [ ] Thống nhất domain
- [ ] Thống nhất use cases
- [ ] Thống nhất API contract
- [ ] Thống nhất database schema
- [ ] Thống nhất repository interfaces
- [ ] Thống nhất architecture
- [ ] Thống nhất Git workflow
- [ ] Thống nhất coding convention
- [ ] Thống nhất naming convention

---

## 6.2. Architecture

Cả nhóm phải hiểu và thống nhất:

```text
API
 ↓
Application / Business
 ↓
Domain / Repository Interface

Infrastructure
 ↓
Repository Implementation
 ↓
Database
```

Checklist:

- [ ] Controller không chứa business logic
- [ ] Service không chứa HTTP logic
- [ ] Service không import FastAPI
- [ ] Service không import SQLAlchemy
- [ ] Repository implementation nằm ở infrastructure
- [ ] SQLAlchemy model không chạy xuyên toàn bộ project
- [ ] Dependency direction đúng

### Configuration decision

Config được quản lý theo một chiều duy nhất:

```text
.env / environment variables
          ↓
app/core/config.py (Pydantic Settings)
          ↓
app/infrastructure/database/session.py
          ↓
SQLAlchemy engine / session factory
```

Quy tắc:

- `app/core/config.py` là nguồn đọc environment variables duy nhất.
- Infrastructure và API nhận config thông qua `get_settings()`; không tự gọi `os.getenv()` rải rác.
- Không có `app/infrastructure/database/config.py` vì sẽ lặp trách nhiệm và `DATABASE_URL`.
- Secret thật chỉ nằm trong environment hoặc `.env` cục bộ; repository chỉ commit `.env.example`.
- Docker Compose phải override `DATABASE_URL` với hostname của database service.

---

## 6.3. Integration

Cả nhóm cùng thực hiện:

- [ ] API gọi đúng service
- [ ] Service gọi đúng repository interface
- [ ] Repository implementation kết nối DB
- [ ] Authentication hoạt động với protected endpoint
- [ ] Exception được map đúng sang HTTP response
- [ ] Docker chạy toàn hệ thống
- [ ] Swagger test được API
- [ ] Integration tests pass

---

## 6.4. Code Review

Quy tắc:

- [ ] Không tự merge PR của chính mình nếu có thể
- [ ] Ít nhất 1 thành viên khác review
- [ ] Review architecture, không chỉ syntax
- [ ] Review naming
- [ ] Review test
- [ ] Review dependency
- [ ] Review error handling

Gợi ý vòng review:

```text
Member 1 → Member 2 review
Member 2 → Member 3 review
Member 3 → Member 1 review
```

---

# 7. Git Workflow

## Branch chính

```text
main
  ↑
develop
  ↑
feature/*
```

### Quy tắc

- [ ] Không code trực tiếp trên `main`
- [ ] Hạn chế code trực tiếp trên `develop`
- [ ] Mỗi task tạo branch riêng
- [ ] Branch tạo từ `develop` mới nhất
- [ ] Hoàn thành thì tạo Pull Request vào `develop`
- [ ] Review trước khi merge
- [ ] Merge xong thì xóa feature branch
- [ ] Chỉ merge `develop → main` khi đạt milestone ổn định
- [ ] Không tạo branch dài hạn theo tên thành viên
- [ ] Mỗi branch gắn với một GitHub Issue
- [ ] Dùng Squash and merge để giữ lịch sử dễ đọc
- [ ] Không force-push hoặc xóa `main`/`develop`

---

## Branch naming

```text
feature/12-auth
feature/18-movie-api
feature/21-showtime-api
feature/27-booking-service
feature/31-database-models
feature/34-repository-adapters
feature/38-docker
feature/42-load-test

fix/46-duplicate-booking
fix/49-jwt-expiration

test/52-booking-service
test/55-api-integration

docs/58-architecture
docs/61-readme

perf/70-redis-cache
perf/73-database-index
```

Format chung: `<type>/<issue-number>-<short-description>`.

---

## Commit convention

Dùng Conventional Commits đơn giản:

```text
feat:
fix:
test:
docs:
refactor:
perf:
chore:
```

Ví dụ:

```text
feat: add JWT authentication
feat: implement booking service
feat: add booking repository
test: add booking service unit tests
fix: prevent unauthorized booking access
docs: add architecture diagram
perf: add database index for showtime query
chore: add docker compose configuration
```

Commit hiện tại dùng imperative, ngắn gọn, không đưa nguyên câu lệnh `git commit` vào message. Một commit chỉ nên chứa một thay đổi logic có thể review.

## GitHub Issues, Project và Pull Requests

- GitHub Project dùng các cột: `Backlog → Todo → In Progress → Review → Done`.
- Mỗi Issue có assignee, acceptance criteria, area label và milestone.
- Labels tối thiểu: `area:api`, `area:domain`, `area:infrastructure`, `type:feature`, `type:bug`, `type:test`, `type:docs`, `phase:1`, `phase:2`.
- Pull Request phải link Issue bằng `Closes #<number>` khi phù hợp.
- Pull Request vào `develop` cần ít nhất 1 approval, CI pass và mọi conversation được resolve.
- Pull Request `develop → main` chỉ tạo khi hoàn thành milestone và đã chạy lại integration test/Docker.
- `main` và `develop` phải bật ruleset chặn direct push, force push và branch deletion.

---

# 8. Cấu trúc thư mục mục tiêu

```text
cinema-booking-system/
├── .github/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies/
│   ├── application/
│   │   └── services/
│   ├── domain/
│   │   ├── entities/
│   │   ├── repositories/
│   │   └── exceptions/
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   └── repositories/
│   ├── schemas/
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── load_tests/
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── benchmark.md
│   └── phase2.md
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitattributes
├── .gitignore
└── README.md
```

---

# 9. Pha 1 — Definition of Done

Pha 1 chỉ được xem là hoàn thành khi:

## API

- [ ] Có REST API sử dụng JSON
- [ ] Có GET
- [ ] Có POST
- [ ] Có DELETE
- [ ] Có OpenAPI / Swagger

## Architecture

- [ ] Có API layer
- [ ] Có Business/Application layer
- [ ] Có Repository/Data Access layer
- [ ] Business layer không import web framework
- [ ] Business layer không import DB library

## Database

- [ ] PostgreSQL hoạt động
- [ ] ORM hoạt động
- [ ] Repository hoạt động
- [ ] Migration hoạt động

## Security

- [ ] Có register
- [ ] Có login
- [ ] Có password hashing
- [ ] Có JWT
- [ ] Có protected GET
- [ ] Có protected POST
- [ ] Authentication không lặp trong từng endpoint

## Deployment

- [ ] Có Dockerfile
- [ ] Có Docker Compose
- [ ] Có thể chạy project bằng Docker

## Testing

- [ ] Unit test business logic
- [ ] Integration test API cơ bản
- [ ] Load test chạy được

## Documentation

- [ ] GitHub public
- [ ] README đầy đủ
- [ ] Architecture diagram
- [ ] API description
- [ ] Hướng dẫn chạy
- [ ] Database description

---

# 10. Pha 2 — Nhiệm vụ chung

Pha 2 không bắt đầu bằng việc chọn công nghệ.

Flow phải là:

```text
Benchmark Pha 1
      ↓
Phát hiện vấn đề
      ↓
Xác định Quality Attribute
      ↓
Đề xuất Architecture Decision
      ↓
Implement
      ↓
Benchmark lại
      ↓
So sánh Before / After
      ↓
Phân tích Trade-off
```

---

# 11. Pha 2 — Experiment 1: Performance

## Baseline

- [ ] Benchmark `GET /movies`
- [ ] Benchmark `GET /showtimes`
- [ ] Benchmark `GET /showtimes/{id}/seats`
- [ ] Ghi RPS
- [ ] Ghi Avg latency
- [ ] Ghi P95
- [ ] Ghi P99
- [ ] Ghi error rate

## Phân tích

- [ ] Kiểm tra query DB
- [ ] Kiểm tra read-heavy endpoint
- [ ] Kiểm tra query lặp
- [ ] Kiểm tra index

## Giải pháp có thể nghiên cứu

Chỉ triển khai nếu có số liệu chứng minh nhu cầu.

- [ ] Database index
- [ ] Query optimization
- [ ] Redis cache
- [ ] Cache-aside pattern
- [ ] TTL
- [ ] Cache invalidation

## Sau cải tiến

- [ ] Benchmark lại cùng hardware
- [ ] Cùng workload
- [ ] Cùng dataset
- [ ] Cùng concurrency level
- [ ] So sánh Before / After
- [ ] Giải thích nguyên nhân cải thiện
- [ ] Ghi trade-off

---

# 12. Pha 2 — Experiment 2: Concurrent Booking

## Problem

Kiểm tra trường hợp nhiều user đặt cùng một ghế cùng lúc.

Ví dụ:

```text
100 concurrent requests
        ↓
same showtime
        ↓
same seat
```

## Baseline test

- [ ] Tạo kịch bản concurrent booking
- [ ] Kiểm tra có double booking hay không
- [ ] Ghi lại failure behavior
- [ ] Ghi lại consistency issue

## Kiến thức cần nghiên cứu

- [ ] Race condition
- [ ] Database transaction
- [ ] ACID
- [ ] Isolation
- [ ] Unique constraint
- [ ] Optimistic locking
- [ ] Pessimistic locking

## Cải tiến

Nhóm chọn giải pháp phù hợp sau khi phân tích.

Có thể:

- [ ] Unique constraint
- [ ] Database transaction
- [ ] Row-level locking
- [ ] Optimistic concurrency control

## Kết quả kỳ vọng

Ví dụ:

```text
100 concurrent requests
1 success
99 conflict/failure hợp lệ
0 duplicate booking
```

## Đánh giá

- [ ] Correctness trước/sau
- [ ] Latency trước/sau
- [ ] Throughput trước/sau
- [ ] Trade-off của locking/transaction

---

# 13. Phân công Pha 2

## Thành viên 1

Primary owner:

- [ ] Chuẩn bị API workload
- [ ] Chạy load test
- [ ] Thu metrics
- [ ] Tổng hợp kết quả benchmark
- [ ] Kiểm tra HTTP behavior sau cải tiến

## Thành viên 2

Primary owner:

- [ ] Phân tích quality attribute
- [ ] Xác định vấn đề
- [ ] Đề xuất architecture decision
- [ ] Phân tích trade-off
- [ ] Viết phần giải thích kiến trúc
- [ ] Kiểm tra business correctness

## Thành viên 3

Primary owner:

- [ ] Implement infrastructure optimization
- [ ] Implement index/cache nếu được chọn
- [ ] Implement transaction/locking nếu được chọn
- [ ] Cấu hình Redis nếu được chọn
- [ ] Hỗ trợ benchmark trên Kaggle
- [ ] Thu DB-level metrics nếu có thể

Cả 3 cùng:

- [ ] Review kết quả
- [ ] So sánh before/after
- [ ] Viết kết luận
- [ ] Chuẩn bị demo
- [ ] Chuẩn bị phần bảo vệ kiến trúc

---

# 14. README Checklist

README cuối cùng nên có:

- [ ] Project Overview
- [ ] Problem Description
- [ ] Functional Requirements
- [ ] Architecture
- [ ] Architecture Diagram
- [ ] Project Structure
- [ ] Domain Model
- [ ] Database Schema
- [ ] API Endpoints
- [ ] Authentication
- [ ] Installation
- [ ] Environment Variables
- [ ] How to Run
- [ ] Docker
- [ ] Testing
- [ ] Load Testing
- [ ] Phase 1 Benchmark
- [ ] Phase 2 Problem Analysis
- [ ] Architecture Improvements
- [ ] Before vs After
- [ ] Trade-offs
- [ ] Team Contributions

---

# 15. Documentation cần chuẩn bị

Trong `docs/`:

```text
docs/
├── architecture.md
├── database.md
├── benchmark.md
└── phase2.md
```

## `architecture.md`

- [ ] Layer diagram
- [ ] Dependency direction
- [ ] Trách nhiệm từng layer
- [ ] Architecture decisions

## `database.md`

- [ ] ERD
- [ ] Tables
- [ ] Relationships
- [ ] Constraints
- [ ] Indexes

## `benchmark.md`

- [ ] Hardware
- [ ] Dataset
- [ ] Workload
- [ ] Concurrent users
- [ ] RPS
- [ ] Average latency
- [ ] P95
- [ ] P99
- [ ] Error rate

## `phase2.md`

- [ ] Problem
- [ ] Quality attribute
- [ ] Root cause
- [ ] Architecture decision
- [ ] Implementation
- [ ] Before
- [ ] After
- [ ] Trade-off
- [ ] Conclusion

---

# 16. Milestones

## Milestone 0 — Project Setup

- [x] Repository tạo xong
- [x] `main`
- [x] `develop`
- [x] Folder/package structure
- [x] `requirements.txt`
- [x] README skeleton
- [ ] FastAPI hello endpoint

---

## Milestone 1 — Core Architecture

- [ ] Domain entities
- [ ] Repository interfaces
- [ ] Database setup
- [ ] SQLAlchemy models
- [ ] Repository implementations
- [ ] Service layer

---

## Milestone 2 — API + Auth

- [ ] Register
- [ ] Login
- [ ] JWT
- [ ] Movie API
- [ ] Showtime API
- [ ] Booking API
- [ ] Protected GET
- [ ] Protected POST
- [ ] Swagger

---

## Milestone 3 — Testing + Docker

- [ ] Unit tests
- [ ] Integration tests
- [ ] Dockerfile
- [ ] Docker Compose
- [ ] Migration
- [ ] Seed data

---

## Milestone 4 — Phase 1 Benchmark

- [ ] Locust scripts
- [ ] Kaggle CPU environment
- [ ] Baseline results
- [ ] Benchmark documentation
- [ ] Tag `v1.0-phase1`

---

## Milestone 5 — Phase 2

- [ ] Chọn quality attribute
- [ ] Xác định bottleneck/problem
- [ ] Đề xuất cải tiến
- [ ] Implement cải tiến
- [ ] Benchmark lại
- [ ] Before vs After
- [ ] Trade-off analysis

---

## Milestone 6 — Final

- [ ] Full test
- [ ] README hoàn chỉnh
- [ ] Architecture docs hoàn chỉnh
- [ ] Benchmark docs hoàn chỉnh
- [ ] Git history sạch
- [ ] Docker chạy lại từ đầu thành công
- [ ] Demo script
- [ ] Final presentation/demo
- [ ] Tag final release

---

# 17. Quy tắc quan trọng của nhóm

1. Không over-engineer Pha 1.
2. Không thêm Redis/Kafka/Microservices chỉ để “trông xịn”.
3. Mỗi công nghệ mới phải giải quyết một vấn đề cụ thể.
4. Business layer phải độc lập FastAPI và SQLAlchemy.
5. Không đặt business logic trong router/controller.
6. Không query DB trực tiếp từ router.
7. Mỗi feature nên có test nếu hợp lý.
8. Mỗi PR phải được review.
9. Benchmark Pha 1 phải được lưu để làm baseline.
10. Pha 2 phải có số liệu Before vs After trên cùng cấu hình phần cứng.
11. Không đọc environment variables rải rác ngoài `app/core/config.py`.
12. Mọi architecture decision phải giải thích được:
    - Vấn đề là gì?
    - Vì sao chọn giải pháp này?
    - Nó cải thiện quality attribute nào?
    - Trade-off là gì?
    - Số liệu có chứng minh hiệu quả không?

---

# 18. Kết quả cuối cùng mong muốn

Nhóm phải có thể trình bày được câu chuyện:

```text
Chúng tôi xây dựng Cinema Booking System
        ↓
sử dụng Layered Architecture
        ↓
API → Business → Repository → PostgreSQL
        ↓
Business layer độc lập framework/database
        ↓
hệ thống có Authentication + Docker
        ↓
chúng tôi benchmark Pha 1
        ↓
phát hiện vấn đề chất lượng
        ↓
đưa ra Architecture Decision
        ↓
implement cải tiến
        ↓
benchmark lại cùng hardware
        ↓
chứng minh Before vs After
        ↓
phân tích trade-off
```

Đây là mục tiêu chính của toàn bộ bài tập lớn.
