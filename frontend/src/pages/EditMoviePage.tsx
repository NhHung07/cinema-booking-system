import { useEffect, useState, useRef, type FormEvent, type ChangeEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Film,
  Clock,
  Calendar,
  FileText,
  ArrowLeft,
  AlertCircle,
  Upload,
  Image as ImageIcon,
  Trash2,
  CheckCircle2,
  Save,
} from "lucide-react";

import { getMovieById, updateMovie, uploadMovieImage } from "../api/movieApi";
import { getApiErrorMessage } from "../api/errors";
import { Loading } from "../components/Loading";
import { ErrorMessage } from "../components/ErrorMessage";
import type { Movie } from "../types/movie";

export function EditMoviePage() {
  const { movieId: movieIdParam } = useParams();
  const movieId = Number(movieIdParam);
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [durationMinutes, setDurationMinutes] = useState<number | "">(120);
  const [releaseDate, setReleaseDate] = useState("");

  // Quản lý ảnh của phim
  const [posterFile, setPosterFile] = useState<File | null>(null);
  const [posterPreview, setPosterPreview] = useState<string | null>(null);
  const [posterUrlInput, setPosterUrlInput] = useState("");
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadMovieData() {
    if (!Number.isInteger(movieId) || movieId <= 0) {
      setLoadError("Mã định danh phim không hợp lệ.");
      setIsLoading(false);
      return;
    }
    setLoadError(null);
    setIsLoading(true);
    try {
      const movie: Movie = await getMovieById(movieId);
      setTitle(movie.title);
      setDescription(movie.description);
      setDurationMinutes(movie.duration_minutes);
      setReleaseDate(movie.release_date);
      if (movie.poster_url) {
        setPosterUrlInput(movie.poster_url);
        setPosterPreview(movie.poster_url);
      }
    } catch (err) {
      setLoadError(getApiErrorMessage(err, "Không thể tải thông tin bộ phim để chỉnh sửa."));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMovieData();
  }, [movieIdParam]);

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

    setIsSubmitting(true);
    try {
      let finalPosterUrl: string | null = null;

      // 1. Tải ảnh lên nếu có file mới được chọn
      if (posterFile && posterPreview && posterPreview.startsWith("data:")) {
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

      // 2. Cập nhật thông tin phim
      await updateMovie(movieId, {
        title: title.trim(),
        description: description.trim(),
        duration_minutes: duration,
        release_date: releaseDate,
        poster_url: finalPosterUrl,
      });

      navigate(`/movies/${movieId}`, {
        replace: true,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, "Không thể cập nhật thông tin phim. Vui lòng kiểm tra lại."));
    } finally {
      setIsSubmitting(false);
      setIsUploadingImage(false);
    }
  }

  if (isLoading) {
    return <Loading message="Đang tải dữ liệu phim cần sửa..." />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} onRetry={() => void loadMovieData()} />;
  }

  return (
    <div className="admin-page-container" style={{ maxWidth: "48rem", margin: "2rem auto", padding: "0 1rem" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          to={`/movies/${movieId}`}
          className="button button--ghost button--small"
          style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
        >
          <ArrowLeft size={16} />
          <span>Quay lại chi tiết phim</span>
        </Link>
      </div>

      <div className="auth-card-v2" style={{ width: "100%", maxWidth: "100%" }}>
        <div className="auth-header">
          <div className="auth-brand-logo" style={{ background: "rgba(225, 29, 72, 0.15)", color: "var(--color-primary)" }}>
            <Film size={26} />
          </div>
          <h1 className="auth-title">Quản Trị: Chỉnh Sửa Phim</h1>
          <p className="auth-subtitle">
            Cập nhật tên, thời lượng, tóm tắt và poster đại diện cho bộ phim #{movieId}.
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
            <label>Ảnh bìa / Poster phim</label>
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
                      {posterFile ? `Tệp mới: ${posterFile.name}` : "Poster hiện tại của phim"}
                    </p>
                    <button
                      type="button"
                      className="button button--danger button--small"
                      onClick={handleRemoveImage}
                      style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
                    >
                      <Trash2 size={14} />
                      <span>Xóa và đổi ảnh khác</span>
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
                    Hỗ trợ PNG, JPG, WEBP (tối đa 10MB).
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    style={{ display: "none" }}
                    id="poster-edit-upload"
                  />
                  <label
                    htmlFor="poster-edit-upload"
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
                placeholder="Mô tả tóm tắt nội dung..."
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

          <button
            className="button button--wide button--glow button--large"
            type="submit"
            disabled={isSubmitting}
            style={{ marginTop: "1rem" }}
          >
            <Save size={18} />
            <span>
              {isUploadingImage
                ? "Đang tải ảnh lên..."
                : isSubmitting
                ? "Đang lưu thay đổi..."
                : "Lưu cập nhật phim"}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
}

