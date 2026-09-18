import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

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
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const token = await login({ email, password });
      saveToken(token.access_token);
      navigate(state?.from ?? "/movies", { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Đăng nhập không thành công."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">Cinema Booking</p>
        <h1>Đăng nhập</h1>
        <p className="muted">Đăng nhập để chọn ghế, đặt vé và quản lý booking của bạn.</p>
        {state?.message ? <div className="alert alert--success">{state.message}</div> : null}
        {error ? <div className="alert alert--error">{error}</div> : null}
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="button button--wide" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>
        <p className="auth-card__footer">
          Chưa có tài khoản? <Link to="/register">Đăng ký ngay</Link>
        </p>
      </div>
    </section>
  );
}
