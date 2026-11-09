# Pha 2: giải thích kiến trúc và đánh giá backend trên Kaggle CPU

## Pha 2 giải quyết bài toán gì?

Backend ban đầu đã xử lý đăng ký, đăng nhập, xem phim, xem suất chiếu, đặt vé và hủy vé. Backend được chia thành các tầng API, application, domain và infrastructure; PostgreSQL lưu dữ liệu và dùng ràng buộc duy nhất để ngăn hai đơn cùng chiếm một ghế của một suất chiếu.

Việc luồng nghiệp vụ chạy đúng chưa cho biết hệ thống xử lý được bao nhiêu yêu cầu, chậm ở đâu hoặc dùng bao nhiêu CPU/RAM. Pha 2 bổ sung hai phương án cải tiến có thể đo được:

1. **Cache danh mục bằng Redis:** giảm việc đọc lại cùng dữ liệu phim và suất chiếu từ PostgreSQL.
2. **Chạy hai worker API:** cho phép hai tiến trình backend cùng xử lý yêu cầu trên tài nguyên CPU được cấp.

Kết hợp hai lựa chọn này tạo ra bốn cấu hình A/B/C/D. Chúng là bốn biến thể của cùng backend, được chạy lần lượt để so sánh; không phải bốn chức năng hoặc bốn hệ thống có nghiệp vụ khác nhau.

Mục tiêu là xác định phương án phù hợp với từng loại tải: xem danh mục, đặt các ghế khác nhau, tranh cùng một ghế và tải kết hợp đọc/ghi. Các đại lượng cần so sánh gồm tốc độ hoàn thành yêu cầu, độ trễ, lỗi, số truy vấn SQL và CPU/RAM.

Nghiệp vụ đặt/hủy vé, SQL, schema PostgreSQL và request/response của API được giữ nguyên trong phép so sánh chính. Pha này chưa bổ sung giữ ghế có thời hạn, thanh toán, gửi email, QR hoặc idempotency.

## Thuật ngữ cần biết

| Thuật ngữ | Ý nghĩa trong hệ thống |
|---|---|
| Worker API | Một tiến trình Python chạy ứng dụng FastAPI qua Uvicorn. Hai worker cùng chạy mã backend và truy cập PostgreSQL chung. |
| Cache | Bản sao dữ liệu để đọc nhanh. Trong Pha 2, Redis chỉ giữ bản sao danh mục; PostgreSQL vẫn lưu dữ liệu chính. |
| Cache hit / miss | Hit: tìm thấy kết quả hợp lệ trong Redis. Miss: chưa có kết quả và phải đọc PostgreSQL. |
| Cache-aside | Ứng dụng tự kiểm tra cache; nếu thiếu thì đọc database, lưu kết quả vào cache và trả cho client. |
| TTL | Thời gian một bản ghi cache được phép tồn tại. TTL hiện tại là 120 giây. |
| Connection pool | Nhóm kết nối database được tái sử dụng. Mỗi worker có pool riêng, nên phải tính tổng kết nối của tất cả worker. |
| Throughput / RPS | Số yêu cầu hoàn thành mỗi giây. Khi đo đặt vé, số vé đặt thành công được thống kê riêng. |
| p95 latency | Mốc độ trễ mà 95% request trong nhóm có thời gian không vượt quá. Ví dụ, p95 = 300 ms nghĩa là 95% request mất tối đa khoảng 300 ms. |
| Concurrency | Số người dùng ảo hoạt động đồng thời. 100 người dùng đồng thời không đồng nghĩa 100 request mỗi giây. |
| Baseline | Cấu hình mốc để so sánh các phương án cải tiến. |
| Metrics | Các thông số đo hoặc đếm của hệ thống, chẳng hạn số request, độ trễ và số truy vấn. |
| Snapshot | Bản trạng thái database dùng để tạo lại cùng dữ liệu trước mỗi lượt đo. |
| Fingerprint | Dấu kiểm tra dùng để phát hiện source, môi trường hoặc dữ liệu đã thay đổi. |
| Warm-up | Giai đoạn làm nóng trước cửa sổ đo, giúp giảm ảnh hưởng của khởi động và lần truy cập đầu. |
| Drain | Giai đoạn ngừng phát request mới và chờ các request đang chạy kết thúc. |

Một worker vẫn có thể xử lý nhiều request đồng thời. Tăng worker không có nghĩa tăng throughput theo đúng tỷ lệ, vì các worker còn chia sẻ CPU, PostgreSQL và các tài nguyên khác.

## A/B/C/D là những kiến trúc nào?

| Ký hiệu | Tên cấu hình | Worker | Redis cache | Thay đổi cần đánh giá |
|---|---|---:|---|---|
| **A** | Backend một worker, không cache — baseline | 1 | Tắt | Hiệu năng của kiến trúc mốc |
| **B** | Backend một worker với Redis cache-aside | 1 | Bật | Tác động của cache so với A |
| **C** | Backend hai worker, không cache | 2 | Tắt | Tác động của số worker so với A |
| **D** | Backend hai worker với Redis cache-aside | 2 | Bật | Tác động khi kết hợp hai phương án |

### A — Một worker và PostgreSQL: cấu hình mốc

```mermaid
flowchart LR
    Client[Client hoặc bộ tạo tải] --> API[Một worker FastAPI]
    API --> PG[(PostgreSQL)]
```

Khi nhận `GET /movies/1`, service đọc phim từ PostgreSQL rồi trả kết quả. Khi client khác yêu cầu cùng phim, service tiếp tục truy vấn PostgreSQL. Với `POST /bookings`, backend kiểm tra dữ liệu và tạo đơn trong transaction như nghiệp vụ hiện có.

A không dùng Redis. Cấu hình này cung cấp mốc để xác định các biến thể sau có giảm truy vấn, giảm độ trễ hoặc tăng throughput hay không.

A dùng mã nghiệp vụ và truy vấn hiện có, nhưng có cấu hình đo, connection pool và cơ chế thu thập metrics chung với các biến thể khác. Vì vậy, kết quả A là baseline của thí nghiệm chuẩn hóa, không phải số đo đã có từ một triển khai production trước đó.

### B — Một worker, Redis và PostgreSQL: giảm đọc lặp

```mermaid
flowchart LR
    Client[Client hoặc bộ tạo tải] --> API[Một worker FastAPI]
    API -->|Kiểm tra bản sao danh mục| Redis[(Redis)]
    API -->|Cache miss hoặc lỗi cache| PG[(PostgreSQL)]
```

Ví dụ hai lần đọc cùng một phim:

1. Lần đầu: Redis chưa có phim → service đọc PostgreSQL → lưu bản sao vào Redis với TTL 120 giây → trả kết quả.
2. Lần tiếp theo khi bản sao còn hạn: service lấy phim từ Redis → trả kết quả mà không truy vấn repository phim.
3. Khi bản sao hết hạn hoặc payload hỏng: service đọc lại PostgreSQL. Nếu Redis không truy cập được, service vẫn có đường đọc từ PostgreSQL.

`CatalogService` điều phối luồng này qua interface `CatalogCache`; `RedisCatalogCache` thực hiện thao tác Redis và mã hóa/khôi phục dữ liệu. Phần điều phối nghiệp vụ không import trực tiếp thư viện Redis.

**Lý do lựa chọn:** nhiều lượt xem có thể yêu cầu cùng một danh mục phim hoặc lịch chiếu. Cache có thể giảm số truy vấn database trong trường hợp này.

**Đánh đổi:** cần thêm bộ nhớ và một dịch vụ Redis; dữ liệu danh mục có thể cũ trong thời gian TTL. Cache không loại bỏ chi phí xử lý và tạo JSON của API, nên giảm SQL chưa đủ để kết luận toàn bộ request sẽ nhanh hơn.

### C — Hai worker và PostgreSQL: tận dụng khả năng xử lý của CPU

```mermaid
flowchart LR
    Client[Client hoặc bộ tạo tải] --> Listener[Cổng HTTP do Uvicorn quản lý]
    Listener --> W1[Worker FastAPI 1]
    Listener --> W2[Worker FastAPI 2]
    W1 --> PG[(PostgreSQL chung)]
    W2 --> PG
```

Uvicorn chạy hai tiến trình trên cùng cổng HTTP. Mỗi worker có instance ứng dụng và pool kết nối riêng; các request được phục vụ bởi những tiến trình này, không được chạy hai lần để tạo hai kết quả.

C không dùng Redis. Cả hai worker đọc và ghi vào cùng PostgreSQL. Đơn được tạo qua worker thứ nhất có thể được đọc qua worker thứ hai sau khi transaction đã commit. Ràng buộc duy nhất trong PostgreSQL vẫn là cơ chế bảo vệ ghế khi hai worker nhận yêu cầu trùng nhau.

Trạng thái đơn không được lưu riêng trong bộ nhớ của một worker làm nguồn dữ liệu chính. Các worker dùng cùng cấu hình xác thực JWT và database chung, nên request tiếp theo không cần quay về đúng worker đã tạo đơn.

**Lý do lựa chọn:** một tiến trình API có thể trở thành giới hạn khi CPU xử lý request bão hòa. Hai tiến trình có thể sử dụng CPU hiệu quả hơn nếu vẫn còn tài nguyên.

**Đánh đổi:** thêm chi phí bộ nhớ cho tiến trình, tăng lượng công việc có thể đổ xuống database và có thể làm tranh chấp tăng lên. Nếu giới hạn nằm ở database hoặc tổng CPU đã hết, thêm worker có thể không cải thiện kết quả.

Đây là cấu hình nhiều tiến trình trên một máy. Phép đo này chưa kiểm chứng mở rộng sang nhiều máy chủ hoặc khả năng phục vụ khi một máy bị hỏng.

### D — Hai worker, Redis và PostgreSQL: kết hợp hai phương án

```mermaid
flowchart LR
    Client[Client hoặc bộ tạo tải] --> Listener[Cổng HTTP do Uvicorn quản lý]
    Listener --> W1[Worker FastAPI 1]
    Listener --> W2[Worker FastAPI 2]
    W1 -->|Cache danh mục| Redis[(Redis chung)]
    W2 -->|Cache danh mục| Redis
    W1 -->|Cache miss hoặc đặt vé| PG[(PostgreSQL chung)]
    W2 -->|Cache miss hoặc đặt vé| PG
```

Hai worker dùng chung Redis và PostgreSQL. Một worker có thể đọc bản sao danh mục do worker còn lại đã lưu vào Redis. Khi đặt vé, cả hai vẫn đi qua transaction và ràng buộc ghế tại PostgreSQL.

**Lý do lựa chọn:** kiểm tra xem việc giảm tải đọc database và tăng khả năng xử lý phía API có hỗ trợ nhau hay không.

**Đánh đổi:** cùng chịu chi phí bộ nhớ và vận hành của Redis lẫn nhiều worker. D không mặc nhiên tốt nhất; khi tải chủ yếu là đặt vé, cache danh mục có thể ít tác dụng. Với giới hạn CPU cố định, các tiến trình bổ sung cũng phải chia sẻ tài nguyên với PostgreSQL và bộ tạo tải.

### Vì sao trạng thái ghế không đi qua Redis?

Ví dụ ghế A1 vừa được đặt thành công nhưng một bản sao cache vẫn ghi ghế trống. Nếu dùng bản sao đó làm căn cứ quyết định đặt vé, hệ thống có thể đưa ra quyết định sai.

Trong phạm vi hiện tại, các API ghế và booking tiếp tục đọc/ghi PostgreSQL. Redis chỉ phục vụ danh mục phim và suất chiếu. Ràng buộc `UNIQUE(showtime_id, seat_id)` và transaction tại PostgreSQL quyết định request đặt ghế nào thành công; Redis không đóng vai trò khóa ghế.

### Vì sao giữ tổng ngân sách kết nối bằng nhau?

| Biến thể | Pool mỗi worker | Số worker | Overflow | Tổng tối đa của API |
|---|---:|---:|---:|---:|
| A/B | 8 | 1 | 0 | 8 |
| C/D | 4 | 2 | 0 | 8 |

Nếu một worker được tám kết nối còn hai worker được mười sáu kết nối, phép so sánh sẽ đồng thời thay đổi số worker và tài nguyên database. Cấu hình hiện tại giữ tổng ở tám để tách tác động của worker rõ hơn. Overflow là số kết nối được phép mở vượt pool; giá trị 0 ngăn việc vượt ngân sách này. Pool timeout là 3 giây; kết nối quan sát và quản trị được ghi nhận riêng.

## Pha 2 đã bổ sung những thành phần nào?

| Thành phần | Nội dung đã triển khai | Vai trò trong đánh giá |
|---|---|---|
| Cache danh mục | Interface `CatalogCache`, adapter Redis, TTL, key theo bộ lọc, khôi phục kiểu dữ liệu và fallback | Thực hiện biến thể B/D và đo tác động giảm đọc database |
| Cấu hình worker và pool | Runner khởi chạy một hoặc hai worker; tổng pool API luôn là tám | Thực hiện A/B/C/D trên ngân sách tài nguyên chung |
| Kiểm tra khả năng phục vụ | `GET /ready` truy vấn kiểm tra PostgreSQL | Chỉ bắt đầu phát tải khi API sẵn sàng |
| Quan sát ứng dụng | Metrics request, thời gian xử lý, SQL, pool, cache và từng worker; hỗ trợ nhiều process | Xác định tác động của cải tiến và dấu hiệu bão hòa |
| Dữ liệu tái lập | Bộ dữ liệu có seed, manifest ghế, snapshot PostgreSQL và fingerprint | Bắt đầu các lượt từ cùng trạng thái |
| Bộ phát tải | Locust với bốn kịch bản R1/R2/R3/R4 | Đánh giá những hành vi sử dụng khác nhau |
| Runner thí nghiệm | Tạo ma trận, khởi chạy/dừng tiến trình, phục hồi dữ liệu, làm nóng, đo, drain và lưu kết quả | Tự động thực hiện phép so sánh có kiểm soát |
| Bảo vệ tính hợp lệ | Phát hiện thay đổi source/môi trường, dịch vụ chết, generator bão hòa, lỗi cleanup và sai lệch dữ liệu | Giữ bằng chứng lỗi và tránh kết luận từ lượt đo không hợp lệ |
| Môi trường Kaggle | Bootstrap, dependency lock và notebook điều phối | Chuẩn bị và chạy thí nghiệm trên CPU cố định |
| Công cụ báo cáo | CSV/JSON, bảng so sánh và biểu đồ throughput, latency, CPU/RAM | Cung cấp dữ liệu để phân tích và viết kết luận |

Các điểm nối chính trong mã nguồn:

- [CatalogService](../app/application/services/catalog_service.py) quyết định đọc cache hoặc repository; [CatalogCache](../app/application/ports/catalog_cache.py) định nghĩa hợp đồng cho cache.
- [RedisCatalogCache](../app/infrastructure/cache/catalog_cache.py) thực hiện hợp đồng bằng Redis; [app/main.py](../app/main.py) khởi tạo và nối dependency theo cấu hình.
- [observability.py](../app/infrastructure/observability.py) thu thập metrics phía API/database.
- [config.py](../experiments/phase2/config.py) định nghĩa A/B/C/D và ma trận; [runner.py](../experiments/phase2/runner.py) tổ chức từng lượt.
- [load.py](../experiments/phase2/load.py) phát request; [collect.py](../experiments/phase2/collect.py) lấy mẫu tài nguyên; [report.py](../experiments/phase2/report.py) tổng hợp kết quả.

## Phần nào đã được kiểm chứng, phần nào còn cần đo?

| Nội dung | Bằng chứng hiện có | Điều có thể kết luận |
|---|---|---|
| Chức năng và nhánh lỗi của phần triển khai | Đã ghi nhận 43 kiểm thử đạt, gồm PostgreSQL/Redis thật, cache fallback, tranh chấp hai worker và cleanup | Các trường hợp được kiểm thử hoạt động đúng trong môi trường kiểm chứng |
| Pipeline A/B/C/D | Đã chạy đủ 16 lượt smoke với dữ liệu chuẩn trong container cục bộ giới hạn 4 CPU/8 GB; các lượt đều hợp lệ | Runner, dữ liệu, dịch vụ và xuất kết quả hoạt động xuyên suốt trong lượt kiểm tra này |
| Chuẩn bị Kaggle | Có notebook và bootstrap; chưa có bằng chứng thực thi trực tiếp trong runtime Kaggle | Đã có công cụ chuẩn bị, chưa khẳng định cài đặt Kaggle đã được xác minh |
| Đánh giá hiệu năng Pha 2 | Chưa có ma trận full 144 lượt trên Kaggle CPU | Chưa xác định biến thể tốt nhất hoặc mức cải thiện trên phần cứng yêu cầu |

Smoke là phép kiểm tra ngắn xem bộ thí nghiệm có chạy được hay không. Full là phép đo chính với nhiều mức tải và ba lần lặp. Việc 16 lượt smoke đạt không có nghĩa hệ thống đã đáp ứng một SLA, chịu được một số người dùng production xác định hoặc hoàn tất đánh giá Pha 2.

Sau khi chạy full trên Kaggle, công cụ tự tạo bảng số liệu, các tỷ lệ so sánh và biểu đồ. Phần phân tích vẫn phải giải thích số liệu: cải thiện ở kịch bản nào, tài nguyên nào trở thành giới hạn, sai số giữa các lần lặp và chi phí đánh đổi. Công cụ không tự suy diễn một kết luận kiến trúc khi thiếu dữ liệu.

## Chuẩn bị mã nguồn

Chạy tại thư mục gốc repository:

```bash
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python --require-hashes -r experiments/phase2/requirements.lock.txt
.venv/bin/python -m experiments.phase2.bundle --output /tmp/cinema-phase2-source.tar.gz
```

Lệnh bundle đóng gói backend, migration, kiểm thử, dependency đã khóa và công cụ thí nghiệm. Không đóng gói `.env`, môi trường ảo, frontend hoặc dữ liệu kết quả. Đích bundle phải nằm ngoài repository và chưa tồn tại.

Đưa mã nguồn lên Kaggle theo hai đầu vào riêng:

1. Tạo Kaggle Dataset riêng và tải lên tệp `cinema-phase2-source.tar.gz` vừa đóng gói. Dataset này chứa backend sẽ được chạy.
2. Nhập tệp `experiments/phase2/kaggle_cpu.ipynb` vào Kaggle Notebook. Đây là notebook điều phối, không phải tệp backend cần giải nén thủ công.
3. Thêm Dataset ở bước 1 làm đầu vào của notebook. Chỉ gắn một bundle có tên `cinema-phase2-source.tar.gz`; ô đầu tiên sẽ tự tìm, kiểm tra checksum và giải nén.

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
| R1 — Đọc danh mục | 20% danh sách phim, 40% chi tiết phim, 30% suất theo phim, 10% suất theo phim/ngày; tập nóng 50 phim | Phản hồi đọc 200 |
| R2 — Đặt ghế khác nhau | Mỗi request đặt một ghế thuộc phân vùng riêng | Vé thành công 201; 409 ngoài dự kiến |
| R3 — Tranh cùng ghế | Tất cả người dùng tranh một ghế theo vòng; mỗi vòng dùng ghế mới | Một 201 và các 409 khi không có lỗi hạ tầng |
| R4 — Đọc và đặt vé | Chu kỳ bốn request đọc và một request đặt ghế riêng | Độ trễ đọc và ghi thống kê riêng |

Full gồm bốn biến thể × bốn kịch bản × ba mức concurrency 10/50/100 × ba lần lặp. Thứ tự biến thể được xáo trộn có seed trong mỗi khối cùng kịch bản, mức tải và lần lặp.

Sau khi tạo đủ người dùng ảo, mỗi lượt full có 15 giây warm-up, 45 giây đo và tối đa 10 giây drain. R1/R4 có bước gọi trước cùng một tập endpoint để làm nóng. Database và cache đều được chuẩn bị lại cho mỗi lượt. Tổng thời gian warm-up, đo và drain tối đa khoảng 2 giờ 48 phút; thời gian khởi động, clone và kiểm tra dữ liệu được ghi riêng, nên tổng dự kiến là 3–4 giờ.

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

Các cờ trong JSON có ý nghĩa khác nhau:

| Cờ | Ý nghĩa | Điều không được suy ra |
|---|---|---|
| `valid` của một lượt | Lượt đo vượt qua các kiểm tra tính hợp lệ của runner, tài nguyên và dữ liệu | Không chứng minh độ trễ hoặc tỷ lệ lỗi đã đạt ngưỡng chất lượng |
| `canonical` | Phép chạy dùng chế độ đo chính trên Kaggle và các dịch vụ cục bộ do runner quản lý | Không có nghĩa đã chạy đủ 144 lượt; smoke trên Kaggle cũng có thể mang cờ này |
| `primary_complete` | Có đủ ma trận full hợp lệ và không bị lỗi kết thúc/cleanup ngăn hoàn tất | Không khẳng định D tốt nhất hoặc hệ thống đã đạt SLA production |

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

Ví dụ cách lập luận sau khi có số liệu:

- Nếu B có ít SQL/request hơn A và p95 đọc thấp hơn trên cùng mức tải, số liệu hỗ trợ việc dùng cache cho bài toán đọc lặp. Cần báo cáo thêm hit ratio, CPU và bộ nhớ Redis để thấy chi phí đi kèm.
- Nếu C có throughput cao hơn A nhưng p95 ghi hoặc pool timeout tăng, cần kiểm tra database và thời gian chờ; không kết luận thêm worker luôn tốt.
- Nếu D không cải thiện R2/R3 so với C, đây có thể là kết quả phù hợp với thiết kế: cache danh mục không tham gia quyết định đặt ghế.
- Nếu ba lần lặp chênh lệch lớn hoặc bộ tạo tải bão hòa, chưa đủ cơ sở xếp hạng các biến thể từ một con số trung bình.

Các nhận định trên là cách đọc kết quả, không phải kết luận đã được xác nhận. Số liệu thực tế quyết định có giữ hay bác bỏ từng giả thuyết.

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
