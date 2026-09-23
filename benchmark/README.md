# Phase 1 Benchmark

Thư mục này tạo baseline performance reproducible cho backend hiện tại. Benchmark không thêm cache, không thay database, không đổi business logic và không phải một bản tối ưu. PostgreSQL là database bắt buộc cho kết quả production-equivalent.

## Kiến trúc và workload

```text
Locust ──HTTP──> FastAPI (1 worker) ──> Application ──> Repository ──> PostgreSQL
   │
   └── metric collector (psutil) đọc CPU/RAM của cùng Kaggle CPU và process backend
```

Ba scenario được chạy độc lập:

- `catalogue`: request mix 50% `GET /movies`, 30% `GET /showtimes?movie_id=...`, 20% `GET /showtimes/{id}/seats`.
- `booking`: mỗi virtual user login qua `POST /auth/login`, browse movies/showtimes/seats và tạo một booking trên seat riêng. Sau booking, user tiếp tục read flow và kiểm tra booking để giữ load ổn định; token không được hard-code.
- `concurrent`: mọi virtual user dùng account riêng nhưng cùng đặt một `(showtime_id, seat_id)`. Đúng khi có đúng một `201`, có cạnh tranh thực sự với `409` ở load lớn hơn 1, không có booking response ngoài dự kiến và database chỉ có một allocation. `409` được ghi là expected business outcome, không tính là technical failure. Locust có thể spawn user thay thế sau `StopUser`, nên số attempt/`409` có thể lớn hơn `users - 1`; `users` là mức concurrency, không phải tổng số request.

Dataset mặc định cố định với random seed `42`: 220 users, 12 movies, 36 showtimes, 3 rooms, 60 physical seats (20/room), 720 showtime-seat slots. ID thật sau seed được ghi vào `benchmark/.state/dataset.json`; workload không giả định ID bắt đầu từ 1. Reset chỉ xóa record mang namespace `bench-user-*`, `BENCH_MOVIE_*`, `BENCH_ROOM_*`.

## Chạy local

Yêu cầu PostgreSQL đang chạy và schema đã migrate. Cài dependency rồi khởi động API bằng đúng một worker, không dùng reload:

```powershell
python -m pip install -r requirements.txt -r benchmark/requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/cinema"
$env:JWT_SECRET_KEY = "local-benchmark-only-secret-32-bytes"
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Ở terminal khác, truyền PID của Uvicorn để thu app RSS/CPU chính xác rồi chạy toàn bộ suite:

```powershell
$env:BENCH_SERVER_PID = "<uvicorn-pid>"
python benchmark/scripts/run_benchmark.py
```

Runner tự kiểm tra `/health`, warm-up, reset/seed trước từng measured run, chạy Locust headless, thu metric, kiểm tra same-seat correctness, aggregate và vẽ graph. Có thể chạy nhanh để kiểm tra tooling:

Technical failure của request (HTTP 5xx, timeout, connection error) vẫn được Locust ghi vào `failure count`/`failure rate` nhưng không làm dừng toàn bộ ma trận load. Vi phạm concurrent correctness được ghi bằng `concurrency_correct=false` và `concurrency_error` trong manifest thay vì làm mất các load level sau. Runner chỉ dừng khi Locust/tooling không chạy được, thiếu artifact CSV/outcome hoặc không thể kiểm tra database.

```powershell
python benchmark/scripts/run_benchmark.py --scenarios catalogue --loads 1,10 --duration 15s --warmup-duration 5s --repetitions 1
```

Lệnh seed/reset độc lập:

```powershell
python benchmark/scripts/seed_benchmark.py
python benchmark/scripts/reset_benchmark.py
```

SQLite chỉ được phép cho automated test của helper khi đặt rõ `BENCH_ALLOW_NON_POSTGRES=1`; kết quả đó tuyệt đối không phải production-equivalent baseline.

## Tham số

| Environment variable | Mặc định | Ý nghĩa |
| --- | ---: | --- |
| `BENCH_SCENARIOS` | `catalogue,booking,concurrent` | Scenario cần chạy |
| `BENCH_LOAD_LEVELS` | `1,10,25,50,100` | Concurrent users |
| `BENCH_SPAWN_RATE` | `10` | Users được spawn mỗi giây |
| `BENCH_DURATION` | `60s` | Duration của mỗi measured run |
| `BENCH_WARMUP_DURATION` | `30s` | Warm-up mỗi scenario, bị loại khỏi result |
| `BENCH_WARMUP_USERS` | `10` | Users trong warm-up |
| `BENCH_REPETITIONS` | `3` | Số lần lặp cho mỗi load level |
| `BENCH_RANDOM_SEED` | `42` | Seed deterministic |
| `BENCH_BACKEND_WORKERS` | `1` | Runner từ chối giá trị khác 1 |
| `BENCH_METRICS_INTERVAL` | `1` | Chu kỳ sampling system metrics, giây |
| `BENCH_SERVER_PID` | trống | PID backend để thu riêng app CPU/RSS |
| `BENCH_OUTPUT_DIR` | timestamp mới | Thư mục kết quả tùy chọn |

Các flag `--scenarios`, `--loads`, `--spawn-rate`, `--duration`, `--warmup-duration`, `--repetitions`, `--output` override environment tương ứng. Dùng cùng bộ tham số cho Phase 2.

## Chạy trên Kaggle CPU

1. Tạo Kaggle Notebook CPU, bật Internet để clone repository nếu repository chưa có trong Dataset/Input.
2. Mở `benchmark/kaggle_phase1_benchmark.ipynb` trong repository.
3. Chạy lần lượt Section 1 đến Section 6. Section 4 cài/khởi động PostgreSQL, migrate và seed; bất kỳ lỗi nào phải dừng notebook.
4. Chạy Section 7. Đây là Locust headless; không cần mở Web UI. Bộ mặc định gồm 45 measured runs nên có thể mất nhiều thời gian.
5. Section 9 hiển thị bảng tổng hợp thật, Section 10 hiển thị năm graph.
6. Mở tab **Output** và download toàn bộ thư mục `phase1-results/` làm artifact của Phase 1. Notebook đặt `BENCH_OUTPUT_DIR=/kaggle/working/phase1-results` để output có đường dẫn ổn định.

Không chuyển ngầm sang SQLite nếu PostgreSQL không khởi động. Hãy lưu log lỗi PostgreSQL và coi run đó chưa tạo được baseline.

## Kết quả và cách đọc

Baseline chính thức hiện tại là [Kaggle Version 4](https://www.kaggle.com/code/nhhung07/kaggle-phase1-benchmark?scriptVersionId=351931925), chạy từ commit `e2328fc`, hoàn thành 45 measured runs trong `49m 58s`. Bảng số liệu và phân tích nằm trong [`docs/phase2/baseline.md`](../docs/phase2/baseline.md). Generated output đầy đủ vẫn nằm trong tab **Output** của notebook và không được commit vào Git.

Mỗi run có `locust_stats.csv`, `locust_stats_history.csv`, `system-metrics.csv`, `locust.log`; concurrent run có thêm `concurrent-outcomes.json`. Root result có:

- `environment.json`: hardware, OS, Python, Git SHA, tham số và ghi chú load generator/backend dùng chung CPU.
- `manifest.json`: đường dẫn và metadata của mọi measured run.
- `runs.csv`: metric từng repetition.
- `summary.csv` / `summary.json`: mean, median, standard deviation theo scenario/load.
- `charts/`: RPS, P95, P99, failure rate và CPU theo concurrency.

Không commit các generated result. Chỉ `.gitkeep` được Git theo dõi.
