# Performance Baseline Phase 1

## Mục tiêu (Objective)

Baseline này đo nguyên trạng Phase 1 trước khi thực hiện cải tiến kiến trúc ở Phase 2. Nó không thêm Redis, caching, thay database, đổi business rule hay tối ưu code. Mục tiêu là tạo bằng chứng có thể lặp lại để so sánh Phase 1 và Phase 2 một cách công bằng.

## Môi trường (Environment)

Kết quả chính thức được tạo bởi [Kaggle Version 4](https://www.kaggle.com/code/nhhung07/kaggle-phase1-benchmark?scriptVersionId=351931925) trong `49m 58s`:

- CPU: Intel Xeon @ 2.20 GHz, 4 logical CPUs.
- RAM: 31.35 GiB.
- OS: Linux `6.12.90+`, x86_64, glibc 2.35.
- Python: 3.12.13.
- PostgreSQL: 14.24.
- Git commit: `e2328fcb5cece70431841f108ec6d8310a46cf42`.
- Timestamp bắt đầu: `2026-09-22T17:54:30.102286+00:00`.

Mỗi lần chạy vẫn tự sinh `environment.json` gồm Python version, CPU model, physical/logical cores, total RAM, OS/platform, UTC timestamp và Git commit SHA. Khi so sánh Phase 2 phải dùng artifact này, không dùng ước lượng.

## Cấu hình application

- Backend: FastAPI/Uvicorn, đúng `1 worker`, không `--reload`.
- Database: PostgreSQL theo production architecture; Alembic migration là schema source of truth.
- Database pool: SQLAlchemy engine mặc định của project với `pool_pre_ping=True`; benchmark không chỉnh pool để làm đẹp số liệu.
- Dataset: 220 benchmark users, 12 movies, 36 showtimes, 3 rooms, 60 physical seats và 720 showtime-seat slots; random seed `42`.
- Commit SHA: tự ghi trong `environment.json`.
- Load generator và application chạy chung Kaggle CPU environment.

## Workload

- Scenario A — Catalogue Browsing: read-heavy mix 50% movies, 30% showtimes theo movie và 20% seat availability.
- Scenario B — Normal Booking Flow: login thật để nhận JWT, browse catalogue, đọc seat list và book một seat hợp lệ riêng cho từng virtual user. Dataset được reset trước mỗi measured run.
- Scenario C — Concurrent Seat Booking: nhiều account cùng tranh một seat. Đúng khi đúng một `201`, có expected `409` khi load lớn hơn 1, không có booking response ngoài dự kiến, và unique `(showtime_id, seat_id)` trong database có đúng một row. Vì Locust có thể spawn user thay thế sau `StopUser`, số attempt/`409` có thể lớn hơn `users - 1`; `users` biểu diễn concurrency chứ không phải tổng số request.

## Cấu hình load

Mặc định chạy `1, 10, 25, 50, 100` concurrent users; `spawn rate=10 users/s`; `duration=60s`; warm-up `30s` với 10 users cho mỗi scenario; `3 repetitions`; seed `42`; backend `1 worker`. Có thể thêm 200 users khi Kaggle còn ổn, nhưng Phase 2 phải dùng chính xác cùng configuration.

## Metric

Locust ghi total requests, requests/sec, average, P50, P95, P99, max latency, failure count và failure rate. `psutil` sampling mỗi giây ghi system CPU/RAM và, khi có `BENCH_SERVER_PID`, app CPU/RSS. Aggregation báo mean, median và standard deviation qua repetitions. Expected `409` của Scenario C được tách khỏi technical failure.

HTTP 5xx, timeout, connection error và vi phạm concurrent correctness trong measured run là dữ liệu baseline hợp lệ: chúng được giữ trong failure metrics hoặc `concurrency_correct=false` và không làm runner bỏ dở các load level còn lại. Runner chỉ dừng khi Locust/tooling lỗi, thiếu artifact CSV/outcome hoặc không thể kiểm tra database.

## Chạy trên Kaggle

1. Import/clone repository vào Kaggle Notebook CPU.
2. Mở `benchmark/kaggle_phase1_benchmark.ipynb`.
3. Chạy tuần tự 10 section: environment, dependency, config, PostgreSQL, app, sanity, Locust, metrics, aggregation, graphs.
4. Nếu PostgreSQL setup hoặc sanity test fail, dừng và sửa nguyên nhân; không fallback ngầm.
5. Mở tab **Output** và download toàn bộ thư mục `phase1-results/` làm artifact chính thức. Notebook này đặt `BENCH_OUTPUT_DIR=/kaggle/working/phase1-results` để output có đường dẫn ổn định.

Chi tiết command và ý nghĩa artifact nằm trong [`benchmark/README.md`](../../benchmark/README.md).

## Kết quả (Results)

Kaggle Version 4 hoàn thành đủ `45` measured runs (`3 scenarios × 5 load levels × 3 repetitions`) và thu `2.751` system-metric samples. Bảng dưới đây lấy trực tiếp từ `summary.csv`; latency dùng millisecond và các giá trị là mean của ba repetitions.

| Scenario | Users | RPS | Avg ms | P50 | P95 | P99 | Failure % | CPU Avg % | App RAM MB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| booking | 1 | 7,47 | 8,82 | 8,00 | 12,67 | 14,67 | 0,00 | 3,99 | 122,88 |
| booking | 10 | 73,09 | 12,71 | 9,00 | 21,00 | 47,33 | 0,00 | 20,23 | 131,41 |
| booking | 25 | 145,55 | 44,46 | 32,67 | 106,33 | 183,33 | 0,00 | 47,87 | 146,41 |
| booking | 50 | 164,24 | 169,71 | 153,33 | 280,00 | 533,33 | 0,00 | 50,37 | 152,88 |
| booking | 100 | 4,45 | 13.012,16 | 12.163,33 | 22.000,00 | 22.000,00 | 33,81 | 8,41 | 150,08 |
| catalogue | 1 | 2,00 | 8,63 | 8,33 | 12,33 | 13,33 | 0,00 | 2,48 | 107,75 |
| catalogue | 10 | 19,82 | 8,67 | 8,00 | 12,33 | 20,00 | 0,00 | 6,55 | 108,15 |
| catalogue | 25 | 48,50 | 8,75 | 7,00 | 13,33 | 30,33 | 0,00 | 12,29 | 108,69 |
| catalogue | 50 | 94,39 | 12,06 | 9,00 | 25,00 | 79,67 | 0,00 | 23,03 | 111,60 |
| catalogue | 100 | 160,57 | 75,11 | 66,33 | 176,67 | 240,00 | 0,00 | 47,84 | 121,13 |
| concurrent | 1 | 9,61 | 6.034,29 | 12.080,00 | 12.080,00 | 12.080,00 | 0,00 | 5,29 | 149,37 |
| concurrent | 10 | 19,55 | 479,47 | 766,67 | 966,67 | 966,67 | 0,00 | 3,46 | 137,38 |
| concurrent | 25 | 19,64 | 700,08 | 823,33 | 1.500,00 | 1.700,00 | 0,00 | 7,43 | 156,23 |
| concurrent | 50 | 20,41 | 1.379,54 | 1.500,00 | 2.766,67 | 3.166,67 | 0,00 | 12,85 | 196,05 |
| concurrent | 100 | 1,90 | 27.460,83 | 24.966,67 | 35.333,33 | 35.666,67 | 62,49 | 11,19 | 177,24 |

Các kết luận baseline chính:

- `catalogue` scale ổn đến 100 users: 160,57 RPS, P95 176,67 ms và 0% failure.
- `booking` đạt đỉnh tại 50 users: 164,24 RPS, P95 280 ms và 0% failure; tại 100 users throughput sụp xuống 4,45 RPS, P95 tăng lên 22 giây và failure rate trung bình là 33,81%.
- `concurrent` giữ đúng uniqueness từ 1 đến 50 users. Tại 100 users, `concurrency_correct_all=false`: ba repetitions có tổng 223 requests, 69 technical failures; chỉ repetition đầu tạo được một booking, ghi 55 expected conflicts và 8 unexpected booking failures. Hai repetitions sau không tạo được allocation vì hệ thống đã quá tải trước booking flow.
- `runs.csv` giữ số từng repetition; `summary.json` phù hợp cho xử lý tự động; năm graph nằm trong `charts/`.

## Giới hạn (Limitations)

- Locust và FastAPI cạnh tranh cùng CPU/RAM trên Kaggle, nên kết quả là whole-notebook capacity chứ không cô lập server. Điều này phải giữ nguyên ở Phase 2.
- Kaggle CPU model và contention có thể thay đổi giữa session; phải đối chiếu `environment.json` và chạy repetitions.
- Localhost loại bỏ network latency thực tế.
- Scenario B chỉ tạo một booking/virtual user trong mỗi run rồi duy trì read flow, nhằm tránh deliberate seat conflict; write/read mix này phải giữ nguyên ở Phase 2.
- `psutil` system CPU gồm cả load generator và PostgreSQL. App-only metrics chỉ có khi `BENCH_SERVER_PID` được cấu hình.

## Quy tắc so sánh với Phase 2

Phase 2 phải giữ nguyên hardware/Kaggle accelerator setting, PostgreSQL version và schema-compatible dataset, seed, backend worker count, request mix, users, spawn rate, duration, warm-up, repetitions, Locust/tool versions, metric interval và cách client/server dùng chung CPU. Chạy trên cùng commit artifact policy và ghi Git SHA. Không so sánh một fallback SQLite run với PostgreSQL baseline.

So sánh cuối cùng phải tính từ measured artifacts:

| Metric | Phase 1 | Phase 2 | Change |
| --- | ---: | ---: | ---: |
| RPS | measured | measured | calculated |
| Avg latency | measured | measured | calculated |
| P50 / P95 / P99 | measured | measured | calculated |
| Failure rate | measured | measured | calculated |
| CPU / RAM | measured | measured | calculated |
