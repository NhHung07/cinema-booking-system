# Tài liệu Ứng dụng Giao diện (Frontend Architecture & Guide)

Ứng dụng Frontend của **Cinema Booking System** là một Single Page Application (SPA) hiện đại được xây dựng bằng **React 18**, **Vite** và **TypeScript**, cung cấp trải nghiệm đặt vé xem phim trực quan và mượt mà.

---

## 🛠️ Ngăn xếp công nghệ (Tech Stack)

- **Framework & Core:** React 18, TypeScript, Vite (công cụ build siêu nhanh).
- **Routing:** React Router v6 với hỗ trợ route công khai và `ProtectedRoute`.
- **HTTP Client:** Axios với request & response interceptors tự động quản lý Bearer Token.
- **Biểu tượng (Icons):** Lucide React.
- **Styling:** CSS hiện đại, thiết kế Responsive thích ứng điện thoại và máy tính.
- **Containerization:** Docker đa tầng kết hợp với Nginx Alpine để phục vụ static bundle.

---

## 📂 Cấu trúc thư mục

```text
frontend/
├── src/
│   ├── api/                 # Tầng giao tiếp HTTP qua Axios
│   │   ├── client.ts        # Axios instance, cấu hình BaseURL & Interceptors
│   │   ├── authApi.ts       # Đăng ký & đăng nhập
│   │   ├── movieApi.ts      # Danh sách phim & chi tiết phim
│   │   ├── showtimeApi.ts   # Suất chiếu & ma trận ghế
│   │   └── bookingApi.ts    # Đặt vé, xem vé cá nhân & hủy vé
│   ├── components/          # Các UI components tái sử dụng
│   │   ├── Navbar.tsx       # Thanh điều hướng trên cùng, trạng thái user
│   │   ├── MovieCard.tsx    # Card hiển thị poster, tên và thời lượng phim
│   │   └── BookingTicketModal.tsx # Modal vé điện tử đẹp mắt sau khi đặt
│   ├── context/             # Quản lý State toàn cục
│   │   └── AuthContext.tsx  # Cung cấp token, user state, login & logout
│   ├── pages/               # Các trang giao diện chính
│   │   ├── MoviesPage.tsx        # Danh mục phim đang chiếu
│   │   ├── MovieDetailPage.tsx   # Thông tin chi tiết phim & danh sách suất
│   │   ├── ShowtimeSeatsPage.tsx # Sơ đồ chọn ghế rạp chiếu thời gian thực
│   │   ├── MyBookingsPage.tsx    # Danh sách vé của tôi & nút hủy vé
│   │   ├── LoginPage.tsx         # Trang đăng nhập
│   │   ├── RegisterPage.tsx      # Trang đăng ký tài khoản
│   │   └── NotFoundPage.tsx      # Trang 404
│   ├── routes/
│   │   └── ProtectedRoute.tsx    # Guard bảo vệ các trang yêu cầu đăng nhập
│   ├── types/               # TypeScript interfaces & types định nghĩa dữ liệu
│   ├── utils/               # Tiện ích bổ trợ (format ngày giờ, movie metadata)
│   ├── App.tsx              # Component gốc và cấu hình Router
│   ├── main.tsx             # Entrypoint gắn React vào DOM
│   └── styles.css           # Toàn bộ CSS hệ thống giao diện
├── index.html
├── nginx.conf               # Cấu hình Nginx phục vụ SPA trong Docker
├── package.json
└── vite.config.ts
```

---

## 🔑 Cơ chế xác thực & Axios Interceptors

1. **Quản lý Token:**
   - Khi đăng nhập thành công, access token được lưu trong `localStorage` để duy trì phiên làm việc khi người dùng tải lại trang.
   - Trạng thái `isAuthenticated` và thông tin phiên được phát cho toàn bộ ứng dụng qua `AuthContext`.

2. **Request Interceptor:**
   - Mọi request gửi đi từ `client.ts` tự động kiểm tra token trong `localStorage`. Nếu có, header sau sẽ được đính kèm:
     ```http
     Authorization: Bearer <access_token>
     ```

3. **Response Interceptor (Tự động thu hồi phiên):**
   - Khi nhận phản hồi `401 Unauthorized` từ backend (do token hết hạn hoặc giả mạo):
     - Xóa token khỏi `localStorage`.
     - Cập nhật lại state của `AuthContext`.
     - Điều hướng người dùng về trang `/login` một cách êm ái (tránh vòng lặp điều hướng nếu đang ở sẵn trang login).

---

## 🎟️ Luồng trải nghiệm người dùng (User Flow)

```text
Xem danh sách Phim (MoviesPage)
        ↓
Xem chi tiết phim & chọn ngày (MovieDetailPage)
        ↓
Xem sơ đồ ghế & chọn chỗ ngồi (ShowtimeSeatsPage)
        ↓
[Yêu cầu đăng nhập nếu chưa auth]
        ↓
Xác nhận đặt vé (Gọi POST /bookings)
  ├── Thành công (201): Hiển thị Modal Vé Điện Tử (BookingTicketModal)
  └── Trùng ghế (409 Conflict): Thông báo ghế vừa có người đặt, tự động refresh sơ đồ ghế
        ↓
Xem vé đã đặt và quản lý hủy vé (MyBookingsPage)
```

### Xử lý Race Condition & Xung đột ghế tại UI
- Giao diện chọn ghế liên tục phản ánh trạng thái từ `GET /showtimes/{id}/seats`.
- Khi người dùng bấm **Đặt vé**, nếu có một người dùng khác vừa nhanh tay đặt mất ghế đó trước trong tích tắc, Backend sẽ trả về `409 Conflict`.
- Frontend ngay lập tức hiển thị Toast / Banner cảnh báo thân thiện, đổi màu ghế đã bị chiếm và cập nhật lại danh sách ghế mà không làm crash ứng dụng.

---

## 🚀 Hướng dẫn khởi chạy Frontend

### 1. Khởi chạy ở môi trường phát triển (Dev Mode)

Yêu cầu Node.js 20 trở lên.

```bash
cd frontend

# Tạo file cấu hình môi trường
cp .env.example .env

# Cài đặt gói phụ thuộc
npm install

# Khởi chạy Vite dev server với Hot Reload
npm run dev
```

Ứng dụng sẽ hoạt động tại: **<http://localhost:5173>**  
File `.env` trỏ tới backend:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### 2. Biên dịch Production (Production Build)

```bash
npm run build
```
Toàn bộ source code được compile, tối ưu dung lượng và xuất vào thư mục `dist/`.

### 3. Phục vụ bằng Docker & Nginx

Frontend có thể chạy độc lập trong container Nginx nhẹ bằng file cấu hình `frontend/nginx.conf`:
- Lắng nghe cổng `5173`.
- Hỗ trợ routing cho SPA với directive `try_files $uri $uri/ /index.html;`.

---

> Trở về trang chính: [README.md](../README.md) | Xem mục lục tài liệu: [docs/README.md](./README.md)
