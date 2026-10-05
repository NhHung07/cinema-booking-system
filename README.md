# Cinema Booking System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

Hệ thống đặt vé rạp chiếu phim Fullstack hiện đại, được thiết kế theo nguyên lý **Clean Architecture**, trang bị cơ chế xử lý tranh chấp ghế thời gian thực (concurrency control), bảo mật mật khẩu với **Argon2**, xác thực **JWT Bearer**, giao diện **React + Vite** trực quan và bộ công cụ đo lường tải **Locust**.

---

## 👥 Thành viên nhóm phát triển

| STT | Họ và tên | Mã sinh viên |
| :---: | :--- | :---: |
| 1 | **Trần Nhật Hưng** | `24021507` |
| 2 | **Nguyễn Công Huy Hoàng** | `24021486` |
| 3 | **Phạm Đức Hùng** | `24021499` |

---

## ✨ Tính năng nổi bật

- 🛡️ **Ngăn chặn Double-Booking an toàn:** Giải quyết triệt để race condition khi nhiều người dùng cùng tranh đặt một ghế trong cùng tích tắc bằng ràng buộc mức cơ sở dữ liệu `UNIQUE(showtime_id, seat_id)` trong PostgreSQL, tự động rollback transaction và trả về HTTP `409 Conflict`.
- 🏛️ **Kiến trúc phân tầng sạch (Clean Architecture):** Tách biệt rạch ròi giữa Domain Entities, Application Services (Use Cases), Infrastructure Adapters (SQLAlchemy) và API Delivery (FastAPI). Tầng nghiệp vụ không phụ thuộc vào framework.
- 🔐 **Bảo mật chuẩn mực:** Mật khẩu người dùng được băm an toàn bằng thuật toán **Argon2** (thông qua `pwdlib`). Xác thực phiên làm việc bằng **JWT (JSON Web Token)** với `HS256`.
- 💻 **Giao diện người dùng hiện đại:** Ứng dụng SPA viết bằng React 18, TypeScript và Vite; hỗ trợ sơ đồ chọn ghế trực quan theo thời gian thực, modal vé điện tử và trang quản lý vé đã đặt.
- 🐳 **Triển khai 1-Click với Docker:** Khởi chạy toàn bộ hệ thống (PostgreSQL, Backend API, Frontend Nginx) chỉ với một lệnh duy nhất.
- 📊 **Bộ đo lường hiệu năng có thể tái lập (Reproducible Benchmark):** Tích hợp sẵn kịch bản Locust và dataset chuẩn (deterministic seed `42`), cho phép đo đạc RPS, P95/P99 latency và tiêu thụ tài nguyên trên môi trường máy chủ hoặc Kaggle CPU.

---

## 🏛️ Kiến trúc tổng quan hệ thống

```text
[ Trình duyệt / Client ]
           │
           ├── (Cổng 5173: HTML/JS/CSS) ──> [ Container Frontend: Nginx + React SPA ]
           │
           └── (Cổng 8000: RESTful API) ──> [ Container Backend: FastAPI ]
                                                        │
                                                        ├── Tầng Application (BookingService, CatalogService, AuthService)
                                                        │
                                                        ├── Tầng Domain (Entities & UnitOfWork Interfaces)
                                                        │
                                                        └── Tầng Infrastructure (SQLAlchemy 2.0 Adapters)
                                                                        │
                                                                        ↓
                                                         [ Container Database: PostgreSQL 16 ]
```

---

## 🧭 Bản đồ tài liệu kỹ thuật (Documentation Index)

Toàn bộ tài liệu chuyên sâu theo từng chủ đề được tổ chức quy củ trong thư mục [`docs/`](./docs/README.md):

| Tài liệu | Nội dung chi tiết |
| :--- | :--- |
| 📖 [**docs/README.md**](./docs/README.md) | **Cổng thông tin tài liệu:** Mục lục và hướng dẫn tra cứu toàn bộ tài liệu kỹ thuật. |
| 🚀 [**docs/setup.md**](./docs/setup.md) | **Hướng dẫn Cài đặt & Vận hành:** Khởi chạy bằng script 1-click, Docker Compose và thiết lập môi trường Local Dev. |
| 🏗️ [**docs/architecture.md**](./docs/architecture.md) | **Kiến trúc hệ thống:** Phân tầng Clean Architecture, Dependency Inversion, Transaction Boundary và Booking Flow. |
| 🗄️ [**docs/database.md**](./docs/database.md) | **Thiết kế Cơ sở dữ liệu:** Sơ đồ quan hệ ERD, cấu trúc bảng, ràng buộc chống xung đột ghế và chiến lược đánh Index. |
| 📡 [**docs/api.md**](./docs/api.md) | **Đặc tả REST API:** Chi tiết toàn bộ endpoints, payload mẫu, định dạng phản hồi và bảng mã lỗi HTTP. |
| 💻 [**docs/frontend.md**](./docs/frontend.md) | **Kiến trúc Frontend:** Cấu trúc React/Vite/TS, quản lý token với Axios Interceptors và trải nghiệm người dùng. |
| 📊 [**docs/benchmark.md**](./docs/benchmark.md) | **Kiểm thử Tải & Hiệu năng:** 3 kịch bản Locust (catalogue, booking, concurrent), dataset chuẩn và cách chạy đo đạc. |
| 📈 [**docs/phase2/baseline.md**](./docs/phase2/baseline.md) | **Báo cáo Baseline Phase 1:** Bảng số liệu đo đạc thực tế trên Kaggle CPU làm căn cứ đối chuẩn. |

---

## ⚡ Khởi chạy nhanh (Quick Start)

### Cách 1: Sử dụng Script 1-Click (Khuyến nghị)

Chạy script khởi động để tự động dựng PostgreSQL, áp dụng migration, nạp dữ liệu mẫu và chạy Frontend + Backend:

```bash
chmod +x start.sh stop.sh
./start.sh
```

Dừng toàn bộ hệ thống:
```bash
./stop.sh
```

### Cách 2: Sử dụng Docker Compose

```bash
# Khởi chạy PostgreSQL và API
docker compose up --build -d

# Nạp dữ liệu mẫu ban đầu
docker compose exec api python scripts/seed.py
```

### 🌐 Các cổng dịch vụ sau khi khởi động:
- **Giao diện đặt vé (Frontend):** <http://localhost:5173>
- **Tài liệu API tương tác (Swagger UI):** <http://localhost:8000/docs>
- **Tài liệu API chuẩn ReDoc:** <http://localhost:8000/redoc>
- **Cơ sở dữ liệu PostgreSQL:** `localhost:5432` (user/pass: `postgres`/`postgres`, db: `cinema`)

> 💡 Xem hướng dẫn chi tiết cách thiết lập môi trường phát triển cục bộ (Local Python virtualenv & Node.js) tại [docs/setup.md](./docs/setup.md).

---

## 📂 Cấu trúc thư mục dự án

```text
cinema-booking-system/
├── app/                     # Mã nguồn Backend FastAPI
│   ├── api/                 # Routes HTTP, dependencies xác thực, exception handlers
│   ├── application/         # Dịch vụ nghiệp vụ (Auth, Catalog, Booking) & Pydantic DTOs
│   ├── domain/              # Entities và interfaces kho lưu trữ (Repository/UnitOfWork)
│   ├── infrastructure/      # SQLAlchemy ORM models, session & DB adapters
│   └── core/                # Cấu hình Settings, bảo mật JWT/Argon2 và typed exceptions
├── frontend/                # Mã nguồn Frontend React + Vite + TypeScript
│   ├── src/                 # Components, Pages, Context, API client, CSS styles
│   └── nginx.conf           # Cấu hình Nginx phục vụ web bundle trong container
├── docs/                    # Thư mục chứa toàn bộ tài liệu kỹ thuật chuyên sâu
│   ├── README.md            # Mục lục tổng hợp tài liệu
│   ├── architecture.md      # Thiết kế kiến trúc phân tầng
│   ├── database.md          # Thiết kế CSDL, ERD & Indexing
│   ├── api.md               # Đặc tả chi tiết các REST API
│   ├── frontend.md          # Tài liệu hướng dẫn Frontend
│   ├── setup.md             # Hướng dẫn cài đặt & triển khai
│   ├── benchmark.md         # Hướng dẫn kiểm thử tải Locust
│   └── phase2/baseline.md   # Báo cáo số liệu hiệu năng Phase 1
├── benchmark/               # Kịch bản đo tải Locust, runner & Kaggle notebook
├── migrations/              # Alembic database migrations
├── scripts/                 # Scripts tiện ích (seed.py nạp dữ liệu mẫu)
├── tests/                   # Bộ kiểm thử tự động (Unit & Integration tests)
├── docker-compose.yml       # Cấu hình Docker Compose cho DB và API
├── Dockerfile               # Cấu hình đóng gói container cho Backend
├── start.sh                 # Script 1-click khởi chạy toàn bộ hệ thống
├── stop.sh                  # Script 1-click dừng toàn bộ hệ thống
└── requirements.txt         # Danh sách thư viện Python phụ thuộc
```

---

## 📡 Tóm tắt API Endpoints

| Phương thức | Đường dẫn Endpoint | Xác thực | Mô tả nghiệp vụ |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Không | Đăng ký tài khoản người dùng mới |
| `POST` | `/auth/login` | Không | Đăng nhập nhận JWT Bearer Token |
| `GET` | `/movies`, `/movies/{id}` | Không | Xem danh mục phim và chi tiết phim |
| `GET` | `/showtimes?movie_id=&date=` | Không | Tra cứu danh sách suất chiếu |
| `GET` | `/showtimes/{id}/seats` | Không | Lấy sơ đồ ghế và trạng thái khả dụng thời gian thực |
| `POST` | `/bookings` | **Bearer JWT** | Đặt vé theo giao dịch an toàn (trả về 409 nếu trùng ghế) |
| `GET` | `/bookings/me` | **Bearer JWT** | Xem danh sách vé đã đặt của tài khoản |
| `GET` | `/bookings/{id}` | **Bearer JWT** | Xem chi tiết thông tin đơn vé |
| `DELETE`| `/bookings/{id}` | **Bearer JWT** | Hủy vé đã đặt và giải phóng ghế lập tức |
| `GET` | `/health` | Không | Kiểm tra trạng thái hoạt động của hệ thống |

> 📖 Xem đặc tả chi tiết request/response và mã lỗi tại [docs/api.md](./docs/api.md).

---

## 🧪 Kiểm thử tự động (Automated Testing)

Chạy bộ kiểm thử tự động với `pytest`:

```bash
# Kích hoạt môi trường ảo
source .venv/bin/activate  # Trên Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Trên Windows

# Chạy test
pytest
```

- **Unit Tests (`tests/unit/`):** Kiểm thử trọn vẹn nghiệp vụ đặt vé `BookingService` không cần database thật (sử dụng in-memory mock repository).
- **Integration Tests (`tests/integration/`):** Kiểm thử toàn bộ API endpoints với FastAPI TestClient và SQLite database độc lập.
