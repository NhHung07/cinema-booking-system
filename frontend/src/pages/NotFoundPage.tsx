import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="empty-state">
      <h1>404</h1>
      <p>Không tìm thấy trang bạn yêu cầu.</p>
      <Link className="button button--small" to="/movies">
        Về danh sách phim
      </Link>
    </section>
  );
}
