import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Star,
  Ticket,
  MapPin,
  Film,
  Sparkles,
  PlusCircle,
  X,
  AlertCircle,
  CheckCircle2,
  Pencil,
  Trash2,
} from "lucide-react";

import { getApiErrorMessage } from "../api/errors";
import { deleteMovie, getMovieById } from "../api/movieApi";
import {
  createShowtime,
  deleteShowtime,
  getShowtimes,
  updateShowtime,
} from "../api/showtimeApi";
import { ConfirmModal } from "../components/ConfirmModal";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { useAuth } from "../context/AuthContext";
import type { Movie } from "../types/movie";
import type { Showtime } from "../types/showtime";
import {
  calculateEndTime,
  formatDate,
  formatDateTime,
  formatDayOfWeek,
  formatTimeOnly,
} from "../utils/date";
import { getMovieMeta } from "../utils/movieMeta";

export function MovieDetailPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const { movieId: movieIdParam } = useParams();
  const movieId = Number(movieIdParam);

  const [movie, setMovie] = useState<Movie | null>(null);
  const [showtimes, setShowtimes] = useState<Showtime[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDateKey, setSelectedDateKey] = useState<string>("ALL");

  // State cho modal thêm suất chiếu mới của Admin
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRoomName, setNewRoomName] = useState("ROOM_1");
  const [newStartTime, setNewStartTime] = useState(() => {
    const tmr = new Date();
    tmr.setDate(tmr.getDate() + 1);
    tmr.setHours(19, 0, 0, 0);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${tmr.getFullYear()}-${pad(tmr.getMonth() + 1)}-${pad(tmr.getDate())}T${pad(tmr.getHours())}:${pad(tmr.getMinutes())}`;
  });
  const [isAddingShowtime, setIsAddingShowtime] = useState(false);
  const [addShowtimeError, setAddShowtimeError] = useState<string | null>(null);
  const [addSuccessMessage, setAddSuccessMessage] = useState<string | null>(null);

  // State cho sửa suất chiếu
  const [editShowtimeModalOpen, setEditShowtimeModalOpen] = useState(false);
  const [showtimeToEdit, setShowtimeToEdit] = useState<Showtime | null>(null);
  const [editRoomName, setEditRoomName] = useState("ROOM_1");
  const [editStartTime, setEditStartTime] = useState("");
  const [isUpdatingShowtime, setIsUpdatingShowtime] = useState(false);
  const [editShowtimeError, setEditShowtimeError] = useState<string | null>(null);

  // State cho xóa suất chiếu
  const [deleteShowtimeModalOpen, setDeleteShowtimeModalOpen] = useState(false);
  const [showtimeToDelete, setShowtimeToDelete] = useState<Showtime | null>(null);
  const [isDeletingShowtime, setIsDeletingShowtime] = useState(false);

  // State cho xóa phim
  const [deleteMovieModalOpen, setDeleteMovieModalOpen] = useState(false);
  const [isDeletingMovie, setIsDeletingMovie] = useState(false);

  async function loadMovieDetail() {
    if (!Number.isInteger(movieId) || movieId <= 0) {
      setError("Movie ID không hợp lệ.");
      setIsLoading(false);
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      const [movieData, showtimeData] = await Promise.all([
        getMovieById(movieId),
        getShowtimes(movieId),
      ]);
      setMovie(movieData);
      setShowtimes(showtimeData);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Không thể tải thông tin chi tiết phim."));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAddShowtime(e: FormEvent) {
    e.preventDefault();
    if (!movie) return;
    if (!newStartTime) {
      setAddShowtimeError("Vui lòng chọn thời gian bắt đầu chiếu.");
      return;
    }
    setAddShowtimeError(null);
    setIsAddingShowtime(true);
    try {
      await createShowtime({
        movie_id: movie.id,
        room_name: newRoomName,
        start_time: new Date(newStartTime).toISOString(),
      });
      setAddSuccessMessage("Thêm suất chiếu mới thành công!");
      const updatedShowtimes = await getShowtimes(movieId);
      setShowtimes(updatedShowtimes);
      setTimeout(() => {
        setShowAddModal(false);
        setAddSuccessMessage(null);
      }, 1200);
    } catch (err) {
      setAddShowtimeError(getApiErrorMessage(err, "Không thể tạo suất chiếu mới."));
    } finally {
      setIsAddingShowtime(false);
    }
  }

  async function handleDeleteMovie() {
    if (!movie) return;
    setIsDeletingMovie(true);
    setActionError(null);
    try {
      await deleteMovie(movie.id);
      navigate("/movies");
    } catch (err) {
      setActionError(
        getApiErrorMessage(
          err,
          "Không thể xóa phim này. Có thể phim đã có suất chiếu với người đặt vé."
        )
      );
      setDeleteMovieModalOpen(false);
    } finally {
      setIsDeletingMovie(false);
    }
  }

  function openEditShowtimeModal(st: Showtime) {
    setShowtimeToEdit(st);
    setEditRoomName(st.room_name);
    const d = new Date(st.start_time);
    const pad = (n: number) => String(n).padStart(2, "0");
    const localStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    setEditStartTime(localStr);
    setEditShowtimeError(null);
    setEditShowtimeModalOpen(true);
  }

  async function handleUpdateShowtime(e: FormEvent) {
    e.preventDefault();
    if (!showtimeToEdit) return;
    if (!editStartTime) {
      setEditShowtimeError("Vui lòng chọn thời gian bắt đầu chiếu.");
      return;
    }
    setIsUpdatingShowtime(true);
    setEditShowtimeError(null);
    try {
      await updateShowtime(showtimeToEdit.id, {
        room_name: editRoomName,
        start_time: new Date(editStartTime).toISOString(),
      });
      setEditShowtimeModalOpen(false);
      setShowtimeToEdit(null);
      const updatedShowtimes = await getShowtimes(movieId);
      setShowtimes(updatedShowtimes);
    } catch (err) {
      setEditShowtimeError(
        getApiErrorMessage(err, "Không thể cập nhật thông tin suất chiếu.")
      );
    } finally {
      setIsUpdatingShowtime(false);
    }
  }

  function openDeleteShowtimeModal(st: Showtime) {
    setShowtimeToDelete(st);
    setDeleteShowtimeModalOpen(true);
  }

  async function handleDeleteShowtime() {
    if (!showtimeToDelete) return;
    setIsDeletingShowtime(true);
    setActionError(null);
    try {
      await deleteShowtime(showtimeToDelete.id);
      setDeleteShowtimeModalOpen(false);
      setShowtimeToDelete(null);
      const updatedShowtimes = await getShowtimes(movieId);
      setShowtimes(updatedShowtimes);
    } catch (err) {
      setActionError(
        getApiErrorMessage(
          err,
          "Không thể xóa suất chiếu này. Có thể đã có ghế được đặt trong suất chiếu."
        )
      );
      setDeleteShowtimeModalOpen(false);
    } finally {
      setIsDeletingShowtime(false);
    }
  }

  useEffect(() => {
    void loadMovieDetail();
  }, [movieIdParam]);

  const meta = movie ? getMovieMeta(movie) : null;

  // Gom nhóm các lịch chiếu theo ngày địa phương (YYYY-MM-DD)
  const showtimesByDate = useMemo(() => {
    const map = new Map<string, Showtime[]>();
    for (const st of showtimes) {
      let dateKey = st.start_time.split("T")[0];
      try {
        const d = new Date(st.start_time);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        dateKey = `${y}-${m}-${day}`;
      } catch {
        // fallback
      }
      const list = map.get(dateKey) ?? [];
      list.push(st);
      map.set(dateKey, list);
    }
    return map;
  }, [showtimes]);

  // Danh sách ngày duy nhất đã sắp xếp
  const availableDates = useMemo(() => {
    return Array.from(showtimesByDate.keys()).sort();
  }, [showtimesByDate]);

  // Thiết lập ngày mặc định được chọn
  useEffect(() => {
    if (availableDates.length > 0 && selectedDateKey === "ALL") {
      setSelectedDateKey(availableDates[0]);
    }
  }, [availableDates, selectedDateKey]);

  const displayedShowtimes = useMemo(() => {
    if (selectedDateKey === "ALL") return showtimes;
    return showtimesByDate.get(selectedDateKey) ?? [];
  }, [selectedDateKey, showtimes, showtimesByDate]);

  if (isLoading) {
    return <Loading message="Đang tải thông tin phim & suất chiếu..." />;
  }
  if (error) {
    return <ErrorMessage message={error} onRetry={() => void loadMovieDetail()} />;
  }
  if (!movie || !meta) {
    return <ErrorMessage message="Không tìm thấy dữ liệu phim." />;
  }

  return (
    <div className="movie-detail-view">
      {/* Nút quay lại */}
      <div className="back-bar">
        <Link className="back-link-v2" to="/movies">
          <ArrowLeft size={18} />
          <span>Danh sách phim</span>
        </Link>
      </div>

      {/* Backdrop rạp chiếu phim Hero */}
      <section className="detail-hero">
        <div
          className="detail-hero__backdrop"
          style={{ backgroundImage: `url(${meta.backdropUrl})` }}
        />
        <div className="detail-hero__overlay" />

        <div className="detail-hero__container">
          <div className="detail-poster-card">
            <img
              src={meta.posterUrl}
              alt={movie.title}
              className="detail-poster-img"
            />
            <div className="detail-poster-badges">
              <span className="badge badge--age">{meta.ageRating}</span>
              <span className="badge badge--format">{meta.format}</span>
            </div>
          </div>

          <div className="detail-info-block">
            <div className="detail-genre-list">
              {meta.genres.map((g) => (
                <span key={g} className="genre-pill">
                  {g}
                </span>
              ))}
            </div>

            <h1 className="detail-title">{movie.title}</h1>

            <div className="detail-metrics">
              <span className="metric-chip metric-chip--rating">
                <Star size={16} fill="currentColor" />
                <strong>{meta.rating}</strong> / 10
              </span>
              <span className="metric-chip">
                <Clock size={16} />
                <span>{movie.duration_minutes} phút</span>
              </span>
              <span className="metric-chip">
                <Calendar size={16} />
                <span>Khởi chiếu {formatDate(movie.release_date)}</span>
              </span>
            </div>

            <div className="detail-synopsis">
              <h3>Nội dung phim</h3>
              <p>{movie.description}</p>
            </div>

            <div className="detail-credits">
              <div className="credit-row">
                <span className="credit-label">Đạo diễn:</span>
                <span className="credit-value">{meta.director}</span>
              </div>
              <div className="credit-row">
                <span className="credit-label">Diễn viên:</span>
                <span className="credit-value">{meta.cast}</span>
              </div>
              <div className="credit-row">
                <span className="credit-label">Định dạng:</span>
                <span className="credit-value">{meta.format} • Âm thanh vòm Dolby 7.1</span>
              </div>
            </div>

            {isAdmin ? (
              <div
                style={{
                  display: "flex",
                  gap: "0.75rem",
                  marginTop: "1.25rem",
                  paddingTop: "1rem",
                  borderTop: "1px solid rgba(255, 255, 255, 0.1)",
                  flexWrap: "wrap",
                }}
              >
                <Link
                  to={`/admin/movies/${movie.id}/edit`}
                  className="button button--secondary button--small"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
                >
                  <Pencil size={15} />
                  <span>Sửa thông tin phim</span>
                </Link>
                <button
                  type="button"
                  onClick={() => setDeleteMovieModalOpen(true)}
                  className="button button--danger button--small"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
                >
                  <Trash2 size={15} />
                  <span>Xóa phim</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {actionError ? (
        <div
          className="alert alert--error"
          style={{
            maxWidth: "1200px",
            margin: "1.5rem auto 0",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <AlertCircle size={18} />
          <span style={{ flex: 1 }}>{actionError}</span>
          <button
            type="button"
            onClick={() => setActionError(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              padding: 0,
            }}
          >
            <X size={16} />
          </button>
        </div>
      ) : null}

      {/* Phần chọn lịch chiếu */}
      <section className="showtimes-section">
        <div className="section-heading-v2" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <p className="eyebrow">Lịch chiếu phim</p>
            <h2 className="section-title">
              <Ticket size={24} className="title-icon" />
              <span>Chọn suất chiếu & đặt vé</span>
            </h2>
          </div>
          {isAdmin ? (
            <button
              type="button"
              className="button button--small button--glow"
              onClick={() => {
                setAddShowtimeError(null);
                setAddSuccessMessage(null);
                setShowAddModal(true);
              }}
              style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
            >
              <PlusCircle size={16} />
              <span>Thêm suất chiếu</span>
            </button>
          ) : null}
        </div>

        {showtimes.length === 0 ? (
          <div className="empty-state">
            <Film size={44} className="empty-icon" />
            <p className="empty-state__title">Chưa có suất chiếu</p>
            <p className="muted">
              Phim hiện đang được cập nhật lịch chiếu. Vui lòng quay lại sau!
            </p>
          </div>
        ) : (
          <>
            {/* Các tab lọc theo ngày */}
            <div className="date-tabs-bar">
              {availableDates.map((dateStr) => {
                const isActive = selectedDateKey === dateStr;
                const dayLabel = formatDayOfWeek(`${dateStr}T12:00:00`);
                const formattedDate = formatDate(dateStr);
                return (
                  <button
                    key={dateStr}
                    type="button"
                    onClick={() => setSelectedDateKey(dateStr)}
                    className={`date-tab ${isActive ? "date-tab--active" : ""}`}
                  >
                    <span className="date-tab__day">{dayLabel}</span>
                    <span className="date-tab__date">{formattedDate}</span>
                  </button>
                );
              })}
            </div>

            {/* Lưới thẻ lịch chiếu */}
            <div className="showtime-cards-grid">
              {displayedShowtimes.map((showtime) => {
                const startTimeFormatted = formatTimeOnly(showtime.start_time);
                const endTimeFormatted = calculateEndTime(
                  showtime.start_time,
                  movie.duration_minutes
                );

                return (
                  <article className="showtime-card-v2" key={showtime.id}>
                    <div className="showtime-card-v2__header">
                      <span className="room-badge">
                        <MapPin size={14} />
                        <span>Phòng {showtime.room_name}</span>
                      </span>
                      <span className="format-sub-badge">2D Phụ đề</span>
                      {isAdmin ? (
                        <div style={{ display: "flex", gap: "0.25rem", marginLeft: "auto" }}>
                          <button
                            type="button"
                            title="Sửa suất chiếu"
                            className="button button--ghost button--small"
                            style={{ padding: "0.25rem 0.5rem", borderRadius: "6px" }}
                            onClick={() => openEditShowtimeModal(showtime)}
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            type="button"
                            title="Xóa suất chiếu"
                            className="button button--ghost button--small"
                            style={{
                              padding: "0.25rem 0.5rem",
                              borderRadius: "6px",
                              color: "var(--color-danger, #ef4444)",
                            }}
                            onClick={() => openDeleteShowtimeModal(showtime)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ) : null}
                    </div>

                    <div className="showtime-card-v2__times">
                      <div className="time-primary">{startTimeFormatted}</div>
                      <div className="time-secondary">
                        Đến ~{endTimeFormatted}
                      </div>
                    </div>

                    <div className="showtime-card-v2__footer">
                      <div className="price-hint">
                        <span>Giá vé từ:</span>
                        <strong>90.000 ₫</strong>
                      </div>
                      <Link
                        className="button button--glow button--small"
                        to={`/showtimes/${showtime.id}/seats`}
                      >
                        <Sparkles size={15} />
                        <span>{isAdmin ? "Xem sơ đồ ghế" : "Chọn ghế"}</span>
                      </Link>
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </section>

      {/* Modal Thêm Suất Chiếu Mới (Dành cho Admin) */}
      {showAddModal && movie ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
          onClick={() => setShowAddModal(false)}
        >
          <div
            className="auth-card-v2"
            style={{ maxWidth: "28rem", width: "100%", margin: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.2rem" }}>
                <PlusCircle size={20} color="var(--color-primary)" />
                <span>Thêm Suất Chiếu Mới</span>
              </h3>
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => setShowAddModal(false)}
                style={{ padding: "0.25rem" }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
              Lên lịch chiếu mới cho phim <strong>{movie.title}</strong>
            </p>

            {addShowtimeError ? (
              <div className="alert alert--error" style={{ marginBottom: "1rem" }}>
                <AlertCircle size={16} />
                <span>{addShowtimeError}</span>
              </div>
            ) : null}

            {addSuccessMessage ? (
              <div className="alert alert--success" style={{ marginBottom: "1rem" }}>
                <CheckCircle2 size={16} />
                <span>{addSuccessMessage}</span>
              </div>
            ) : null}

            <form onSubmit={handleAddShowtime} className="auth-form">
              <div className="form-field">
                <label htmlFor="modal-room">Phòng chiếu *</label>
                <div className="input-group">
                  <span className="input-icon">
                    <MapPin size={18} />
                  </span>
                  <select
                    id="modal-room"
                    value={newRoomName}
                    onChange={(e) => setNewRoomName(e.target.value)}
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
                      Phòng 1 (ROOM_1 - Standard 15 ghế)
                    </option>
                    <option value="ROOM_2" style={{ background: "#1e293b" }}>
                      Phòng 2 (ROOM_2 - VIP 15 ghế)
                    </option>
                  </select>
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="modal-start-time">Thời gian bắt đầu chiếu *</label>
                <div className="input-group">
                  <span className="input-icon">
                    <Clock size={18} />
                  </span>
                  <input
                    id="modal-start-time"
                    type="datetime-local"
                    value={newStartTime}
                    onChange={(e) => setNewStartTime(e.target.value)}
                    required
                    style={{ colorScheme: "dark" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => setShowAddModal(false)}
                  style={{ flex: 1 }}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="button button--glow"
                  disabled={isAddingShowtime}
                  style={{ flex: 1 }}
                >
                  {isAddingShowtime ? "Đang lưu..." : "Xác nhận tạo"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Modal Sửa Suất Chiếu (Admin) */}
      {editShowtimeModalOpen && showtimeToEdit && movie ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
          onClick={() => setEditShowtimeModalOpen(false)}
        >
          <div
            className="auth-card-v2"
            style={{ maxWidth: "28rem", width: "100%", margin: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1rem",
              }}
            >
              <h3
                style={{
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  fontSize: "1.2rem",
                }}
              >
                <Pencil size={20} color="var(--color-primary)" />
                <span>Sửa Suất Chiếu</span>
              </h3>
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => setEditShowtimeModalOpen(false)}
                style={{ padding: "0.25rem" }}
              >
                <X size={20} />
              </button>
            </div>

            <p
              style={{
                fontSize: "0.85rem",
                color: "var(--text-muted)",
                marginBottom: "1.25rem",
              }}
            >
              Chỉnh sửa thời gian hoặc phòng chiếu cho phim <strong>{movie.title}</strong>
            </p>

            {editShowtimeError ? (
              <div className="alert alert--error" style={{ marginBottom: "1rem" }}>
                <AlertCircle size={16} />
                <span>{editShowtimeError}</span>
              </div>
            ) : null}

            <form onSubmit={handleUpdateShowtime} className="auth-form">
              <div className="form-field">
                <label htmlFor="edit-modal-room">Phòng chiếu *</label>
                <div className="input-group">
                  <span className="input-icon">
                    <MapPin size={18} />
                  </span>
                  <select
                    id="edit-modal-room"
                    value={editRoomName}
                    onChange={(e) => setEditRoomName(e.target.value)}
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
                      Phòng 1 (ROOM_1 - Standard 15 ghế)
                    </option>
                    <option value="ROOM_2" style={{ background: "#1e293b" }}>
                      Phòng 2 (ROOM_2 - VIP 15 ghế)
                    </option>
                  </select>
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="edit-modal-start-time">Thời gian bắt đầu chiếu *</label>
                <div className="input-group">
                  <span className="input-icon">
                    <Clock size={18} />
                  </span>
                  <input
                    id="edit-modal-start-time"
                    type="datetime-local"
                    value={editStartTime}
                    onChange={(e) => setEditStartTime(e.target.value)}
                    required
                    style={{ colorScheme: "dark" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => setEditShowtimeModalOpen(false)}
                  style={{ flex: 1 }}
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="button button--glow"
                  disabled={isUpdatingShowtime}
                  style={{ flex: 1 }}
                >
                  {isUpdatingShowtime ? "Đang lưu..." : "Cập nhật"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Modal xác nhận xóa suất chiếu */}
      <ConfirmModal
        isOpen={deleteShowtimeModalOpen}
        title="Xóa suất chiếu"
        message={`Bạn có chắc chắn muốn xóa suất chiếu lúc ${
          showtimeToDelete ? formatDateTime(showtimeToDelete.start_time) : ""
        } (Phòng ${showtimeToDelete?.room_name})?`}
        confirmText="Xác nhận xóa"
        isDanger={true}
        isLoading={isDeletingShowtime}
        onConfirm={() => void handleDeleteShowtime()}
        onClose={() => {
          setDeleteShowtimeModalOpen(false);
          setShowtimeToDelete(null);
        }}
      />

      {/* Modal xác nhận xóa phim */}
      <ConfirmModal
        isOpen={deleteMovieModalOpen}
        title="Xóa phim"
        message={`Bạn có chắc chắn muốn xóa phim "${movie.title}"? Thao tác này sẽ xóa các suất chiếu chưa có người đặt vé. Không thể hoàn tác.`}
        confirmText="Xác nhận xóa"
        isDanger={true}
        isLoading={isDeletingMovie}
        onConfirm={() => void handleDeleteMovie()}
        onClose={() => setDeleteMovieModalOpen(false)}
      />
    </div>
  );
}
