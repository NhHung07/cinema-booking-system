import { Link } from "react-router-dom";
import { Film, Home, ArrowLeft } from "lucide-react";

export function NotFoundPage() {
  return (
    <section className="not-found-section">
      <div className="not-found-card">
        <div className="not-found-code">404</div>
        <Film size={48} className="not-found-icon" />
        <h2>Không tìm thấy trang yêu cầu</h2>
        <p className="muted">
          Đường dẫn bạn vừa truy cập không tồn tại hoặc đã được thay đổi.
        </p>
        <div className="not-found-actions">
          <Link className="button button--glow button--large" to="/movies">
            <Home size={18} />
            <span>Về trang chủ phim</span>
          </Link>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => window.history.back()}
          >
            <ArrowLeft size={16} />
            <span>Quay lại</span>
          </button>
        </div>
      </div>
    </section>
  );
}
