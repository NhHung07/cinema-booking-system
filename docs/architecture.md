# Kiến trúc hệ thống

## Hướng phụ thuộc

```text
FastAPI routes / dependencies
          ↓
Application services (use cases)
          ↓
Domain entities, repository interfaces, errors
          ↑
SQLAlchemy repository implementations và PostgreSQL
```

`infrastructure` triển khai các interface được định nghĩa ở `domain`; chúng được ghép nối trong API dependency/composition layer. Mũi tên không bao giờ đi từ `domain` hoặc `application` đến FastAPI hay SQLAlchemy.

## Các layer

| Layer | Chứa gì? | Vì sao cần? | Dependency được phép |
| --- | --- | --- | --- |
| `app/api` | Routes, FastAPI dependencies, chuyển đổi HTTP error | Giữ HTTP concern và Swagger annotation ở boundary | application, domain, infrastructure tại composition layer |
| `app/application` | `AuthService`, `CatalogService`, `BookingService`, Pydantic contract | Điều phối từng use case | Chỉ domain và core; không FastAPI hoặc SQLAlchemy |
| `app/domain` | Dataclass entity và abstract repository/unit-of-work interface | Diễn tả business concept không phụ thuộc framework | Chỉ Python standard library |
| `app/infrastructure` | ORM model, session factory, SQLAlchemy repository | Adapter từ interface sang PostgreSQL | domain, core, SQLAlchemy |
| `app/core` | Settings, password/JWT helper, application error | Chính sách kỹ thuật dùng chung | Package library; không FastAPI/SQLAlchemy |

## Request flow: tạo booking

```text
POST /bookings + Bearer JWT
  → get_current_user dependency decode JWT một lần
  → route parse BookingCreateRequest
  → BookingService.create_booking
  → UnitOfWork repository kiểm tra showtime và seat
  → SQLAlchemy repository insert Booking + BookingSeat trong một transaction
  → PostgreSQL UNIQUE(showtime_id, seat_id) chỉ chấp nhận một writer
  → API map SeatAlreadyBookedError thành HTTP 409
```

### Input và output

- Input: `user_id` đã authentication, `showtime_id`, và danh sách `seat_ids` không trùng lặp.
- Output khi thành công: `Booking` ở trạng thái confirmed, có identifier và các seat đã chọn.
- Output khi có request cạnh tranh: `SeatAlreadyBookedError`; chỉ API layer chuyển lỗi này thành `409 Conflict`.

## Chính sách cancellation

Khi cancel, hệ thống giữ row `bookings` với status `CANCELLED` để lưu lịch sử, sau đó xóa các row `booking_seats` của booking đó. Việc xóa allocation row giải phóng ghế nhưng lịch sử booking vẫn còn.

## Transaction boundary

`SQLAlchemyUnitOfWork` được cung cấp cho application service. Service sở hữu use case ở mức logic; adapter sở hữu `Session.commit()` / `rollback()`. Nếu unique constraint thất bại lúc thêm seat, adapter rollback và raise `SeatAlreadyBookedError`. Điều này đảm bảo không có booking dang dở được persist.
