# Hướng dẫn Kiểm thử Tải & Hiệu năng (Benchmark Guide)

Thư mục `benchmark/` cung cấp bộ công cụ đo lường hiệu năng và sức chịu tải có thể tái lập (reproducible performance baseline) cho hệ thống **Cinema Booking System**. Bộ kiểm thử sử dụng công cụ **Locust** kết hợp với tiến trình thu thập tài nguyên hệ thống **psutil**.

Mục tiêu chính của bộ benchmark này là ghi nhận chính xác năng lực xử lý ở **Phase 1** (trước khi áp dụng bộ nhớ đệm Cache/Redis hay tối ưu kiến trúc ở Phase 2).

---

## 🏗️ Mô hình kiểm thử tải

```text
Locust (Load Generator) ──HTTP──> FastAPI (1 worker) ──> SQLAlchemy ──> PostgreSQL
        │
        └── psutil metric collector (giám sát CPU/RAM hệ thống và tiến trình API)
```

---

## 🎯 3 Kịch bản kiểm thử (Scenarios)

1. **`catalogue` (Đọc danh mục - Read Heavy):**
   - Tỷ lệ phân bổ request: 50% `GET /movies`, 30% `GET /showtimes?movie_id=...`, 20% `GET /showtimes/{id}/seats`.
   - Mô phỏng hành vi duyệt phim, xem lịch chiếu và xem sơ đồ rạp của phần lớn người dùng.

2. **`booking` (Quy trình đặt vé tiêu chuẩn - Normal Booking Flow):**
   - Mỗi virtual user thực hiện đăng nhập qua `POST /auth/login` để lấy JWT Bearer token thật.
   - Duyệt catalogue và thực hiện đặt 1 ghế hợp lệ riêng biệt cho mình.
   - Sau khi đặt, user tiếp tục chu trình đọc để duy trì mức tải liên tục lên máy chủ.

3. **`concurrent` (Tranh chấp cùng một ghế - Concurrent Seat Booking):**
   - Tất cả các virtual users đều có tài khoản riêng nhưng cùng gửi request đặt chung **một vị trí ghế duy nhất** `(showtime_id, seat_id)`.
   - **Tiêu chuẩn tính đúng đắn (Correctness Criteria):**
     - Đúng duy nhất một request nhận mã thành công `201 Created`.
     - Các request đến sau hoặc bị tranh chấp phải nhận đúng mã `409 Conflict`.
     - Cơ sở dữ liệu PostgreSQL tại bảng `booking_seats` chỉ được phép tồn tại đúng 1 bản ghi duy nhất.
     - Mã lỗi `409` ở kịch bản này được tính là **kết quả nghiệp vụ mong đợi (Expected Outcome)**, không phải lỗi kỹ thuật (technical failure).

---

## 🎲 Tập dữ liệu chuẩn (Deterministic Dataset)

Để đảm bảo kết quả đo đạc giữa các lần chạy và giữa các Phase luôn công bằng và so sánh được:
- Sử dụng số ngẫu nhiên cố định (Random seed = `42`).
- Dataset gồm: **220 users**, **12 movies**, **36 showtimes**, **3 rooms**, **60 physical seats** (20 ghế/phòng) và **720 slots** ghế-suất chiếu.
- Dữ liệu benchmark được gắn namespace riêng (`bench-user-*`, `BENCH_MOVIE_*`) giúp việc dọn dẹp (reset) độc lập hoàn toàn với dữ liệu thực tế.

---

## 💻 Hướng dẫn chạy Benchmark Cục bộ (Local)

### 1. Chuẩn bị môi trường

Cài đặt các gói phụ thuộc bổ sung:
```bash
pip install -r requirements.txt -r benchmark/requirements.txt
```

Khởi chạy PostgreSQL và API bằng đúng **1 worker** (không bật `--reload`):
```bash
# Thiết lập biến môi trường
export DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/cinema"
export JWT_SECRET_KEY="local-benchmark-only-secret-32-bytes"

# Áp dụng migration
alembic upgrade head

# Chạy FastAPI backend với 1 worker
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

### 2. Thực thi kịch bản kiểm thử

Mở một terminal mới, lấy PID của tiến trình uvicorn để đo CPU/RAM chính xác:

```bash
# Thiết lập PID của server (tùy chọn)
export BENCH_SERVER_PID="<uvicorn-pid>"

# Chạy toàn bộ bộ kiểm thử
python benchmark/scripts/run_benchmark.py
```

Để chạy kiểm tra nhanh (Smoke test) với số lượng tải nhỏ:
```bash
python benchmark/scripts/run_benchmark.py --scenarios catalogue --loads 1,10 --duration 15s --warmup-duration 5s --repetitions 1
```

Lệnh seed hoặc reset dữ liệu benchmark độc lập:
```bash
python benchmark/scripts/seed_benchmark.py
python benchmark/scripts/reset_benchmark.py
```

---

## ☁️ Chạy trên Kaggle Notebook CPU

Dự án cung cấp sẵn notebook tự động hóa hoàn toàn [`benchmark/kaggle_phase1_benchmark.ipynb`](../benchmark/kaggle_phase1_benchmark.ipynb):

1. Tạo Kaggle Notebook mới với môi trường **CPU**, bật **Internet: On**.
2. Upload hoặc clone mã nguồn vào notebook.
3. Chạy lần lượt các Section:
   - Cài đặt & khởi chạy PostgreSQL 14 / 16.
   - Migrate schema và nạp benchmark dataset.
   - Chạy Locust ở chế độ Headless qua 45 vòng đo (3 scenarios × 5 load levels × 3 repetitions).
   - Tự động tổng hợp số liệu, xuất biểu đồ và sinh file `phase1-results.zip`.

---

## ⚙️ Bảng tham số cấu hình

| Biến môi trường | Tham số dòng lệnh | Mặc định | Mô tả |
| :--- | :--- | :--- | :--- |
| `BENCH_SCENARIOS` | `--scenarios` | `catalogue,booking,concurrent` | Các kịch bản cần thực thi |
| `BENCH_LOAD_LEVELS` | `--loads` | `1,10,25,50,100` | Số lượng concurrent users |
| `BENCH_SPAWN_RATE` | `--spawn-rate` | `10` | Tốc độ tăng user (users/giây) |
| `BENCH_DURATION` | `--duration` | `60s` | Thời gian chạy cho mỗi lần đo |
| `BENCH_WARMUP_DURATION`| `--warmup-duration`| `30s` | Thời gian warm-up bỏ qua |
| `BENCH_REPETITIONS` | `--repetitions` | `3` | Số lần lặp lại cho mỗi mức tải |
| `BENCH_RANDOM_SEED` | `--seed` | `42` | Seed sinh dữ liệu ngẫu nhiên |
| `BENCH_OUTPUT_DIR` | `--output` | `benchmark/results/<timestamp>` | Thư mục lưu trữ artifact kết quả |

---

## 📊 Kết quả đo đạc Baseline thực tế

Số liệu chi tiết đo đạc chính thức trên môi trường Kaggle CPU 4 cores / 32GB RAM cùng phân tích chuyên sâu được trình bày chi tiết tại:

👉 [**Báo cáo Hiệu năng Baseline Phase 1 (`docs/phase2/baseline.md`)**](./phase2/baseline.md)

---

> Trở về trang chính: [README.md](../README.md) | Xem mục lục tài liệu: [docs/README.md](./README.md)
