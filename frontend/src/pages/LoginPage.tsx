import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Film,
  LogIn,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
  Sparkles,
  ShieldCheck,
  UserCheck,
} from "lucide-react";

import { getMe, login } from "../api/authApi";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../context/AuthContext";

interface LoginLocationState {
  from?: string;
  message?: string;
  email?: string;
}

export function LoginPage() {
  const { login: saveToken, isAuthenticated, isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LoginLocationState | null;

  const [email, setEmail] = useState(() => state?.email ?? "");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(state?.from ?? (isAdmin ? "/admin/movies/new" : "/movies"), { replace: true });
    }
  }, [isAuthenticated, isAdmin, navigate, state]);

  async function performLogin(loginEmail: string, loginPass: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      const token = await login({ email: loginEmail.trim(), password: loginPass });
      saveToken(token.access_token, loginEmail.trim(), token.role);

      try {
        const user = await getMe();
        if (user.full_name) {
          saveToken(token.access_token, user.email, user.role, user.full_name);
        }
      } catch {
        // Fallback silently if getMe fails
      }

      navigate(state?.from ?? "/movies", { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Đăng nhập không thành công. Vui lòng kiểm tra lại email và mật khẩu."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await performLogin(email, password);
  }

  async function handleQuickLogin(accountEmail: string, accountPass: string) {
    setEmail(accountEmail);
    setPassword(accountPass);
    await performLogin(accountEmail, accountPass);
  }

  function fillAccount(accountEmail: string, accountPass: string) {
    setEmail(accountEmail);
    setPassword(accountPass);
    setError(null);
  }

  return (
    <section className="auth-page-v2">
      <div className="auth-card-v2">
        <div className="auth-header">
          <div className="auth-brand-logo">
            <Film size={26} />
          </div>
          <h1 className="auth-title">Chào mừng trở lại!</h1>
          <p className="auth-subtitle">
            Đăng nhập vào CineVerse để chọn chỗ ngồi yêu thích và xem lịch sử vé.
          </p>
        </div>

        {state?.message ? (
          <div className="alert alert--success">
            <CheckCircle size={18} />
            <span>{state.message}</span>
          </div>
        ) : null}

        {error ? (
          <div className="alert alert--error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="login-email">Email</label>
            <div className="input-group">
              <span className="input-icon">
                <Mail size={18} />
              </span>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                placeholder="tenban@example.com"
                required
              />
            </div>
          </div>

          <div className="form-field">
            <label htmlFor="login-password">Mật khẩu</label>
            <div className="input-group">
              <span className="input-icon">
                <Lock size={18} />
              </span>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="Nhập mật khẩu của bạn"
                required
              />
              <button
                type="button"
                className="input-eye-btn"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button
            className="button button--wide button--glow button--large"
            type="submit"
            disabled={isSubmitting}
          >
            <LogIn size={18} />
            <span>{isSubmitting ? "Đang xác thực..." : "Đăng nhập ngay"}</span>
          </button>

          {/* Thông tin đăng nhập nhanh & tài khoản mẫu */}
          <div className="demo-fill-box" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
              <Sparkles size={14} color="var(--color-primary)" />
              <span>Đăng nhập nhanh một chạm bằng tài khoản mẫu:</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
              <button
                type="button"
                className="demo-fill-btn"
                onClick={() => void handleQuickLogin("admin@cinema.com", "admin123")}
                disabled={isSubmitting}
                style={{
                  borderColor: "rgba(225, 29, 72, 0.4)",
                  background: "rgba(225, 29, 72, 0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.4rem",
                  padding: "0.6rem 0.5rem",
                  borderRadius: "8px",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
                title="Đăng nhập ngay với vai trò Quản Trị Viên (Người khởi tạo)"
              >
                <ShieldCheck size={16} color="var(--color-primary)" />
                <span>Admin / Người khởi tạo</span>
              </button>

              <button
                type="button"
                className="demo-fill-btn"
                onClick={() => void handleQuickLogin("demo@gmail.com", "password123")}
                disabled={isSubmitting}
                style={{
                  borderColor: "rgba(56, 189, 248, 0.3)",
                  background: "rgba(56, 189, 248, 0.06)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.4rem",
                  padding: "0.6rem 0.5rem",
                  borderRadius: "8px",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
                title="Đăng nhập ngay với vai trò Khách hàng (Đặt vé)"
              >
                <UserCheck size={16} color="#38bdf8" />
                <span>Khách hàng / Đặt vé</span>
              </button>
            </div>

            <div style={{ display: "flex", justifyContent: "center", gap: "1rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
              <button
                type="button"
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", textDecoration: "underline" }}
                onClick={() => fillAccount("admin@cinema.com", "admin123")}
              >
                Điền Admin
              </button>
              <span>•</span>
              <button
                type="button"
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", textDecoration: "underline" }}
                onClick={() => fillAccount("demo@gmail.com", "password123")}
              >
                Điền Khách
              </button>
            </div>
          </div>
        </form>

        <footer className="auth-card-footer">
          <span>Chưa có tài khoản CineVerse? </span>
          <Link to="/register" className="auth-link">
            Đăng ký tài khoản mới
          </Link>
        </footer>
      </div>
    </section>
  );
}
