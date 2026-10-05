# Đặc tả REST API (API Reference)

Tài liệu này cung cấp đặc tả kỹ thuật chi tiết cho toàn bộ các endpoints của **Cinema Booking System API**, bao gồm các tham số đầu vào, cấu trúc phản hồi, cơ chế xác thực và các mã lỗi tương ứng.

---

## 🔐 Cơ chế xác thực (Authentication)

- Hệ thống sử dụng giao thức **HTTP Bearer Authentication** kết hợp với **JWT (JSON Web Token)** được mã hóa bằng thuật toán `HS256`.
- Mật khẩu người dùng được băm bằng thuật toán **Argon2** an toàn cao, không bao giờ lưu trữ mật khẩu gốc dưới dạng plaintext.
- Đối với các protected routes, client cần đính kèm header:
  ```http
  Authorization: Bearer <access_token>
  ```
- Nếu token bị thiếu hoặc không hợp lệ, API trả về `401 Unauthorized` kèm header `WWW-Authenticate: Bearer`.

---

## 🚦 Quy ước phản hồi lỗi (Error Format)

Mọi phản hồi lỗi từ tầng ứng dụng đều tuân thủ cấu trúc JSON đồng nhất:

```json
{
  "detail": "Mô tả nguyên nhân lỗi cụ thể"
}
```

### Bảng mã trạng thái HTTP

| HTTP Code | Ý nghĩa | Kịch bản áp dụng |
| :--- | :--- | :--- |
| **`200 OK`** | Thành công | Yêu cầu đọc hoặc thao tác thành công. |
| **`201 Created`** | Tạo mới thành công | Đăng ký tài khoản hoặc đặt vé thành công. |
| **`400 Bad Request`** | Dữ liệu không hợp lệ | Vi phạm logic đầu vào hoặc cấu trúc request. |
| **`401 Unauthorized`** | Chưa xác thực | Thiếu token, token sai hoặc token đã hết hạn. |
| **`403 Forbidden`** | Không có quyền | Cố gắng xem/hủy đơn đặt vé của người dùng khác. |
| **`404 Not Found`** | Không tìm thấy | Không tồn tại Phim, Suất chiếu, Ghế hoặc Vé. |
| **`409 Conflict`** | Xung đột tài nguyên | Email đã tồn tại khi đăng ký; hoặc **ghế đã bị người khác đặt**. |
| **`422 Unprocessable Entity`** | Thực thể không hợp lệ | Đặt vé không có ghế, ghế không thuộc phòng chiếu của suất đó. |

---

## 📡 Danh sách Endpoints chi tiết

### 1. Hệ thống (System)

#### `GET /health`
- **Mô tả:** Kiểm tra trạng thái hoạt động của API service.
- **Yêu cầu xác thực:** Không.
- **Phản hồi thành công (`200 OK`):**
  ```json
  {
    "status": "ok"
  }
  ```

---

### 2. Xác thực tài khoản (Authentication)

#### `POST /auth/register`
- **Mô tả:** Đăng ký tài khoản người dùng mới.
- **Yêu cầu xác thực:** Không.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123",
    "full_name": "Nguyễn Văn A"
  }
  ```
- **Phản hồi thành công (`201 Created`):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Nguyễn Văn A",
    "created_at": "2026-10-05T12:00:00Z"
  }
  ```
- **Lỗi thường gặp:** `409 Conflict` nếu email đã được đăng ký.

#### `POST /auth/login`
- **Mô tả:** Đăng nhập và nhận JWT access token.
- **Yêu cầu xác thực:** Không.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123"
  }
  ```
- **Phản hồi thành công (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer"
  }
  ```
- **Lỗi thường gặp:** `401 Unauthorized` nếu sai email hoặc mật khẩu.

---

### 3. Danh mục Phim (Movies)

#### `GET /movies`
- **Mô tả:** Lấy danh sách toàn bộ các bộ phim đang và sắp chiếu.
- **Yêu cầu xác thực:** Không.
- **Phản hồi thành công (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "title": "Inception",
      "description": "A thief who steals corporate secrets through the use of dream-sharing technology...",
      "duration_minutes": 148,
      "release_date": "2010-07-16"
    }
  ]
  ```

#### `GET /movies/{id}`
- **Mô tả:** Lấy thông tin chi tiết một bộ phim cụ thể theo ID.
- **Yêu cầu xác thực:** Không.
- **Phản hồi thành công (`200 OK`):** Đối tượng `Movie` tương tự trên.
- **Lỗi thường gặp:** `404 Not Found` nếu không tìm thấy phim.

---

### 4. Suất chiếu & Sơ đồ Ghế (Showtimes & Seats)

#### `GET /showtimes`
- **Mô tả:** Lấy danh sách các suất chiếu, hỗ trợ lọc theo phim và ngày chiếu.
- **Yêu cầu xác thực:** Không.
- **Query Parameters:**
  - `movie_id` *(int, tùy chọn)*: Lọc theo mã phim.
  - `date` *(string định dạng YYYY-MM-DD, tùy chọn)*: Lọc theo ngày chiếu.
- **Phản hồi thành công (`200 OK`):**
  ```json
  [
    {
      "id": 10,
      "movie_id": 1,
      "start_time": "2026-10-06T19:30:00Z",
      "room_name": "Cinema Hall 1"
    }
  ]
  ```

#### `GET /showtimes/{id}/seats`
- **Mô tả:** Lấy sơ đồ ghế và trạng thái khả dụng thời gian thực của suất chiếu.
- **Yêu cầu xác thực:** Không.
- **Phản hồi thành công (`200 OK`):**
  ```json
  {
    "showtime_id": 10,
    "room_name": "Cinema Hall 1",
    "seats": [
      {
        "id": 101,
        "row": "A",
        "number": 1,
        "is_available": true
      },
      {
        "id": 102,
        "row": "A",
        "number": 2,
        "is_available": false
      }
    ]
  }
  ```

---

### 5. Đặt vé & Quản lý vé (Bookings)

#### `POST /bookings`
- **Mô tả:** Thực hiện đặt vé cho các ghế được chọn trong một suất chiếu.
- **Yêu cầu xác thực:** **Bắt buộc** (`Bearer <token>`).
- **Request Body:**
  ```json
  {
    "showtime_id": 10,
    "seat_ids": [101, 103]
  }
  ```
- **Phản hồi thành công (`201 Created`):**
  ```json
  {
    "id": 501,
    "user_id": 1,
    "showtime_id": 10,
    "status": "CONFIRMED",
    "created_at": "2026-10-05T12:30:00Z",
    "seats": [
      { "id": 101, "row": "A", "number": 1 },
      { "id": 103, "row": "A", "number": 3 }
    ]
  }
  ```
- **Lỗi thường gặp:**
  - `409 Conflict`: Ghế đã có người khác đặt trong cùng thời điểm (xử lý race condition).
  - `422 Unprocessable Entity`: Danh sách `seat_ids` rỗng hoặc chứa ghế không thuộc phòng chiếu của suất này.

#### `GET /bookings/me`
- **Mô tả:** Lấy danh sách lịch sử tất cả các vé đã đặt của người dùng đang đăng nhập.
- **Yêu cầu xác thực:** **Bắt buộc** (`Bearer <token>`).
- **Phản hồi thành công (`200 OK`):** Danh sách các đối tượng booking.

#### `GET /bookings/{id}`
- **Mô tả:** Xem chi tiết một đơn đặt vé cụ thể.
- **Yêu cầu xác thực:** **Bắt buộc** (`Bearer <token>`).
- **Lỗi thường gặp:**
  - `403 Forbidden`: Người dùng không có quyền truy cập đơn vé của tài khoản khác.
  - `404 Not Found`: Không tìm thấy mã đơn vé.

#### `DELETE /bookings/{id}`
- **Mô tả:** Hủy vé đã đặt. Hệ thống sẽ giải phóng ghế để người khác có thể đặt, đồng thời cập nhật trạng thái đơn vé thành `CANCELLED`.
- **Yêu cầu xác thực:** **Bắt buộc** (`Bearer <token>`).
- **Phản hồi thành công (`200 OK`):**
  ```json
  {
    "id": 501,
    "status": "CANCELLED"
  }
  ```
- **Lỗi thường gặp:** `403 Forbidden` nếu không phải chủ sở hữu đơn vé.

---

> Trở về trang chính: [README.md](../README.md) | Xem mục lục tài liệu: [docs/README.md](./README.md)
