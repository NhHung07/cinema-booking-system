# Đánh giá kiến trúc backend trên Kaggle CPU

## Mục đích

Bộ thí nghiệm so sánh tác động của Redis cache-aside và số worker API đến throughput, độ trễ, số truy vấn database và tài nguyên. Nghiệp vụ, SQL, schema PostgreSQL và hợp đồng API đặt vé được giữ nguyên giữa các biến thể.

| Biến thể | Worker | Cache danh mục | Pool mỗi worker | Overflow | Tổng pool API |
|---|---:|---|---:|---:|---:|
| A | 1 | Tắt | 8 | 0 | 8 |
| B | 1 | Redis | 8 | 0 | 8 |
| C | 2 | Tắt | 4 | 0 | 8 |
| D | 2 | Redis | 4 | 0 | 8 |

Pool timeout là 3 giây. Các kết nối quan sát và quản trị được ghi nhận riêng. A là kiến trúc hiện tại với cấu hình thí nghiệm chuẩn hóa và instrumentation chung, không phải phép đo cấu hình production trước đó.

## Chuẩn bị mã nguồn

Chạy tại thư mục gốc repository:

```bash
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python --require-hashes -r experiments/phase2/requirements.lock.txt
.venv/bin/python -m experiments.phase2.bundle --output /tmp/cinema-phase2-source.tar.gz
```

Lệnh bundle đóng gói backend, migration, kiểm thử, dependency đã khóa và công cụ thí nghiệm. Không đóng gói `.env`, môi trường ảo, frontend hoặc dữ liệu kết quả. Đích bundle phải nằm ngoài repository và chưa tồn tại.

Tạo Kaggle Dataset riêng chứa `cinema-phase2-source.tar.gz`, sau đó thêm Dataset vào notebook `experiments/phase2/kaggle_cpu.ipynb`.

## Chạy trên Kaggle

1. Chọn **Accelerator: None**, bật Internet cho bước chuẩn bị dependency.
2. Chạy ô giải nén Dataset; checksum bundle được hiển thị để đối chiếu.
3. Chạy bootstrap. Công cụ chuẩn bị Python 3.12, PostgreSQL 16 và Redis 7. Các gói Python được cài theo lock có checksum.
4. Chạy kiểm chứng chức năng. Công cụ tạo PostgreSQL/Redis cục bộ riêng và chạy toàn bộ kiểm thử, gồm migration và tranh chấp hai worker.
5. Chạy smoke với bộ dữ liệu chuẩn: 16 lượt, 10 người dùng, warm-up 5 giây, đo 10 giây.
6. Nếu smoke đạt, chạy full trong cùng phiên: 144 lượt với ba lần lặp.
7. Chạy tổng hợp và tải archive kết quả trong `/kaggle/working`.

Bootstrap chỉ cho phép cài dịch vụ trong môi trường Kaggle có quyền root và APT. Nó dùng repository chính thức của PostgreSQL và Redis, ngăn package tự khởi động dịch vụ trong lúc cài, rồi khôi phục chính sách khởi động ban đầu. Các dịch vụ đo tải được runner khởi chạy bằng tiến trình riêng, không phụ thuộc Docker daemon.

Phép đo chính yêu cầu tối thiểu bốn CPU hiệu dụng, 8 GiB RAM khả dụng và 4 GiB đĩa trống. Runner dùng chung tập tối đa bốn CPU cho toàn bộ cây tiến trình thí nghiệm. Nếu điều kiện không đạt hoặc không chuẩn bị được đúng PostgreSQL/Redis, phép đo dừng; không thay bằng SQLite hoặc cache trong bộ nhớ.

Không thay source, dependency, giới hạn CPU hoặc cấu hình notebook khi ma trận đang chạy. Runner kiểm tra fingerprint source và môi trường trước từng lượt. Không ghép các lượt từ những phiên Kaggle khác nhau thành một ma trận chính.

Kaggle có thể cung cấp CPU khác nhau giữa các phiên. Thông số thực tế của phiên được lưu trong manifest, thay vì giả định tên CPU cố định. Xem [tài liệu Kaggle](https://www.kaggle.com/docs/notebooks).

## Giao diện dòng lệnh

Các lệnh sau dùng Python của môi trường đã khóa:

```bash
python -m experiments.phase2.verify
python -m experiments.phase2.runner --profile full --dry-run
python -m experiments.phase2.runner --profile smoke --output-root /kaggle/working/phase2-results-smoke
python -m experiments.phase2.runner --profile full --output-root /kaggle/working/phase2-results-full
python -m experiments.phase2.report /kaggle/working/phase2-results-full
```

`--dry-run` chỉ xuất ma trận, không khởi động dịch vụ. Thư mục kết quả phải chưa tồn tại và nằm ngoài repository. Không ghi đè hoặc tự xóa kết quả cũ.

### Kiểm tra triển khai trên máy phát triển

Khởi chạy các dịch vụ riêng của bộ kiểm thử:

```bash
docker compose -p cinema-phase2-test -f experiments/phase2/compose.test.yml up -d --wait
```

Thiết lập các biến môi trường sau cho lệnh kiểm chứng hoặc runner:

```bash
export PHASE2_ADMIN_URL=postgresql://phase2:phase2-local-test@127.0.0.1:35439/postgres
export PHASE2_REDIS_URL=redis://127.0.0.1:36389/0
.venv/bin/python -m experiments.phase2.verify
.venv/bin/python -m experiments.phase2.runner --profile smoke --validation-only --output-root /tmp/cinema-phase2-validation
.venv/bin/python -m experiments.phase2.report /tmp/cinema-phase2-validation
```

`--validation-only` chỉ cho phép smoke. Có thể thêm `--small-data` hoặc `--limit-runs N` để kiểm tra nhanh; các tùy chọn này bị từ chối trong thí nghiệm chính. Database/Redis bên ngoài chỉ được dùng ở chế độ validation và phải nằm trên loopback. Thông tin xác thực trên là dữ liệu riêng của compose kiểm thử, không dùng cho triển khai thực tế.

Dừng hạ tầng kiểm thử sau khi sử dụng:

```bash
docker compose -p cinema-phase2-test -f experiments/phase2/compose.test.yml down
```

Kết quả validation được đánh dấu `canonical=false`, `primary_complete=false`. Do PostgreSQL/Redis có thể nằm trong container ngoài cây tiến trình, các cột tài nguyên không quan sát được được để trống. Kết quả này chỉ kiểm tra pipeline, không thay thế số đo Kaggle.

## Dữ liệu và kịch bản

Bộ dữ liệu chuẩn dùng seed `20261025`: 2.000 người dùng, 250 phim, 50 phòng, 200 ghế mỗi phòng, 5.000 suất chiếu và 100.000 đơn nền, mỗi đơn một ghế. Thời điểm suất chiếu bắt đầu năm 2030 theo UTC.

Một database snapshot được tạo qua Alembic và seed, sau đó clone trước mỗi lượt. Fingerprint gồm số hàng và checksum nội dung từng bảng. Runner chỉ tạo/xóa database có prefix `cinema_phase2_`, thuộc owner ngẫu nhiên hiện tại và được chính runner đăng ký tạo. Các database nghiệp vụ không được reset.

| Kịch bản | Nội dung | Kết quả cần phân biệt |
|---|---|---|
| R1 | 20% danh sách phim, 40% chi tiết phim, 30% suất theo phim, 10% suất theo phim/ngày; tập nóng 50 phim | Phản hồi đọc 200 |
| R2 | Mỗi request đặt một ghế thuộc phân vùng riêng | Vé thành công 201; 409 ngoài dự kiến |
| R3 | Tất cả người dùng tranh một ghế theo vòng; mỗi vòng dùng ghế mới | Một 201 và các 409 khi không có lỗi hạ tầng |
| R4 | Chu kỳ bốn request đọc và một request đặt ghế riêng | Độ trễ đọc và ghi thống kê riêng |

Full gồm bốn biến thể × bốn kịch bản × ba mức concurrency 10/50/100 × ba lần lặp. Thứ tự biến thể được xáo trộn có seed trong mỗi khối cùng kịch bản, mức tải và lần lặp.

Sau khi spawn đủ người dùng, mỗi lượt full có 15 giây warm-up, 45 giây đo và tối đa 10 giây drain. R1/R4 có bước prime cùng một tập endpoint trước warm-up. Database và cache đều được chuẩn bị lại cho mỗi lượt. Tổng thời gian phát tải tối đa khoảng 2 giờ 48 phút; thời gian khởi động, clone và kiểm tra dữ liệu được ghi riêng, nên tổng dự kiến là 3–4 giờ.

Locust dùng `FastHttpUser` để giảm CPU của bộ tạo tải. Đây là mô hình tải đóng, không có thời gian nghỉ chủ động. Concurrency không phải RPS cố định. Nếu bộ tạo tải dùng từ 90% một CPU trong ít nhất 20% các mẫu đo, lượt bị đánh dấu không hợp lệ.

## Chính sách cache và cấu hình ứng dụng

Cache chỉ áp dụng cho danh mục phim và suất chiếu; không cache ghế, đơn vé hoặc người dùng. Key phân biệt toàn bộ bộ lọc và có namespace riêng cho mỗi lượt. TTL 120 giây; Redis giới hạn 128 MB với `allkeys-lru`.

Redis lỗi, timeout hoặc chứa payload hỏng dẫn tới truy vấn PostgreSQL. Client không retry ngầm. Không cache 404 hoặc lỗi database. Chưa có cơ chế single-flight chống nhiều request cùng nạp lại key; các kết quả chính là kết quả sau warm-up, không đại diện cho cold-start hoặc cache stampede.

| Biến môi trường | Mặc định ứng dụng | Mục đích |
|---|---|---|
| `CATALOG_CACHE_ENABLED` | `false` | Bật Redis cache-aside |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Địa chỉ cache |
| `REDIS_TIMEOUT` | `0.1` | Timeout kết nối/đọc, tính bằng giây |
| `CATALOG_CACHE_NAMESPACE` | `default` | Phân vùng key |
| `CATALOG_CACHE_TTL` | `120` | TTL tính bằng giây |
| `DB_POOL_SIZE` | `5` | Pool mỗi process |
| `DB_MAX_OVERFLOW` | `10` | Kết nối vượt pool mỗi process |
| `DB_POOL_TIMEOUT` | `30` | Thời gian chờ lấy kết nối |
| `METRICS_ENABLED` | `false` | Bật endpoint metrics |

Các profile thí nghiệm ghi đè ngân sách pool theo bảng A/B/C/D. Không cần Redis khi cache tắt. Số worker được cấu hình bằng tham số Uvicorn.

`GET /health` giữ hành vi hiện tại. `GET /ready` kiểm tra PostgreSQL bằng `SELECT 1`, trả 200 hoặc 503 và không tiết lộ nội dung lỗi kết nối. Redis hỏng không làm mất readiness vì có fallback. `GET /metrics` trả 404 khi bị tắt.

Metrics dùng route mẫu như `/movies/{movie_id}`, không dùng ID thực tế hoặc token làm nhãn. Trong cấu hình nhiều worker, `PROMETHEUS_MULTIPROC_DIR` được thiết lập trước khi Python import ứng dụng và luôn là thư mục mới.

## Đầu ra và cách đánh giá

Thư mục kết quả chứa:

- `experiment.json`: phiên chạy, profile, ma trận và trạng thái nguồn đo.
- `environment.json`, `requirements.freeze.txt`: tài nguyên, phiên bản dependency và fingerprint môi trường.
- `source.tar.gz`, `source-manifest.json`: mã nguồn thực tế, gồm cả tệp chưa commit cần cho thí nghiệm.
- `dataset.json`, `snapshot.json`: cấu hình seed, danh sách allocation và fingerprint database.
- Mỗi lượt: spec, state, result, load log, API log, metrics trước/sau và CSV tài nguyên.
- Sau tổng hợp: `runs.csv`, `summary.csv`, `comparisons.csv`, `summary.json`, `report.md`, biểu đồ throughput/latency PNG và SVG.
- `resources.png` và `resources.svg`: CPU và tổng RSS theo thời gian cho từng thành phần, bao gồm cả lượt không hợp lệ.

Token và bí mật ký chỉ được chuyển qua bộ nhớ/biến môi trường của tiến trình; không xuất vào manifest hoặc kết quả.

So sánh B/A và D/C để xem tác động cache; C/A và D/B để xem tác động worker; D/A để xem hiệu quả kết hợp. Mỗi nhóm báo cáo median và min–max của ba lần lặp. Không suy luận ý nghĩa thống kê từ riêng ba số đo.

Throughput tính theo request hoàn thành trong cửa sổ đo. Phân bố latency gồm request bắt đầu trong cửa sổ và được thu tới hết drain. SQL/request và hit ratio lấy từ khoảng quiescent sau warm-up đến hết drain; khoảng này có thể bao gồm phần hoàn tất vòng R3 ở ranh giới cửa sổ.

SQL/request đếm các statement ứng dụng đi qua sự kiện SQLAlchemy; không bao gồm lệnh nội bộ như pool pre-ping, BEGIN/COMMIT của driver hoặc truy vấn từ bộ quan sát.

Hit ratio tính trên các lần đọc cache, gồm hit, miss và lỗi đọc. Lỗi ghi cache được cộng vào tổng lỗi cache nhưng không được tính thêm như một lần đọc thất bại.

409 hợp lệ ở R3 không tính là lỗi hệ thống và không tính vào successful booking/s. Timeout luôn nằm trong mẫu số tỷ lệ lỗi. Đơn commit nhưng không được client xác nhận được ghi riêng; không tự retry request đặt vé để che kết quả chưa xác định.

Ngưỡng tham chiếu: p95 đọc ≤ 500 ms, p95 đặt ghế riêng ≤ 1.000 ms, lỗi ngoài dự kiến ≤ 1%, không vi phạm tính đúng đắn. Đây là ngưỡng đánh giá đề xuất, không phải SLA production.

CPU được tính theo một CPU logic nên tổng có thể lớn hơn 100%. Bộ nhớ là tổng RSS theo cây tiến trình, có thể tính lặp vùng nhớ dùng chung; giá trị peak chỉ là đỉnh quan sát theo mẫu một giây.

Chỉ `primary_complete=true` khi có đủ 144 lượt hợp lệ của profile full trên nguồn đo chính. Lượt hạ tầng lỗi, source thay đổi, sampler lỗi, generator bão hòa hoặc worker thay đổi được giữ trong dữ liệu gốc, không dùng để vẽ so sánh. Không lựa chọn các lượt đẹp để thay thế lượt lỗi.

Lỗi dịch vụ do runner sở hữu trong warm-up, đo hoặc drain đều được ghi nhận. Kết quả lỗi được lưu trước cleanup; nếu cleanup database hoặc process group thất bại, lỗi cleanup được lưu riêng và thí nghiệm không được đánh dấu hoàn tất. Nhóm tiến trình được thu dọn cả khi tiến trình cha đã thoát.

Thao tác ngắt ô notebook được chuyển tiếp tới process group của runner để thực hiện cleanup. Sau khi ngắt có thể chạy công cụ report trên thư mục đã tạo để xem phần kết quả còn lại. Tắt cưỡng bức runtime không bảo đảm chạy được các khối cleanup; thư mục trạng thái chưa hoàn tất không được dùng như một phép đo đầy đủ.

Nếu 100 người dùng chưa gây bão hòa, kết luận chỉ có giá trị trong dải đo. Phép đo trên một máy không chứng minh horizontal scaling nhiều máy, độ trễ Internet, khả năng chịu lỗi máy chủ hoặc tính sẵn sàng cao.

Repository cung cấp pipeline và kiểm thử; kết luận hiệu năng Pha 2 phải dựa trên các artifact Kaggle thực tế được tạo sau khi chạy notebook.
