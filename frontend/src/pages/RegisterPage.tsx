import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { register } from "../api/authApi";
import { getApiErrorMessage } from "../api/errors";

export function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password cần có ít nhất 8 ký tự.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Confirm password chưa khớp.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register({ email, password, full_name: fullName });
      navigate("/login", {
        replace: true,
        state: { message: "Đăng ký thành công. Bạn có thể đăng nhập ngay." },
      });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể đăng ký tài khoản."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">Cinema Booking</p>
        <h1>Tạo tài khoản</h1>
        <p className="muted">Dùng tài khoản để đặt ghế cho suất chiếu bạn yêu thích.</p>
        {error ? <div className="alert alert--error">{error}</div> : null}
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Full name
            <input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              autoComplete="name"
              required
            />
          </label>
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
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <label>
            Confirm password
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <button className="button button--wide" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Đang tạo tài khoản..." : "Đăng ký"}
          </button>
        </form>
        <p className="auth-card__footer">
          Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
        </p>
      </div>
    </section>
  );
}
