# Tài liệu kiến trúc chuyên sâu (Architecture Deep Dive)

Tài liệu này trình bày chi tiết về kiến trúc hệ thống của dự án **Cinema Booking System**, các nguyên lý thiết kế phần mềm cốt lõi được áp dụng, bảng giải thích chi tiết toàn bộ các tệp tin trong từng tầng, và luồng vận hành đầu-cuối (end-to-end flow) của các ca sử dụng chính.

---

## 1. Tổng quan mô hình kiến trúc

Hệ thống được xây dựng theo phong cách **Clean Architecture (Onion / Hexagonal Architecture)** kết hợp với phương pháp thiết kế **Domain-Driven Design (DDD)**.

### Sơ đồ phân tầng kiến trúc tổng thể

```text
+-----------------------------------------------------------------------------------+
|                        PRESENTATION / API LAYER (FastAPI)                         |
|   - HTTP Routes (/auth, /movies, /showtimes, /bookings)                           |
|   - Request Validation (Pydantic Schemas)                                         |
|   - Composition Root & Dependency Injection (dependencies.py)                     |
|   - Global Exception Mapping (Domain Exceptions -> HTTP Status Codes)             |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | calls (gọi nghiệp vụ)
                                          v
+-----------------------------------------------------------------------------------+
|                            APPLICATION LAYER (Use Cases)                          |
|   - Use Case Services: BookingService, CatalogService, AuthService                |
|   - Data Transfer Objects (DTOs / Application Schemas)                            |
|   - Điều phối nghiệp vụ, kiểm tra ràng buộc logic                                 |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | uses (sử dụng)
                                          v
+-----------------------------------------------------------------------------------+
|                        DOMAIN LAYER (Core Business Logic)                         |
|   - Domain Entities (Dataclasses: Booking, Movie, Showtime, Seat, User)          |
|   - Repository Interfaces (Abstract Base Classes)                                 |
|   - UnitOfWork Interface (Transaction Boundary)                                   |
|   * QUY TẮC: Độc lập 100%, chỉ sử dụng Python Standard Library                    |
+-----------------------------------------+-----------------------------------------+
                                          ^
                                          | implements (Dependency Inversion)
                                          |
+-----------------------------------------+-----------------------------------------+
|                        INFRASTRUCTURE LAYER (Adapters)                            |
|   - SQLAlchemy 2.0 ORM Models & Session Management                                |
|   - Repository Implementations (SqlAlchemyBookingRepository, etc.)                |
|   - Transaction Controller (SqlAlchemyUnitOfWork)                                 |
|   - Data Mappers (Chuyển đổi ORM Model <-> Domain Entity)                         |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | persists to
                                          v
+-----------------------------------------------------------------------------------+
|                          POSTGRESQL DATABASE 16                                   |
|   - Tables, Primary/Foreign Keys, Indexes                                         |
|   - Ràng buộc toàn vẹn cứng: UNIQUE(showtime_id, seat_id)                         |
+-----------------------------------------------------------------------------------+
```

### Nguyên tắc bất biến: The Dependency Rule (Quy tắc phụ thuộc)
* **Chiều phụ thuộc luôn hướng vào tâm (từ ngoài vào trong):** Các tầng bên ngoài phụ thuộc vào các tầng bên trong. Tầng `domain` nằm ở trung tâm và không được phép biết đến sự tồn tại của bất kỳ tầng nào khác.
* **Không phụ thuộc vào Framework:** Tầng `domain` và `application` không import FastAPI, SQLAlchemy hay bất kỳ thư viện web/cơ sở dữ liệu cụ thể nào.

---

## 2. Các nguyên lý kiến trúc cốt lõi và cách áp dụng

### 2.1. Dependency Inversion Principle (DIP - Chữ D trong SOLID)
* **Định nghĩa:** Các module cấp cao (High-level modules như Domain, Application) không được phụ thuộc vào các module cấp thấp (Low-level modules như Database, Framework). Cả hai phải phụ thuộc vào các giao diện trừu tượng (Abstractions / Interfaces).
* **Cách áp dụng trong dự án:**
  1. Tầng **Domain** định nghĩa hợp đồng `UnitOfWork` và các `Repository` dưới dạng lớp trừu tượng (`abc.ABC`):
     ```python
     # app/domain/repositories/unit_of_work.py
     class UnitOfWork(ABC):
         bookings: BookingRepository
         showtimes: ShowtimeRepository
         seats: SeatRepository
         @abstractmethod
         def commit(self) -> None: ...
         @abstractmethod
         def rollback(self) -> None: ...
     ```
  2. Tầng **Application** (`BookingService`) chỉ nhận tham số kiểu `UnitOfWork` interface vào constructor:
     ```python
     class BookingService:
         def __init__(self, unit_of_work: UnitOfWork) -> None:
             self._unit_of_work = unit_of_work
     ```
  3. Tầng **Infrastructure** triển khai chi tiết bằng SQLAlchemy (`SQLAlchemyUnitOfWork`), phụ thuộc ngược lại vào interface của Domain.
* **Lợi ích:** Có thể viết Unit Test kiểm thử 100% logic của `BookingService` bằng `FakeUnitOfWork` lưu trong bộ nhớ RAM mà không cần bật cơ sở dữ liệu PostgreSQL.

### 2.2. Separation of Concerns (SoC) & Single Responsibility Principle (SRP)
* Mỗi module, layer và file chỉ đảm nhận một trách nhiệm duy nhất:
  * **API Layer (`app/api`):** Chỉ giải quyết bài toán giao thức HTTP (Path, Query params, Request body, HTTP Header, Status codes).
  * **Application Layer (`app/application`):** Chỉ điều phối kịch bản sử dụng (Use case), không quan tâm request đến từ Web hay CLI.
  * **Domain Layer (`app/domain`):** Chỉ chứa mô hình nghiệp vụ và quy tắc sống của thực thể.
  * **Infrastructure Layer (`app/infrastructure`):** Chỉ quan tâm cách đọc/ghi dữ liệu vào PostgreSQL bằng SQLAlchemy.

### 2.3. Skinny Controller / Fat Service (Controller mỏng, Service giàu nghiệp vụ)
* Các hàm route trong `app/api/routes/*.py` chỉ dài từ 3 đến 5 dòng code. Chúng không thực hiện tính toán hay kiểm tra nghiệp vụ phức tạp mà chỉ:
  1. Nhận request đã được parse và validate bởi Pydantic.
  2. Lấy thông tin user đã xác thực qua `CurrentUser`.
  3. Gọi method tương ứng của Service.
  4. Bọc kết quả trả về bằng Pydantic Response Model.

### 2.4. Repository Pattern & Unit of Work (UoW) Pattern
* **Repository Pattern:** Tách biệt tầng logic nghiệp vụ khỏi tầng truy xuất dữ liệu, giúp tầng Application tương tác với cơ sở dữ liệu như một tập hợp đối tượng trong bộ nhớ (Collection-like interface: `get_by_id`, `add`, `list`).
* **Unit of Work Pattern:** Đảm bảo ranh giới giao dịch (Transaction Boundary) an toàn theo chuẩn ACID. Khi một ca đặt vé cần ghi nhiều dòng dữ liệu (tạo bản ghi `Booking` và chèn nhiều bản ghi `BookingSeat`), toàn bộ quá trình nằm trong một transaction duy nhất. Nếu bất kỳ ghế nào bị trùng, toàn bộ thao tác được tự động `rollback`.

### 2.5. Phòng thủ chiều sâu (Defense-in-Depth) chống Race Condition / Double-Booking
* Hệ thống xử lý tranh chấp ghế thời gian thực bằng 2 lớp:
  * **Lớp 1 (Optimistic Check tại Application Service):** Kiểm tra ghế có tồn tại và thuộc phòng chiếu đó không.
  * **Lớp 2 (Pessimistic Constraint tại Database):** Ràng buộc duy nhất `UNIQUE(showtime_id, seat_id)` trên bảng `booking_seats`. Nếu 2 request cùng cố đặt 1 ghế trong cùng 1 mili-giây, PostgreSQL sẽ chặn đứng request thứ 2, trigger rollback transaction và đẩy lỗi vi phạm khóa duy nhất $\to$ Infrastructure bắt lỗi và biến thành `SeatAlreadyBookedError` $\to$ API trả về HTTP `409 Conflict`.

---

## 3. Cấu trúc chi tiết từng tầng và giải thích từng file

Dưới đây là sơ đồ tổ chức thư mục toàn diện của mã nguồn `app/`:

```text
app/
├── core/                           # Tầng chính sách & tiện ích dùng chung
│   ├── config.py                   # Cấu hình hệ thống (Pydantic Settings, biến môi trường)
│   ├── exceptions.py               # Cây phả hệ ngoại lệ nghiệp vụ toàn hệ thống
│   └── security.py                 # Hàm băm Argon2 và mã hóa/giải mã JWT token
│
├── domain/                         # TẦNG 3: DOMAIN LAYER (Nghiệp vụ cốt lõi)
│   ├── entities/                   # Thực thể nghiệp vụ (Python Dataclasses thuần túy)
│   │   ├── user.py                 # Thực thể User
│   │   ├── movie.py                # Thực thể Phim
│   │   ├── showtime.py             # Thực thể Suất chiếu
│   │   ├── seat.py                 # Thực thể Ghế ngồi
│   │   └── booking.py              # Thực thể Đơn đặt vé & Enum trạng thái
│   └── repositories/               # Hợp đồng giao tiếp (Interfaces / Abstract Base Classes)
│       ├── user_repository.py      # Interface thao tác dữ liệu người dùng
│       ├── movie_repository.py     # Interface tra cứu phim
│       ├── showtime_repository.py  # Interface tra cứu suất chiếu
│       ├── seat_repository.py      # Interface tra cứu ghế
│       ├── booking_repository.py   # Interface ghi/đọc vé và gán ghế
│       └── unit_of_work.py         # Interface quản lý transaction (commit/rollback)
│
├── application/                    # TẦNG 2: APPLICATION LAYER (Ca sử dụng)
│   ├── schemas/                    # Pydantic DTO (Data Transfer Objects) vào/ra
│   │   ├── auth.py                 # DTO Đăng ký, Đăng nhập, Token
│   │   ├── catalog.py              # DTO Phim, Suất chiếu, Trạng thái ghế
│   │   └── booking.py              # DTO Tạo vé, Thông tin phản hồi vé đặt
│   └── services/                   # Các Use Case Services
│       ├── auth_service.py         # Nghiệp vụ đăng ký, kiểm tra mật khẩu, sinh JWT
│       ├── catalog_service.py      # Nghiệp vụ xem phim, lịch chiếu, tính toán ghế trống
│       └── booking_service.py      # Nghiệp vụ tạo vé, kiểm tra hợp lệ, hủy vé
│
├── infrastructure/                 # TẦNG 4: INFRASTRUCTURE LAYER (Hạ tầng kỹ thuật)
│   ├── database/                   # Kết nối cơ sở dữ liệu & SQLAlchemy ORM
│   │   ├── base.py                 # Khởi tạo DeclarativeBase của SQLAlchemy
│   │   ├── session.py              # Engine factory, cấu hình connection pool & sessionmaker
│   │   └── models/                 # Bảng ánh xạ SQLAlchemy (ORM Models)
│   │       ├── user.py             # Model bảng users
│   │       ├── movie.py            # Model bảng movies
│   │       ├── showtime.py         # Model bảng showtimes
│   │       ├── seat.py             # Model bảng seats
│   │       └── booking.py          # Model bảng bookings & booking_seats
│   └── repositories/               # Triển khai cụ thể các Repository của Domain
│       ├── mappers.py              # Ánh xạ qua lại giữa SQLAlchemy Model và Domain Entity
│       ├── sqlalchemy_user_repository.py
│       ├── sqlalchemy_movie_repository.py
│       ├── sqlalchemy_showtime_repository.py
│       ├── sqlalchemy_seat_repository.py
│       ├── sqlalchemy_booking_repository.py
│       └── sqlalchemy_unit_of_work.py # Hiện thực UnitOfWork với session.commit/rollback
│
├── api/                            # TẦNG 1: PRESENTATION LAYER (API Delivery)
│   ├── dependencies.py             # Composition Root: Dependency Injection (DI) của FastAPI
│   └── routes/                     # Các bộ điều hướng HTTP (FastAPI Routers)
│       ├── auth.py                 # POST /auth/register, POST /auth/login
│       ├── movies.py               # GET /movies, GET /movies/{id}
│       ├── showtimes.py            # GET /showtimes, GET /showtimes/{id}/seats
│       └── bookings.py             # POST /bookings, GET /me, GET /{id}, DELETE /{id}
│
└── main.py                         # Điểm khởi động ứng dụng FastAPI & Exception Handlers
```

---

### Chi tiết các file theo từng tầng

#### A. Tầng Presentation (`app/api/` & `app/main.py`)
1. **`app/main.py`**:
   * Khởi tạo đối tượng `FastAPI`.
   * Cấu hình Middleware CORS cho phép Frontend kết nối.
   * Đăng ký bộ xử lý ngoại lệ tập trung `_register_exception_handlers`: Ánh xạ các Domain Exception từ tầng nghiệp vụ sang mã lỗi HTTP chuẩn mực (Ví dụ: `SeatAlreadyBookedError` $\to$ `409 Conflict`, `NotFoundError` $\to$ `404 Not Found`, `InvalidCredentialsError` $\to$ `401 Unauthorized`).
   * Gắn các routes vào ứng dụng (`include_router`).
2. **`app/api/dependencies.py`**:
   * **Composition Root**: Nơi lắp ráp tất cả các phụ thuộc.
   * `get_session()`: Quản lý vòng đời SQLAlchemy Session theo từng request (`yield session` và tự động `session.close()` trong khối `finally`).
   * `get_unit_of_work()`: Đưa session vào `SQLAlchemyUnitOfWork`.
   * `get_booking_service()`, `get_auth_service()`, `get_catalog_service()`: Bơm Unit of Work vào các Service.
   * `get_current_user()` & `CurrentUser`: Đọc Header `Authorization: Bearer <token>`, giải mã JWT, kiểm tra người dùng trong cơ sở dữ liệu và trả về thực thể `User`.
3. **`app/api/routes/bookings.py`**:
   * Định nghĩa các endpoints đặt vé: `POST /bookings` (đặt vé mới), `GET /bookings/me` (lịch sử vé người dùng), `GET /bookings/{id}`, `DELETE /bookings/{id}` (hủy vé).
4. **`app/api/routes/auth.py`**:
   * Định nghĩa endpoints xác thực: `POST /auth/register` (đăng ký), `POST /auth/login` (đăng nhập trả về JWT Access Token).
5. **`app/api/routes/movies.py` & `showtimes.py`**:
   * Cung cấp endpoints xem danh sách phim, chi tiết lịch chiếu và kiểm tra sơ đồ ghế của suất chiếu kèm trạng thái `AVAILABLE` hoặc `BOOKED`.

#### B. Tầng Application (`app/application/`)
1. **`services/booking_service.py`**:
   * Hiện thực Use Case đặt vé `create_booking`: Kiểm tra danh sách ghế đầu vào không rỗng và không trùng lặp, xác minh suất chiếu tồn tại, đảm bảo tất cả ghế thuộc đúng phòng chiếu của suất đó, mở Unit of Work, thêm vé và danh sách ghế, gọi `commit()`.
   * Hiện thực Use Case hủy vé `cancel_booking`: Kiểm tra quyền sở hữu vé, chuyển trạng thái vé sang `CANCELLED`, xóa các bản ghi ghế tương ứng để giải phóng chỗ cho người khác.
2. **`services/catalog_service.py`**:
   * Tra cứu danh mục phim đang chiếu, chi tiết phim, danh sách suất chiếu theo phim.
   * Tính toán trạng thái thời gian thực của từng ghế trong phòng chiếu (Ghế nào đã được đặt, ghế nào còn trống).
3. **`services/auth_service.py`**:
   * Quản lý nghiệp vụ tài khoản: Đăng ký (kiểm tra username đã tồn tại chưa, băm mật khẩu qua Argon2) và Đăng nhập (so khớp hash mật khẩu, sinh JWT Bearer token).
4. **`schemas/*.py`**:
   * Các lớp Pydantic định nghĩa cấu trúc dữ liệu gửi lên và trả về giữa Client và API (Request/Response DTOs), thực hiện validate kiểu dữ liệu tự động.

#### C. Tầng Domain (`app/domain/`)
1. **`entities/*.py`**:
   * Các lớp Dataclass mô tả đối tượng thế giới thực: `Movie` (id, title, duration), `Showtime` (id, movie_id, room_name, start_time, price), `Seat` (id, room_name, row, number), `Booking` (id, user_id, showtime_id, status, seat_ids), `User` (id, username, password_hash).
   * Không phụ thuộc bất kỳ ORM nào.
2. **`repositories/*.py`**:
   * Các Interface giao tiếp: `MovieRepository`, `ShowtimeRepository`, `SeatRepository`, `BookingRepository`, `UserRepository`.
   * `unit_of_work.py`: Định nghĩa ngữ cảnh quản lý transaction với context manager (`__enter__`, `__exit__`, `commit`, `rollback`).

#### D. Tầng Infrastructure (`app/infrastructure/`)
1. **`database/base.py` & `session.py`**:
   * Cấu hình kết nối PostgreSQL với chuỗi kết nối từ `Settings`, khởi tạo SQLAlchemy engine và session factory.
2. **`database/models/*.py`**:
   * Các bảng cơ sở dữ liệu vật lý được ánh xạ bằng SQLAlchemy ORM (`users`, `movies`, `showtimes`, `seats`, `bookings`, `booking_seats`).
   * Định nghĩa khóa chính, khóa ngoại (`ForeignKey`) và chỉ mục ràng buộc `UniqueConstraint("showtime_id", "seat_id", name="uq_showtime_seat")`.
3. **`repositories/mappers.py`**:
   * Hàm chuyển đổi qua lại giữa SQLAlchemy Model (đối tượng DB) và Domain Entity (đối tượng nghiệp vụ thuần túy), ngăn cách triệt để không cho model của ORM rò rỉ lên tầng Domain.
4. **`repositories/sqlalchemy_*.py`**:
   * Triển khai cụ thể các câu lệnh truy vấn SQLAlchemy (Select, Insert, Delete).
   * Trong `sqlalchemy_booking_repository.py`: Bắt ngoại lệ `IntegrityError` từ cơ sở dữ liệu khi có xung đột khóa duy nhất và chuyển thành `SeatAlreadyBookedError`.
5. **`repositories/sqlalchemy_unit_of_work.py`**:
   * Hiện thực hóa `UnitOfWork` interface: Gọi `self.session.commit()` khi hoàn thành tác vụ thành công hoặc `self.session.rollback()` khi có lỗi xảy ra.

#### E. Tầng Bổ trợ Kỹ thuật (`app/core/`)
1. **`config.py`**: Quản lý biến môi trường (`DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`) bằng `pydantic-settings`.
2. **`exceptions.py`**: Hệ thống các lỗi nghiệp vụ độc lập với HTTP: `ApplicationError`, `SeatAlreadyBookedError`, `ShowtimeNotFoundError`, `InvalidCredentialsError`, v.v.
3. **`security.py`**: Công cụ bảo mật: Hàm băm và xác thực mật khẩu sử dụng thuật toán **Argon2**, hàm tạo và giải mã token JWT (**HS256**).

---

## 4. Tóm tắt luồng hoạt động đầu-cuối của hệ thống

### Kịch bản 1: Luồng Đặt vé xem phim (`POST /bookings`)

```text
[ Client (React SPA) ]
       │
       │  1. POST /bookings { showtime_id: 1, seat_ids: [5, 6] }
       │     Header: Authorization: Bearer <token>
       ▼
[ Presentation Layer: FastAPI Routes ]
       │
       │  2. Route gọi dependencies:
       │     - get_current_user giải mã JWT -> xác thực User (id=10)
       │     - get_session mở DB session
       │     - get_unit_of_work bọc session vào SQLAlchemyUnitOfWork
       │     - get_booking_service inject UnitOfWork vào BookingService
       ▼
[ Application Layer: BookingService.create_booking ]
       │
       │  3. Kiểm tra logic nghiệp vụ:
       │     - Danh sách ghế không được rỗng và không chứa ID trùng lặp
       │     - Mở context: with self._unit_of_work as uow:
       │     - Kiểm tra suất chiếu (showtime_id) có tồn tại không?
       │     - Kiểm tra toàn bộ ghế có thuộc đúng phòng chiếu của suất chiếu không?
       ▼
[ Infrastructure Layer: SQLAlchemyUnitOfWork ]
       │
       │  4. Thực thi cơ sở dữ liệu:
       │     - Chèn bản ghi vào bảng bookings
       │     - Chèn các bản ghi tương ứng vào bảng booking_seats
       │     - uow.commit() -> đẩy thay đổi xuống PostgreSQL
       ▼
[ PostgreSQL Database ]
       │
       │  5. Kiểm tra ràng buộc cứng UNIQUE(showtime_id, seat_id):
       │     - Nếu hợp lệ: Commit thành công, trả về ID đặt vé
       ▼
[ Response trả ngược về Client ]
       │
       │  6. BookingService trả về Domain Entity Booking
       │  7. Route chuyển đổi sang BookingResponse (Pydantic)
       │  8. Trả về HTTP 201 Created kèm dữ liệu vé cho Client
```

---

### Kịch bản 2: Xử lý Tranh chấp / Xung đột ghế (Race Condition / Double-Booking)

Giả sử Người dùng A và Người dùng B cùng bấm nút đặt **ghế số 5 của suất chiếu số 1** tại cùng một thời điểm:

```text
User A (Request 1) ──────────┐
                             ├─► [ PostgreSQL: Bảng booking_seats ]
User B (Request 2) ──────────┘
```

1. Cả hai request đều vượt qua bước kiểm tra tại `BookingService` vì lúc đó ghế vẫn đang trống trong cơ sở dữ liệu.
2. Cả hai tiến hành thực hiện câu lệnh chèn vào bảng `booking_seats`.
3. Do cơ chế Transaction Isolation và ràng buộc `UNIQUE(showtime_id, seat_id)`:
   * **Request của User A** đến trước một phần triệu giây: Ghi thành công $\to$ Commit $\to$ Trả về `201 Created`.
   * **Request của User B** đến sau: Vi phạm ràng buộc khóa duy nhất `uq_showtime_seat`.
4. **PostgreSQL** ném ra lỗi `IntegrityError` đối với request của User B.
5. **`SQLAlchemyBookingRepository`** bắt lấy `IntegrityError`, tự động kích hoạt `rollback()` và chuyển hóa thành `SeatAlreadyBookedError`.
6. Tầng **Presentation (`main.py`)** bắt được `SeatAlreadyBookedError` và ngay lập tức trả về cho User B mã trạng thái **`HTTP 409 Conflict`** kèm thông báo lỗi rõ ràng.
7. **Kết quả:** Không bao giờ xảy ra tình trạng hai người cùng mua được một ghế, dữ liệu luôn nhất quán tuyệt đối.

---

### Kịch bản 3: Luồng Đăng nhập & Xác thực bảo mật (Authentication Flow)

```text
Client gửi POST /auth/login { username, password }
  │
  ▼
AuthService kiểm tra:
  - Tìm user theo username qua UserRepository
  - Xác minh mật khẩu bằng Argon2 (verify_password)
  - Nếu khớp: Sinh JWT chứa payload { sub: user_id, exp: ... }
  │
  ▼
Client nhận token và đính kèm vào Header các request sau:
  Authorization: Bearer <token>
  │
  ▼
FastAPI Dependency (CurrentUser):
  - Tách token từ header
  - Giải mã và kiểm tra chữ ký bí mật + hạn sử dụng
  - Nạp thực thể User từ DB và chuyển thẳng vào hàm điều khiển
```

---

## 5. Tổng kết giá trị của kiến trúc

| Tiêu chí | Kiến trúc truyền thống thông thường | Kiến trúc Clean Architecture của dự án |
| :--- | :--- | :--- |
| **Mức độ phụ thuộc** | Code nghiệp vụ dính liền vào thư viện ORM và framework API. | Tách rời hoàn toàn. Nghiệp vụ nằm ở Domain thuần túy. |
| **Khả năng kiểm thử (Testing)** | Buộc phải dựng Database và khởi động Server để test. | Dễ dàng viết Unit Test cho tầng Service bằng Fake Repositories trong vài mili-giây. |
| **Khả năng mở rộng & Bảo trì** | Thay đổi cấu trúc bảng hoặc đổi framework sẽ làm vỡ toàn bộ logic. | Chỉ cần thay đổi tầng Infrastructure hoặc API, lõi nghiệp vụ giữ nguyên 100%. |
| **Tính toàn vẹn dữ liệu** | Dễ bị lỗi tranh chấp khi có lượng truy cập đồng thời cao. | Bảo vệ 2 lớp với Transaction Boundary và Database Unique Constraint. |

---

> Trở về trang chính: [README.md](../README.md) | Xem mục lục tài liệu: [docs/README.md](./README.md)
