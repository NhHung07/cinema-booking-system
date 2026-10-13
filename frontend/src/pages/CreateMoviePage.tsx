import { useState, useRef, type FormEvent, type ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Film,
  Clock,
  Calendar,
  FileText,
  ArrowLeft,
  PlusCircle,
  AlertCircle,
  Upload,
  Image as ImageIcon,
  Trash2,
  MapPin,
  Sparkles,
  CheckCircle2,
} from "lucide-react";

import { createMovie, uploadMovieImage } from "../api/movieApi";
import { createShowtime } from "../api/showtimeApi";
import { getApiErrorMessage } from "../api/errors";

export function CreateMoviePage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [durationMinutes, setDurationMinutes] = useState<number | "">(120);
  const [releaseDate, setReleaseDate] = useState(() => new Date().toISOString().split("T")[0]);

  // Quản lý ảnh của phim
  const [posterFile, setPosterFile] = useState<File | null>(null);
  const [posterPreview, setPosterPreview] = useState<string | null>(null);
  const [posterUrlInput, setPosterUrlInput] = useState("");
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  // Quản lý thêm suất chiếu đầu tiên
  const [addInitialShowtime, setAddInitialShowtime] = useState(true);
  const [roomName, setRoomName] = useState("ROOM_1");
  const [showtimeDate, setShowtimeDate] = useState(() => {
    const tmr = new Date();
    tmr.setDate(tmr.getDate() + 1);
    tmr.setHours(19, 0, 0, 0);
    // Format YYYY-MM-DDTHH:mm
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${tmr.getFullYear()}-${pad(tmr.getMonth() + 1)}-${pad(tmr.getDate())}T${pad(tmr.getHours())}:${pad(tmr.getMinutes())}`;
  });

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Vui lòng chọn tệp định dạng hình ảnh (PNG, JPG, WEBP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Kích thước tệp ảnh không được vượt quá 10MB.");
      return;
    }

    setError(null);
    setPosterFile(file);
    const reader = new FileReader();
    reader.onload = () => {
      setPosterPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  function handleRemoveImage() {
    setPosterFile(null);
    setPosterPreview(null);
    setPosterUrlInput("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Vui lòng nhập tên phim.");
      return;
    }
    if (!description.trim()) {
      setError("Vui lòng nhập tóm tắt nội dung phim.");
      return;
    }
    const duration = Number(durationMinutes);
    if (!duration || duration <= 0 || duration > 600) {
      setError("Thời lượng phim phải lớn hơn 0 và không quá 600 phút.");
      return;
    }
    if (!releaseDate) {
      setError("Vui lòng chọn ngày phát hành.");
      return;
    }

    if (addInitialShowtime && !showtimeDate) {
      setError("Vui lòng chọn thời gian bắt đầu cho suất chiếu.");
      return;
    }

    setIsSubmitting(true);
    try {
      let finalPosterUrl: string | null = null;

      // 1. Tải ảnh lên nếu có file được chọn
      if (posterFile && posterPreview) {
        setIsUploadingImage(true);
        try {
          finalPosterUrl = await uploadMovieImage(posterFile.name, posterPreview);
        } catch (uploadErr) {
          setError(getApiErrorMessage(uploadErr, "Tải ảnh lên máy chủ thất bại."));
          setIsSubmitting(false);
          setIsUploadingImage(false);
          return;
        }
        setIsUploadingImage(false);
      } else if (posterUrlInput.trim()) {
        finalPosterUrl = posterUrlInput.trim();
      }

      // 2. Tạo phim mới
      let createdMovieId: number | null = null;
      try {
        const createdMovie = await createMovie({
          title: title.trim(),
          description: description.trim(),
          duration_minutes: duration,
          release_date: releaseDate,
          poster_url: finalPosterUrl,
        });
        createdMovieId = createdMovie.id;
      } catch (movieErr) {
        setError(getApiErrorMessage(movieErr, "Không thể tạo phim mới. Vui lòng kiểm tra lại thông tin."));
        return;
      }

      // 3. Tạo suất chiếu đầu tiên nếu có chọn
      if (addInitialShowtime && showtimeDate && createdMovieId) {
        try {
          const isoStartTime = new Date(showtimeDate).toISOString();
          await createShowtime({
            movie_id: createdMovieId,
            room_name: roomName,
            start_time: isoStartTime,
          });
        } catch (stErr) {
          console.warn("Lỗi khi tạo suất chiếu đầu tiên:", stErr);
        }
      }

      navigate(`/movies/${createdMovieId}`, {
        replace: true,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, "Đã xảy ra lỗi không xác định khi lưu thông tin phim."));
    } finally {
      setIsSubmitting(false);
      setIsUploadingImage(false);
    }
  }

  return (
    <div className="admin-page-container" style={{ maxWidth: "48rem", margin: "2rem auto", padding: "0 1rem" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          to="/movies"
          className="button button--ghost button--small"
          style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
        >
          <ArrowLeft size={16} />
          <span>Quay lại danh sách phim</span>
        </Link>
      </div>

      <div className="auth-card-v2" style={{ width: "100%", maxWidth: "100%" }}>
        <div className="auth-header">
          <div className="auth-brand-logo" style={{ background: "rgba(225, 29, 72, 0.15)", color: "var(--color-primary)" }}>
            <PlusCircle size={26} />
          </div>
          <h1 className="auth-title">Quản Trị: Thêm Phim & Suất Chiếu Mới</h1>
          <p className="auth-subtitle">
            Cung cấp thông tin bộ phim, tải ảnh poster hiển thị và lên lịch suất chiếu vào hệ thống CineVerse.
          </p>
        </div>

        {error ? (
          <div className="alert alert--error" style={{ marginBottom: "1.5rem" }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          {/* Tên phim */}
          <div className="form-field">
            <label htmlFor="movie-title">Tên phim *</label>
            <div className="input-group">
              <span className="input-icon">
                <Film size={18} />
              </span>
              <input
                id="movie-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="VD: Avatar: Lửa Và Tro"
                required
              />
            </div>
          </div>

          {/* Tải ảnh poster phim */}
          <div className="form-field">
            <label>Ảnh bìa / Poster phim khi hiển thị</label>
            <div
              style={{
                border: "1px dashed var(--color-border, #334155)",
                borderRadius: "12px",
                padding: "1.25rem",
                background: "rgba(15, 23, 42, 0.4)",
                textAlign: "center",
              }}
            >
              {posterPreview ? (
                <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", textAlign: "left" }}>
                  <img
                    src={posterPreview}
                    alt="Xem trước poster"
                    style={{
                      width: "100px",
                      height: "150px",
                      objectFit: "cover",
                      borderRadius: "8px",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                      border: "1px solid rgba(255,255,255,0.1)",
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#4ade80", marginBottom: "0.5rem" }}>
                      <CheckCircle2 size={18} />
                      <strong style={{ fontSize: "0.95rem" }}>Đã chọn ảnh poster</strong>
                    </div>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
                      {posterFile ? `Tệp: ${posterFile.name} (${(posterFile.size / 1024).toFixed(1)} KB)` : "Đường dẫn ảnh trực tuyến"}
                    </p>
                    <button
                      type="button"
                      className="button button--danger button--small"
                      onClick={handleRemoveImage}
                      style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
                    >
                      <Trash2 size={14} />
                      <span>Xóa và chọn ảnh khác</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: "48px",
                      height: "48px",
                      borderRadius: "50%",
                      background: "rgba(225, 29, 72, 0.1)",
                      color: "var(--color-primary)",
                      marginBottom: "0.75rem",
                    }}
                  >
                    <Upload size={24} />
                  </div>
                  <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>Tải ảnh poster từ thiết bị</h4>
                  <p style={{ margin: "0 0 1rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    Hỗ trợ PNG, JPG, WEBP (tối đa 10MB). Ảnh sẽ làm hình nền đại diện cho phim khi khách chọn vé.
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    style={{ display: "none" }}
                    id="poster-upload-input"
                  />
                  <label
                    htmlFor="poster-upload-input"
                    className="button button--small button--glow"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}
                  >
                    <ImageIcon size={16} />
                    <span>Chọn tệp ảnh tải lên</span>
                  </label>

                  <div style={{ margin: "1rem 0 0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    - Hoặc dán trực tiếp đường dẫn URL ảnh -
                  </div>
                  <input
                    type="url"
                    value={posterUrlInput}
                    onChange={(e) => {
                      setPosterUrlInput(e.target.value);
                      if (e.target.value.trim().startsWith("http")) {
                        setPosterPreview(e.target.value.trim());
                      }
                    }}
                    placeholder="https://example.com/poster.jpg"
                    style={{
                      width: "100%",
                      maxWidth: "24rem",
                      padding: "0.5rem 0.75rem",
                      borderRadius: "6px",
                      background: "rgba(0,0,0,0.3)",
                      border: "1px solid var(--color-border, #334155)",
                      color: "var(--text-main)",
                      fontSize: "0.85rem",
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Tóm tắt nội dung */}
          <div className="form-field">
            <label htmlFor="movie-desc">Tóm tắt nội dung phim *</label>
            <div className="input-group" style={{ alignItems: "flex-start", paddingTop: "0.75rem" }}>
              <span className="input-icon" style={{ marginTop: "0.25rem" }}>
                <FileText size={18} />
              </span>
              <textarea
                id="movie-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Mô tả tóm tắt nội dung, thể loại, đạo diễn hoặc dàn diễn viên..."
                rows={4}
                required
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-main)",
                  outline: "none",
                  resize: "vertical",
                  fontFamily: "inherit",
                  fontSize: "0.95rem",
                  paddingLeft: "0.5rem",
                }}
              />
            </div>
          </div>

          {/* Thời lượng và Ngày phát hành */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-field">
              <label htmlFor="movie-duration">Thời lượng (phút) *</label>
              <div className="input-group">
                <span className="input-icon">
                  <Clock size={18} />
                </span>
                <input
                  id="movie-duration"
                  type="number"
                  min={1}
                  max={600}
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="120"
                  required
                />
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="movie-release">Ngày phát hành *</label>
              <div className="input-group">
                <span className="input-icon">
                  <Calendar size={18} />
                </span>
                <input
                  id="movie-release"
                  type="date"
                  value={releaseDate}
                  onChange={(e) => setReleaseDate(e.target.value)}
                  required
                  style={{ colorScheme: "dark" }}
                />
              </div>
            </div>
          </div>

          {/* Lên lịch suất chiếu đầu tiên */}
          <div
            style={{
              marginTop: "0.5rem",
              padding: "1.25rem",
              borderRadius: "12px",
              background: "rgba(30, 41, 59, 0.4)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                cursor: "pointer",
                fontWeight: 600,
                color: "var(--text-main)",
                marginBottom: addInitialShowtime ? "1rem" : "0",
              }}
            >
              <input
                type="checkbox"
                checked={addInitialShowtime}
                onChange={(e) => setAddInitialShowtime(e.target.checked)}
                style={{ width: "18px", height: "18px", accentColor: "var(--color-primary)" }}
              />
              <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
                <Sparkles size={16} color="var(--color-primary)" />
                Tạo ngay suất chiếu đầu tiên cho phim này
              </span>
            </label>

            {addInitialShowtime ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.5rem" }}>
                <div className="form-field">
                  <label htmlFor="showtime-room">Phòng chiếu</label>
                  <div className="input-group">
                    <span className="input-icon">
                      <MapPin size={18} />
                    </span>
                    <select
                      id="showtime-room"
                      value={roomName}
                      onChange={(e) => setRoomName(e.target.value)}
                      style={{
                        width: "100%",
                        background: "transparent",
                        border: "none",
                        color: "var(--text-main)",
                        outline: "none",
                        padding: "0.6rem 0.5rem",
                        fontFamily: "inherit",
                        fontSize: "0.95rem",
                      }}
                    >
                      <option value="ROOM_1" style={{ background: "#1e293b" }}>
                        Phòng 1 (ROOM_1 - Standard)
                      </option>
                      <option value="ROOM_2" style={{ background: "#1e293b" }}>
                        Phòng 2 (ROOM_2 - VIP)
                      </option>
                    </select>
                  </div>
                </div>

                <div className="form-field">
                  <label htmlFor="showtime-time">Thời gian bắt đầu chiếu</label>
                  <div className="input-group">
                    <span className="input-icon">
                      <Clock size={18} />
                    </span>
                    <input
                      id="showtime-time"
                      type="datetime-local"
                      value={showtimeDate}
                      onChange={(e) => setShowtimeDate(e.target.value)}
                      required={addInitialShowtime}
                      style={{ colorScheme: "dark" }}
                    />
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <button
            className="button button--wide button--glow button--large"
            type="submit"
            disabled={isSubmitting}
            style={{ marginTop: "1rem" }}
          >
            <PlusCircle size={18} />
            <span>
              {isUploadingImage
                ? "Đang tải ảnh poster lên..."
                : isSubmitting
                ? "Đang lưu thông tin phim & suất chiếu..."
                : "Tạo và Đăng Phim & Suất Chiếu"}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
}
