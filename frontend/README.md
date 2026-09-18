# Cinema Booking Frontend

Frontend MVP dùng React, Vite, TypeScript, React Router và Axios, kết nối trực tiếp với FastAPI backend ở thư mục cha.

## API integration

`src/api/` là API layer duy nhất gọi Axios:

| File | Endpoint backend |
| --- | --- |
| `authApi.ts` | `POST /auth/register`, `POST /auth/login` |
| `movieApi.ts` | `GET /movies`, `GET /movies/{movie_id}` |
| `showtimeApi.ts` | `GET /showtimes?movie_id=`, `GET /showtimes/{showtime_id}/seats` |
| `bookingApi.ts` | `POST /bookings`, `GET /bookings/me`, `DELETE /bookings/{booking_id}` |

Axios lấy `VITE_API_BASE_URL` từ environment, tự thêm `Authorization: Bearer <token>` qua request interceptor. Khi backend trả `401`, interceptor xóa token và redirect về `/login` (trừ khi đã ở trang login để tránh redirect loop).

## Authentication state

`AuthContext` lưu `token`, `isAuthenticated`, `login()` và `logout()`. Token được lưu trong `localStorage` để phù hợp MVP và vẫn tồn tại sau khi browser reload. Trong production, HttpOnly cookie cùng CSRF protection thường an toàn hơn vì JavaScript không đọc được token.

## Chạy frontend

Yêu cầu Node.js 20 trở lên.

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Trên macOS/Linux, thay `copy` bằng `cp`.

Frontend chạy mặc định ở <http://localhost:5173>. File `.env` cần có:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Chạy toàn hệ thống

Terminal 1 — backend, PostgreSQL và migration cần sẵn sàng trước:

```bash
uvicorn app.main:app --reload
```

Nếu database chưa có catalogue:

```bash
alembic upgrade head
python scripts/seed.py
```

Terminal 2 — frontend:

```bash
cd frontend
npm run dev
```

Mở <http://localhost:5173>. Swagger backend có tại <http://localhost:8000/docs>.

Backend cho phép origin `http://localhost:5173` qua `CORS_ALLOWED_ORIGINS`. Có thể cấu hình nhiều origin bằng chuỗi ngăn cách bởi dấu phẩy, ví dụ:

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## Build production

```bash
npm run build
```

Vite xuất static files vào `dist/`. Frontend hiện được ưu tiên chạy local để dễ phát triển và demo; Docker frontend có thể bổ sung sau khi cần deployment static files.

## Luồng sử dụng

```text
Register → Login → Movies → Movie Details → Showtimes → Seats
→ Select seats → Confirm Booking → My Bookings → Cancel Booking → Logout
```

Seat availability luôn lấy từ `GET /showtimes/{showtime_id}/seats`. Khi `POST /bookings` trả `409 Conflict`, UI tải lại ghế và báo rõ rằng ghế vừa được người khác đặt.
