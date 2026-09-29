import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Film,
  UserPlus,
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";

import { register } from "../api/authApi";
import { getApiErrorMessage } from "../api/errors";

export function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Mật khẩu cần tối thiểu 8 ký tự.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register({ email, password, full_name: fullName });
      navigate("/login", {
        replace: true,
        state: { message: "Đăng ký thành công! Hãy đăng nhập để trải nghiệm đặt vé." },
      });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể đăng ký tài khoản. Email này có thể đã được sử dụng."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-page-v2">
      <div className="auth-card-v2">
        <div className="auth-header">
          <div className="auth-brand-logo">
            <Film size={26} />
          </div>
          <h1 className="auth-title">Đăng ký tài khoản</h1>
          <p className="auth-subtitle">
            Trở thành thành viên CineVerse để tận hưởng dịch vụ đặt vé phim nhanh chóng và tiện lợi.
          </p>
        </div>

        {error ? (
          <div className="alert alert--error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="reg-name">Họ và tên</label>
            <div className="input-group">
              <span className="input-icon">
                <User size={18} />
              </span>
              <input
                id="reg-name"
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                autoComplete="name"
                placeholder="Nguyễn Văn A"
                required
              />
            </div>
          </div>

          <div className="form-field">
            <label htmlFor="reg-email">Email</label>
            <div className="input-group">
              <span className="input-icon">
                <Mail size={18} />
              </span>
              <input
                id="reg-email"
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
            <label htmlFor="reg-password">Mật khẩu (ít nhất 8 ký tự)</label>
            <div className="input-group">
              <span className="input-icon">
                <Lock size={18} />
              </span>
              <input
                id="reg-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
                minLength={8}
                placeholder="••••••••"
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

          <div className="form-field">
            <label htmlFor="reg-confirm">Xác nhận mật khẩu</label>
            <div className="input-group">
              <span className="input-icon">
                <ShieldCheck size={18} />
              </span>
              <input
                id="reg-confirm"
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                minLength={8}
                placeholder="Nhập lại mật khẩu"
                required
              />
            </div>
          </div>

          <button
            className="button button--wide button--glow button--large"
            type="submit"
            disabled={isSubmitting}
          >
            <UserPlus size={18} />
            <span>{isSubmitting ? "Đang tạo tài khoản..." : "Hoàn tất đăng ký"}</span>
          </button>
        </form>

        <footer className="auth-card-footer">
          <span>Đã có tài khoản? </span>
          <Link to="/login" className="auth-link">
            Đăng nhập tại đây
          </Link>
        </footer>
      </div>
    </section>
  );
}
