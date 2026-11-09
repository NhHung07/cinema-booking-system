# Kiến trúc hệ thống (System Architecture)

Tài liệu này trình bày chi tiết về kiến trúc hệ thống của dự án **Cinema Booking System**, các nguyên lý thiết kế phần mềm cốt lõi được áp dụng, bảng giải thích chi tiết toàn bộ các tệp tin trong từng tầng, và luồng vận hành đầu-cuối (end-to-end flow) của các ca sử dụng chính.

---

## 1. Tổng quan mô hình kiến trúc

Hệ thống được xây dựng theo phong cách **Clean Architecture (Onion / Hexagonal Architecture)** kết hợp với phương pháp thiết kế **Domain-Driven Design (DDD)**.

### Sơ đồ phân tầng kiến trúc tổng thể

```text
+-----------------------------------------------------------------------------------+
|                        PRESENTATION / API LAYER (FastAPI)                         |
|   - HTTP Routes (/auth, /movies, /showtimes, /bookings, /admin/analytics)         |
|   - Request Validation (Pydantic Schemas)                                         |
|   - Composition Root & Dependency Injection (dependencies.py)                     |
|   - Global Exception Mapping (Domain Exceptions -> HTTP Status Codes)             |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | calls (gọi nghiệp vụ)
                                          v
+-----------------------------------------------------------------------------------+
|                            APPLICATION LAYER (Use Cases)                          |
|   - Use Case Services: BookingService, CatalogService, AuthService,               |
|     AnalyticsService                                                              |
|   - Ports: CatalogCache Protocol                                                  |
|   - Data Transfer Objects (DTOs / Application Schemas)                            |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | uses (sử dụng)
                                          v
+-----------------------------------------------------------------------------------+
|                        DOMAIN LAYER (Core Business Logic)                         |
|   - Domain Entities (Dataclasses: Booking, Movie, Showtime, Seat, User)           |
|   - Repository Interfaces (Abstract Base Classes)                                 |
|   - UnitOfWork Interface (Transaction Boundary)                                   |
|   * QUY TẮC: Độc lập 100%, chỉ sử dụng Python Standard Library                    |
+-----------------------------------------+-----------------------------------------+
                                          ^
                                          | implements (Dependency Inversion)
                                          |
+-----------------------------------------+-----------------------------------------+
|                        INFRASTRUCTURE LAYER (Adapters)                            |
|   - SQLAlchemy 2.0 ORM Models & Session Management (Connection Pooling)           |
|   - Repository Implementations (SQLAlchemyBookingRepository, etc.)                |
|   - Transaction Controller (SQLAlchemyUnitOfWork) & Data Mappers                  |
|   - Redis Catalog Cache (RedisCatalogCache) & Prometheus Observability            |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | persists to / caches in
                                          v
+-----------------------------------------------------------------------------------+
|                       POSTGRESQL DATABASE 16 & REDIS CACHE                        |
|   - Tables, Primary/Foreign Keys, Indexes                                         |
|   - Ràng buộc toàn vẹn cứng: UNIQUE(showtime_id, seat_id)                         |
+-----------------------------------------------------------------------------------+
```

### Bảng tóm tắt các tầng (Layers)

| Layer | Chứa gì? | Vì sao cần? | Dependency được phép |
| :--- | :--- | :--- | :--- |
| `app/api` | Routes, FastAPI dependencies, chuyển đổi HTTP error | Giữ HTTP concern và Swagger annotation ở boundary | `application`, `domain`, `infrastructure` tại composition layer |
| `app/application` | `AuthService`, `CatalogService`, `BookingService`, `AnalyticsService`, ports, Pydantic schemas | Điều phối từng use case | `domain` và `core` |
| `app/domain` | Dataclass entity và abstract repository/unit-of-work interface | Diễn tả business concept không phụ thuộc framework | Chỉ Python standard library |
| `app/infrastructure` | ORM model, session factory, SQLAlchemy repository, Redis cache, Prometheus metrics | Adapter từ interface sang PostgreSQL / Redis | `domain`, `application/ports`, `core`, SQLAlchemy, Redis |
| `app/core` | Settings, password/JWT helper, application error | Chính sách kỹ thuật dùng chung | Package library; không phụ thuộc FastAPI/SQLAlchemy |

---

## 2. Các nguyên lý kiến trúc cốt lõi và cách áp dụng

### 2.1. Dependency Inversion Principle (DIP - Chữ D trong SOLID)
* **Định nghĩa:** Các module cấp cao (Domain, Application) không phụ thuộc vào các module cấp thấp (Database, Framework). Cả hai phụ thuộc vào các giao diện trừu tượng (Abstractions / Interfaces).
* **Cách áp dụng trong dự án:**
  1. Tầng **Domain** định nghĩa hợp đồng `UnitOfWork` và các `Repository` dưới dạng lớp trừu tượng (`abc.ABC`).
  2. Tầng **Application** (`BookingService`, `CatalogService`) chỉ nhận tham số kiểu `UnitOfWork` (và `CatalogCache` protocol) vào constructor.
  3. Tầng **Infrastructure** triển khai chi tiết bằng SQLAlchemy (`SQLAlchemyUnitOfWork`) và Redis (`RedisCatalogCache`), phụ thuộc ngược lại vào interface.
* **Lợi ích:** Có thể viết Unit Test kiểm thử 100% logic của `BookingService` bằng `FakeUnitOfWork` lưu trong RAM mà không cần bật cơ sở dữ liệu PostgreSQL.

### 2.2. Separation of Concerns (SoC) & Single Responsibility Principle (SRP)
* **API Layer (`app/api`):** Chỉ giải quyết bài toán giao thức HTTP (Path, Query params, Request body, HTTP Header, Status codes).
* **Application Layer (`app/application`):** Chỉ điều phối kịch bản sử dụng (Use case), không quan tâm request đến từ Web hay CLI.
* **Domain Layer (`app/domain`):** Chỉ chứa mô hình nghiệp vụ và quy tắc của thực thể.
* **Infrastructure Layer (`app/infrastructure`):** Đảm nhận đọc/ghi PostgreSQL, caching Redis và thu thập metrics Prometheus.

### 2.3. Repository Pattern & Unit of Work (UoW) Pattern
* **Repository Pattern:** Tách biệt tầng logic nghiệp vụ khỏi tầng truy xuất dữ liệu (`get_by_id`, `add`, `list`, `update`, `delete`).
* **Unit of Work Pattern:** Đảm bảo ranh giới giao dịch (Transaction Boundary) an toàn theo chuẩn ACID. Khi một ca đặt vé cần ghi nhiều dòng dữ liệu (tạo bản ghi `Booking` và chèn nhiều bản ghi `BookingSeat`), toàn bộ quá trình nằm trong một transaction duy nhất. Nếu bất kỳ ghế nào bị trùng, toàn bộ thao tác được tự động `rollback()`.

### 2.4. Phòng thủ chiều sâu (Defense-in-Depth) chống Race Condition / Double-Booking
* **Lớp 1 (Validation tại Application Service):** Kiểm tra danh sách ghế không trùng lặp, suất chiếu tồn tại và chưa bắt đầu, ghế thuộc đúng phòng chiếu.
* **Lớp 2 (Pessimistic Constraint tại Database):** Ràng buộc duy nhất `UNIQUE(showtime_id, seat_id)` trên bảng `booking_seats`. Nếu 2 request cùng cố đặt 1 ghế đồng thời, PostgreSQL chỉ chấp nhận một writer, request còn lại bị rollback và chuyển thành `SeatAlreadyBookedError` $\to$ API trả về HTTP `409 Conflict`.

---

## 3. Cấu trúc chi tiết từng tầng và giải thích từng file

```text
app/
├── core/                           # Tầng chính sách & tiện ích dùng chung
│   ├── config.py                   # Cấu hình hệ thống (Pydantic Settings, DB pool, Redis, Metrics)
│   ├── exceptions.py               # Cây phả hệ ngoại lệ nghiệp vụ toàn hệ thống
│   └── security.py                 # Hàm băm Argon2 và mã hóa/giải mã JWT token
│
├── domain/                         # TẦNG DOMAIN (Nghiệp vụ cốt lõi)
│   ├── entities/                   # Thực thể nghiệp vụ (Python Dataclasses thuần túy)
│   │   ├── user.py                 # Thực thể User (id, email, full_name, role)
│   │   ├── movie.py                # Thực thể Movie
│   │   ├── showtime.py             # Thực thể Showtime
│   │   ├── seat.py                 # Thực thể Seat
│   │   └── booking.py              # Thực thể Booking & BookingStatus Enum
│   └── repositories/               # Hợp đồng giao tiếp (Interfaces / Abstract Base Classes)
│       ├── user_repository.py      # Interface thao tác dữ liệu người dùng
│       ├── movie_repository.py     # Interface tra cứu và quản lý phim
│       ├── showtime_repository.py  # Interface tra cứu và quản lý suất chiếu
│       ├── seat_repository.py      # Interface tra cứu ghế
│       ├── booking_repository.py   # Interface ghi/đọc vé và gán ghế
│       └── unit_of_work.py         # Interface quản lý transaction (commit/rollback)
│
├── application/                    # TẦNG APPLICATION (Ca sử dụng)
│   ├── ports/
│   │   └── catalog_cache.py        # Protocol định nghĩa giao diện bộ nhớ đệm danh mục
│   ├── schemas/                    # Pydantic DTO (Data Transfer Objects) vào/ra
│   │   ├── analytics.py            # DTO Thống kê doanh thu, tỷ lệ lấp đầy, top phim
│   │   ├── auth.py                 # DTO Đăng ký, Đăng nhập, Token, User profile
│   │   ├── catalog.py              # DTO Phim, Suất chiếu, Upload ảnh, Trạng thái ghế
│   │   └── booking.py              # DTO Tạo vé, Thông tin phản hồi vé đặt
│   └── services/                   # Các Use Case Services
│       ├── analytics_service.py    # Nghiệp vụ phân tích số liệu thống kê cho Admin Dashboard
│       ├── auth_service.py         # Nghiệp vụ đăng ký, kiểm tra mật khẩu, sinh JWT
│       ├── catalog_service.py      # Nghiệp vụ quản lý phim, lịch chiếu, sơ đồ ghế (kèm Cache)
│       └── booking_service.py      # Nghiệp vụ tạo vé, kiểm tra hợp lệ, hủy vé
│
├── infrastructure/                 # TẦNG INFRASTRUCTURE (Hạ tầng kỹ thuật)
│   ├── cache/
│   │   └── catalog_cache.py        # RedisCatalogCache (fallback an toàn khi lỗi kết nối)
│   ├── database/                   # Kết nối cơ sở dữ liệu & SQLAlchemy ORM
│   │   ├── base.py                 # Khởi tạo DeclarativeBase của SQLAlchemy
│   │   ├── session.py              # Engine factory, cấu hình connection pool & sessionmaker
│   │   └── models/                 # Bảng ánh xạ SQLAlchemy (ORM Models)
│   ├── observability.py            # Prometheus metrics middleware & SQLAlchemy event hooks
│   └── repositories/               # Triển khai cụ thể các Repository của Domain
│       ├── mappers.py              # Ánh xạ qua lại giữa SQLAlchemy Model và Domain Entity
│       ├── sqlalchemy_user_repository.py
│       ├── sqlalchemy_movie_repository.py
│       ├── sqlalchemy_showtime_repository.py
│       ├── sqlalchemy_seat_repository.py
│       ├── sqlalchemy_booking_repository.py
│       └── sqlalchemy_unit_of_work.py
│
├── api/                            # TẦNG PRESENTATION (API Delivery)
│   ├── dependencies.py             # Composition Root: Dependency Injection (DI) của FastAPI
│   └── routes/                     # Các bộ điều hướng HTTP (FastAPI Routers)
│       ├── analytics.py            # GET /admin/analytics/overview
│       ├── auth.py                 # POST /auth/register, POST /auth/login, GET /auth/me
│       ├── movies.py               # CRUD /movies & POST /movies/upload-image
│       ├── showtimes.py            # CRUD /showtimes & GET /showtimes/{id}/seats
│       └── bookings.py             # POST /bookings, GET /me, GET /{id}, DELETE /{id}
│
└── main.py                         # Điểm khởi động ứng dụng FastAPI, Lifespan & Exception Handlers
```

---

## 4. Luồng hoạt động đầu-cuối (End-to-End Flows)

### 4.1. Luồng Đặt vé xem phim (`POST /bookings`)

```text
POST /bookings + Bearer JWT
  → get_current_user dependency decode JWT và kiểm tra quyền (chặn tài khoản Admin đặt vé)
  → route parse BookingCreateRequest
  → BookingService.create_booking:
      - Kiểm tra danh sách seat_ids không rỗng và không trùng lặp
      - Kiểm tra showtime tồn tại và chưa bắt đầu (start_time > now)
      - Kiểm tra toàn bộ ghế tồn tại và thuộc đúng phòng chiếu của showtime
  → SQLAlchemyUnitOfWork insert Booking + BookingSeat trong một transaction
  → PostgreSQL UNIQUE(showtime_id, seat_id) chỉ chấp nhận một writer
  → Nếu trùng ghế: rollback transaction, raise SeatAlreadyBookedError → HTTP 409 Conflict
  → Nếu thành công: commit transaction → trả về HTTP 201 Created
```

### 4.2. Chính sách hủy vé (`DELETE /bookings/{id}`)

Khi người dùng hủy vé, hệ thống kiểm tra quyền sở hữu (`booking.user_id == user_id`), giữ lại dòng `bookings` với trạng thái `CANCELLED` để lưu lịch sử, đồng thời xóa các dòng `booking_seats` tương ứng trong cùng một transaction. Việc xóa các dòng giữ ghế giúp giải phóng ghế ngay lập tức cho người dùng khác đặt lại.

### 4.3. Luồng Đăng nhập & Xác thực bảo mật (`POST /auth/login`)

```text
Client gửi POST /auth/login { email, password }
  → AuthService tìm user theo email qua UserRepository
  → Xác minh mật khẩu bằng Argon2 (verify_password)
  → Sinh JWT chứa payload { sub: user_id, exp: ... }
  → Client đính kèm Authorization: Bearer <token> ở các request tiếp theo
```

---

> Trở về trang chính: [README.md](../README.md) | Xem mục lục tài liệu: [docs/README.md](./README.md)
