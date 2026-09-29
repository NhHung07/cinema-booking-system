import { useState, type FormEvent } from "react";
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
} from "lucide-react";

import { login } from "../api/authApi";
import { getApiErrorMessage } from "../api/errors";
import { useAuth } from "../context/AuthContext";

interface LoginLocationState {
  from?: string;
  message?: string;
}

export function LoginPage() {
  const { login: saveToken } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LoginLocationState | null;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const token = await login({ email, password });
      saveToken(token.access_token, email);
      navigate(state?.from ?? "/movies", { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Đăng nhập không thành công. Vui lòng kiểm tra lại email và mật khẩu."));
    } finally {
      setIsSubmitting(false);
    }
  }

  function fillDemoAccount() {
    setEmail("demo@gmail.com");
    setPassword("password123");
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

          {/* Quick Demo Credentials */}
          <div className="demo-fill-box">
            <button
              type="button"
              className="demo-fill-btn"
              onClick={fillDemoAccount}
            >
              <Sparkles size={14} />
              <span>Điền tài khoản thử nghiệm (demo@gmail.com)</span>
            </button>
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
