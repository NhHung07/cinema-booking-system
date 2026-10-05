# Hướng dẫn Cài đặt & Vận hành (Setup & Deployment)

Tài liệu này hướng dẫn chi tiết các phương pháp triển khai dự án **Cinema Booking System**, từ khởi chạy nhanh bằng script tự động đến thiết lập môi trường phát triển cục bộ (Local Development).

---

## 📋 Yêu cầu hệ sinh thái

Tùy vào phương thức khởi chạy bạn chọn, hãy đảm bảo máy tính đã cài đặt các công cụ tương ứng:

| Công cụ | Phiên bản khuyến nghị | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Docker & Docker Compose** | Docker v24+ / Compose v2+ | Khởi chạy toàn bộ hệ thống bằng container (khuyến nghị) |
| **Python** | 3.12 trở lên | Phát triển backend cục bộ |
| **Node.js & npm** | Node v20+ / npm v10+ | Phát triển frontend cục bộ |
| **PostgreSQL** | 16 (hoặc 14+) | Hệ quản trị cơ sở dữ liệu chính |

---

## ⚡ Cách 1: Khởi chạy 1-Click bằng Script (Khuyến nghị cho Linux/macOS)

Dự án cung cấp sẵn hai bash script tiện lợi để quản lý trọn bộ vòng đời container:

### 1. Khởi động toàn bộ hệ thống (`./start.sh`)

Script [`start.sh`](../start.sh) sẽ tự động:
1. Tạo và khởi chạy container **PostgreSQL 16 Alpine** (`cinema-postgres`) trên cổng `5432`.
2. Chờ cơ sở dữ liệu sẵn sàng phản hồi (`pg_isready`).
3. Build và khởi chạy container **FastAPI Backend** (`cinema-api`) trên cổng `8000`, tự động áp dụng Alembic migration.
4. Chạy script nạp dữ liệu mẫu [`scripts/seed.py`](../scripts/seed.py).
5. Build ứng dụng React và phục vụ thông qua container **Nginx Alpine** (`cinema-frontend`) trên cổng `5173`.

```bash
chmod +x start.sh stop.sh
./start.sh
```

Sau khi hoàn tất, bạn có thể truy cập:
- **Giao diện người dùng (Frontend):** <http://localhost:5173>
- **Tài liệu API tương tác (Swagger UI):** <http://localhost:8000/docs>
- **Tài liệu API ReDoc:** <http://localhost:8000/redoc>

### 2. Dừng hệ thống (`./stop.sh`)

Để dừng toàn bộ các container đang chạy:

```bash
./stop.sh
```

---

## 🐳 Cách 2: Khởi chạy bằng Docker Compose

Nếu bạn muốn khởi chạy backend và database bằng cấu hình chuẩn Docker Compose:

```bash
# 1. Khởi chạy toàn bộ hệ thống (PostgreSQL, FastAPI backend, React Frontend)
docker compose up --build -d

# 2. Kiểm tra log các dịch vụ
docker compose logs -f

# 3. Nạp dữ liệu mẫu ban đầu (Catalog seed)
docker compose exec api python scripts/seed.py
```

Khi muốn dừng:
```bash
docker compose down
```

---

## 💻 Cách 3: Thiết lập môi trường phát triển cục bộ (Local Development)

Phương pháp này phù hợp khi bạn cần debug code backend hoặc chỉnh sửa giao diện frontend trực tiếp với tính năng Hot Reload.

### Bước 1: Khởi động cơ sở dữ liệu PostgreSQL

Bạn có thể chạy nhanh một PostgreSQL container bằng Docker:
```bash
docker run -d \
  --name cinema-postgres \
  -e POSTGRES_DB=cinema \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -v cinema_postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine
```

### Bước 2: Cài đặt và cấu hình Backend (FastAPI)

1. Tạo môi trường ảo Python và kích hoạt:
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```

3. Cấu hình biến môi trường:
   Sao chép file mẫu `.env.example` thành `.env`:
   ```bash
   cp .env.example .env
   ```
   Kiểm tra các biến môi trường chính trong `.env`:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cinema
   JWT_SECRET_KEY=your-super-secret-key-change-it-in-production-min-32-chars
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

4. Đồng bộ hóa Schema cơ sở dữ liệu với Alembic:
   ```bash
   alembic upgrade head
   ```

5. Nạp dữ liệu mẫu (phim, phòng chiếu, suất chiếu, ghế):
   ```bash
   python scripts/seed.py
   ```

6. Khởi chạy máy chủ Backend:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Truy cập Swagger UI tại <http://localhost:8000/docs>.

### Bước 3: Cài đặt và chạy Frontend (React + Vite)

Mở một cửa sổ dòng lệnh (terminal) mới:

1. Di chuyển vào thư mục frontend:
   ```bash
   cd frontend
   ```

2. Tạo file cấu hình biến môi trường `.env`:
   ```bash
   cp .env.example .env
   ```
   Nội dung `.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

3. Cài đặt các node packages:
   ```bash
   npm install
   ```

4. Chạy Frontend ở chế độ dev:
   ```bash
   npm run dev
   ```
   Ứng dụng sẽ khả dụng tại <http://localhost:5173>.

---

## 🧪 Chạy Kiểm thử (Testing)

Dự án trang bị bộ test tự động sử dụng **pytest**:

```bash
# Kích hoạt virtualenv trước
source .venv/bin/activate

# Chạy toàn bộ test suite
pytest

# Chạy kèm báo cáo chi tiết
pytest -v -s
```

- **Unit tests (`tests/unit/`):** Kiểm tra logic nghiệp vụ của `BookingService` độc lập hoàn toàn, sử dụng Fake/Mock Repository trong bộ nhớ (không cần DB).
- **Integration tests (`tests/integration/`):** Kiểm thử toàn diện API endpoints với `TestClient` của FastAPI và cơ sở dữ liệu SQLite in-memory biệt lập.

---

## 🛠️ Xử lý sự cố thường gặp (Troubleshooting)

1. **Lỗi cổng bị chiếm dụng (Port Conflict):**
   - Lỗi: `address already in use 0.0.0.0:5432` hoặc `8000`, `5173`.
   - Khắc phục: Kiểm tra các tiến trình đang chiếm cổng bằng `lsof -i :<port>` (Linux/macOS) hoặc `netstat -ano | findstr :<port>` (Windows) và tắt chúng trước khi chạy.

2. **Lỗi CORS khi gọi API từ Frontend:**
   - Đảm bảo biến `CORS_ALLOWED_ORIGINS` trong `.env` backend có chứa origin của frontend (`http://localhost:5173`).

3. **Lỗi `alembic upgrade head` thất bại:**
   - Kiểm tra xem chuỗi kết nối `DATABASE_URL` trong `.env` đã trỏ đúng vào PostgreSQL container đang chạy chưa và cổng kết nối có chính xác không.

---

> Trở về trang chính: [README.md](../README.md) | Xem mục lục tài liệu: [docs/README.md](./README.md)
