# Tài liệu kỹ thuật Cinema Booking System

Chào mừng bạn đến với trung tâm tài liệu kỹ thuật của dự án **Cinema Booking System**. Thư mục này tập hợp toàn bộ các hướng dẫn, tài liệu thiết kế kiến trúc, cơ sở dữ liệu, API, frontend và báo cáo hiệu năng chuyên sâu.

---

## 🧭 Bản đồ tài liệu (Documentation Map)

Hệ thống tài liệu được phân chia theo từng chủ đề chuyên biệt giúp việc tra cứu và phát triển trở nên thuận tiện:

| Tài liệu | Mô tả nội dung chính | Đối tượng quan tâm |
| :--- | :--- | :--- |
| 🏗️ [**Kiến trúc hệ thống (`architecture.md`)**](./architecture.md) | Kiến trúc phân tầng Clean Architecture, nguyên tắc Dependency Inversion, ranh giới Unit of Work, Transaction flow chống double-booking. | Backend Engineers, Architects |
| 🗄️ [**Thiết kế cơ sở dữ liệu (`database.md`)**](./database.md) | Sơ đồ ERD (Mermaid), chi tiết các bảng, khóa ngoại, ràng buộc `UNIQUE(showtime_id, seat_id)`, chiến lược đánh chỉ mục (indexing) và Alembic migration. | Database Engineers, Backend |
| 📡 [**Đặc tả REST API (`api.md`)**](./api.md) | Chi tiết toàn bộ endpoints (Authentication, Movies, Showtimes, Seats, Bookings), cấu trúc request/response, mã trạng thái HTTP chuẩn mực và cơ chế bảo mật JWT Bearer. | Frontend, Mobile, Integration |
| 💻 [**Tài liệu Frontend (`frontend.md`)**](./frontend.md) | Kiến trúc ứng dụng React + Vite + TypeScript, quản lý trạng thái xác thực (`AuthContext`), cấu hình Axios Interceptors, hệ thống component và giao diện người dùng. | Frontend Engineers |
| 🚀 [**Hướng dẫn Cài đặt & Vận hành (`setup.md`)**](./setup.md) | Hướng dẫn chi tiết cách chạy dự án bằng script tự động 1-click (`start.sh` / `stop.sh`), chạy qua Docker Compose hoặc chạy từng dịch vụ thủ công trên máy local. | Developers, DevOps |
| 📊 [**Kiểm thử tải & Benchmark (`benchmark.md`)**](./benchmark.md) | Bộ kịch bản kiểm thử hiệu năng với Locust, mô hình dữ liệu kiểm thử deterministic (seed 42), cách chạy benchmark cục bộ và trên Kaggle Notebook CPU. | QA, Performance Engineers |
| 📈 [**Báo cáo Baseline Phase 1 (`phase2/baseline.md`)**](./phase2/baseline.md) | Số liệu đo đạc thực tế của hệ thống ở Phase 1 làm căn cứ chuẩn đối chuẩn (baseline) cho các tối ưu hóa ở Phase 2 (RPS, P95/P99 latency, tài nguyên CPU/RAM). | Tech Lead, Evaluators |

---

## 📌 Các quy chuẩn kỹ thuật quan trọng cần lưu ý

1. **Nguyên tắc phân tầng (Dependency Rule):**
   - Không được phép import các thư viện của tầng ngoài (như FastAPI, SQLAlchemy ORM) vào trong `domain` hoặc `application`.
   - Mọi nghiệp vụ phải đi qua `BookingService`, `CatalogService`, `AuthService`.
2. **Xử lý xung đột ghế (Double-Booking Prevention):**
   - Tầng ứng dụng thực hiện kiểm tra sơ bộ, nhưng **PostgreSQL với ràng buộc duy nhất `UNIQUE(showtime_id, seat_id)` tại bảng `booking_seats` mới là tuyến phòng thủ tối hậu**.
   - Khi có tranh chấp ghi dữ liệu, cơ chế transaction rollback sẽ được kích hoạt và trả về mã lỗi `409 Conflict`.
3. **Bảo mật xác thực:**
   - Mật khẩu người dùng được băm an toàn bằng thuật toán **Argon2** (thông qua `pwdlib`).
   - Token chứng thực sử dụng chuẩn **JWT Bearer (HS256)** với hạn sử dụng xác định.

---

> Trở về trang chính: [README.md](../README.md)
