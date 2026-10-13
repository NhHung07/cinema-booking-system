import { useEffect, useState, useMemo } from "react";
import {
  DollarSign,
  Ticket,
  Users,
  TrendingUp,
  RefreshCw,
  Film,
  Award,
  Calendar,
  AlertCircle,
  Armchair,
  CheckCircle2,
  XCircle,
  BarChart3,
  Sparkles,
} from "lucide-react";

import { getAnalyticsOverview } from "../api/analyticsApi";
import type { AnalyticsOverviewResponse, RevenueTimelinePoint } from "../types/analytics";
import { formatCurrency, formatDate, formatDateTime } from "../utils/date";

export function AdminDashboardPage() {
  const [data, setData] = useState<AnalyticsOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [daysFilter, setDaysFilter] = useState<number>(7);
  const [activeTab, setActiveTab] = useState<"revenue" | "tickets">("revenue");
  const [hoveredPoint, setHoveredPoint] = useState<RevenueTimelinePoint | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  async function fetchAnalytics(days: number) {
    try {
      setLoading(true);
      setError(null);
      const res = await getAnalyticsOverview(days);
      setData(res);
    } catch (err: unknown) {
      console.error("Failed to load analytics:", err);
      setError("Không thể tải dữ liệu báo cáo thống kê. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAnalytics(daysFilter);
  }, [daysFilter]);

  // Tính toán dữ liệu đồ thị SVG
  const chartData = useMemo(() => {
    if (!data || !data.revenue_timeline || data.revenue_timeline.length === 0) {
      return null;
    }
    const points = data.revenue_timeline;
    const values = points.map((p) => (activeTab === "revenue" ? p.revenue : p.tickets));
    const maxVal = Math.max(...values, activeTab === "revenue" ? 100000 : 1);
    const minVal = 0;

    const width = 800;
    const height = 240;
    const paddingLeft = 60;
    const paddingRight = 25;
    const paddingTop = 25;
    const paddingBottom = 40;

    const plotWidth = width - paddingLeft - paddingRight;
    const plotHeight = height - paddingTop - paddingBottom;

    const coords = points.map((p, idx) => {
      const val = activeTab === "revenue" ? p.revenue : p.tickets;
      const x =
        points.length > 1
          ? paddingLeft + (idx / (points.length - 1)) * plotWidth
          : paddingLeft + plotWidth / 2;
      const y = paddingTop + plotHeight - ((val - minVal) / (maxVal - minVal || 1)) * plotHeight;
      return { x, y, point: p, val };
    });

    let linePath = "";
    if (coords.length > 0) {
      linePath = `M ${coords[0].x} ${coords[0].y}`;
      for (let i = 1; i < coords.length; i++) {
        const prev = coords[i - 1];
        const curr = coords[i];
        const cp1x = prev.x + (curr.x - prev.x) / 2;
        const cp1y = prev.y;
        const cp2x = prev.x + (curr.x - prev.x) / 2;
        const cp2y = curr.y;
        linePath += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${curr.x} ${curr.y}`;
      }
    }

    const areaPath =
      coords.length > 0
        ? `${linePath} L ${coords[coords.length - 1].x} ${paddingTop + plotHeight} L ${
            coords[0].x
          } ${paddingTop + plotHeight} Z`
        : "";

    // 4 vạch chia trục Y
    const yTicks = [0, 0.33, 0.66, 1].map((pct) => {
      const val = Math.round(minVal + pct * (maxVal - minVal));
      const y = paddingTop + plotHeight - pct * plotHeight;
      return {
        y,
        label:
          activeTab === "revenue"
            ? val >= 1000000
              ? `${(val / 1000000).toFixed(1)}Tr`
              : val >= 1000
              ? `${Math.round(val / 1000)}k`
              : `${val}`
            : `${val}`,
      };
    });

    return {
      width,
      height,
      paddingLeft,
      paddingTop,
      plotWidth,
      plotHeight,
      coords,
      linePath,
      areaPath,
      yTicks,
      maxVal,
    };
  }, [data, activeTab]);

  // Phân tích so sánh 2 phòng
  const roomComparisonText = useMemo(() => {
    if (!data?.room_occupancy || data.room_occupancy.length < 2) return null;
    const r1 = data.room_occupancy.find((r) => r.room_name === "ROOM_1");
    const r2 = data.room_occupancy.find((r) => r.room_name === "ROOM_2");
    if (!r1 || !r2) return null;

    if (r2.occupancy_rate > r1.occupancy_rate) {
      const diff = (r2.occupancy_rate - r1.occupancy_rate).toFixed(1);
      return `Phòng VIP (ROOM_2) đang dẫn đầu với tỷ lệ lấp đầy cao hơn ${diff}% so với phòng tiêu chuẩn.`;
    } else if (r1.occupancy_rate > r2.occupancy_rate) {
      const diff = (r1.occupancy_rate - r2.occupancy_rate).toFixed(1);
      return `Phòng tiêu chuẩn (ROOM_1) có tỷ lệ lấp đầy cao hơn ${diff}% so với phòng VIP.`;
    }
    return "Cả 2 phòng chiếu đang có tỷ lệ lấp đầy cân bằng nhau.";
  }, [data]);

  return (
    <div className="analytics-page">
      {/* Header & Controls */}
      <div className="analytics-header">
        <div className="analytics-header__title-group">
          <div className="analytics-badge">
            <BarChart3 size={16} />
            <span>Trung Tâm Báo Cáo & Quản Trị</span>
          </div>
          <h1 className="analytics-header__title">Thống Kê Doanh Thu & Hiệu Suất</h1>
          <p className="analytics-header__subtitle">
            Theo dõi doanh thu bán vé thực tế, tỷ lệ lấp đầy phòng chiếu và xu hướng tiêu dùng theo thời gian thực.
          </p>
        </div>

        <div className="analytics-header__actions">
          {/* Filter chuyển đổi thời gian */}
          <div className="filter-button-group" role="group" aria-label="Bộ lọc thời gian">
            <button
              type="button"
              className={`filter-btn ${daysFilter === 7 ? "filter-btn--active" : ""}`}
              onClick={() => setDaysFilter(7)}
            >
              7 ngày qua
            </button>
            <button
              type="button"
              className={`filter-btn ${daysFilter === 30 ? "filter-btn--active" : ""}`}
              onClick={() => setDaysFilter(30)}
            >
              30 ngày qua
            </button>
            <button
              type="button"
              className={`filter-btn ${daysFilter === 0 ? "filter-btn--active" : ""}`}
              onClick={() => setDaysFilter(0)}
            >
              Toàn thời gian
            </button>
          </div>

          <button
            type="button"
            className="refresh-btn"
            onClick={() => fetchAnalytics(daysFilter)}
            disabled={loading}
            title="Làm mới dữ liệu"
          >
            <RefreshCw size={17} className={loading ? "spin" : ""} />
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      {error ? (
        <div className="analytics-error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      ) : null}

      {/* KPI Stat Cards */}
      <div className="kpi-grid">
        {/* Card 1: Tổng doanh thu */}
        <div className="kpi-card kpi-card--revenue">
          <div className="kpi-card__glow" />
          <div className="kpi-card__header">
            <span className="kpi-card__label">Tổng Doanh Thu</span>
            <div className="kpi-card__icon kpi-card__icon--revenue">
              <DollarSign size={22} />
            </div>
          </div>
          <div className="kpi-card__value">
            {loading && !data ? (
              <span className="skeleton-text" />
            ) : (
              formatCurrency(data?.summary.total_revenue ?? 0)
            )}
          </div>
          <div className="kpi-card__footer">
            <span className="kpi-badge kpi-badge--success">
              <Sparkles size={12} /> Doanh thu thực
            </span>
            <span className="kpi-card__subtext">Chỉ tính đơn CONFIRMED</span>
          </div>
        </div>

        {/* Card 2: Số vé đã bán */}
        <div className="kpi-card kpi-card--tickets">
          <div className="kpi-card__glow" />
          <div className="kpi-card__header">
            <span className="kpi-card__label">Số Vé Đã Bán</span>
            <div className="kpi-card__icon kpi-card__icon--tickets">
              <Ticket size={22} />
            </div>
          </div>
          <div className="kpi-card__value">
            {loading && !data ? (
              <span className="skeleton-text" />
            ) : (
              `${(data?.summary.total_tickets ?? 0).toLocaleString("vi-VN")} vé`
            )}
          </div>
          <div className="kpi-card__footer">
            <span className="kpi-badge kpi-badge--primary">
              {data?.summary.total_bookings ?? 0} đơn đặt
            </span>
            <span className="kpi-card__subtext">Ghế đã đặt thành công</span>
          </div>
        </div>

        {/* Card 3: Khách hàng mới */}
        <div className="kpi-card kpi-card--customers">
          <div className="kpi-card__glow" />
          <div className="kpi-card__header">
            <span className="kpi-card__label">Khách Hàng Đăng Ký</span>
            <div className="kpi-card__icon kpi-card__icon--customers">
              <Users size={22} />
            </div>
          </div>
          <div className="kpi-card__value">
            {loading && !data ? (
              <span className="skeleton-text" />
            ) : (
              `${(data?.summary.total_customers ?? 0).toLocaleString("vi-VN")} người`
            )}
          </div>
          <div className="kpi-card__footer">
            <span className="kpi-badge kpi-badge--info">Cộng đồng CineVerse</span>
            <span className="kpi-card__subtext">Tổng tài khoản thành viên</span>
          </div>
        </div>

        {/* Card 4: Tỷ lệ lấp đầy ghế */}
        <div className="kpi-card kpi-card--occupancy">
          <div className="kpi-card__glow" />
          <div className="kpi-card__header">
            <span className="kpi-card__label">Tỷ Lệ Lấp Đầy Ghế TB</span>
            <div className="kpi-card__icon kpi-card__icon--occupancy">
              <TrendingUp size={22} />
            </div>
          </div>
          <div className="kpi-card__value">
            {loading && !data ? (
              <span className="skeleton-text" />
            ) : (
              `${data?.summary.average_occupancy_rate ?? 0}%`
            )}
          </div>
          <div className="kpi-card__footer">
            <div className="kpi-mini-progress">
              <div
                className="kpi-mini-progress__bar"
                style={{ width: `${Math.min(100, data?.summary.average_occupancy_rate ?? 0)}%` }}
              />
            </div>
            <span className="kpi-card__subtext">Toàn bộ suất chiếu</span>
          </div>
        </div>
      </div>

      {/* Biểu đồ Doanh thu trực quan (Revenue Trend Chart) */}
      <div className="dashboard-section chart-card">
        <div className="chart-card__header">
          <div>
            <h2 className="section-title">
              <BarChart3 size={20} className="section-title__icon" />
              Biến Động Doanh Thu & Số Vé Theo Ngày
            </h2>
            <p className="section-subtitle">
              Biểu đồ trực quan đường sóng thể hiện hiệu suất tài chính theo chu kỳ đã chọn.
            </p>
          </div>

          <div className="chart-tabs">
            <button
              type="button"
              className={`chart-tab ${activeTab === "revenue" ? "chart-tab--active" : ""}`}
              onClick={() => setActiveTab("revenue")}
            >
              <DollarSign size={15} />
              Doanh thu (VNĐ)
            </button>
            <button
              type="button"
              className={`chart-tab ${activeTab === "tickets" ? "chart-tab--active" : ""}`}
              onClick={() => setActiveTab("tickets")}
            >
              <Ticket size={15} />
              Số lượng vé
            </button>
          </div>
        </div>

        {/* Khung vẽ biểu đồ SVG */}
        <div className="chart-canvas-container">
          {chartData && chartData.coords.length > 0 ? (
            <div className="svg-wrapper">
              <svg
                viewBox={`0 0 ${chartData.width} ${chartData.height}`}
                className="revenue-chart-svg"
                preserveAspectRatio="xMidYMid meet"
              >
                <defs>
                  <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor={activeTab === "revenue" ? "#e11d48" : "#38bdf8"}
                      stopOpacity="0.45"
                    />
                    <stop
                      offset="100%"
                      stopColor={activeTab === "revenue" ? "#e11d48" : "#38bdf8"}
                      stopOpacity="0.0"
                    />
                  </linearGradient>
                  <filter id="glow">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {/* Grid lines ngang & nhãn trục Y */}
                {chartData.yTicks.map((tick, i) => (
                  <g key={i}>
                    <line
                      x1={chartData.paddingLeft}
                      y1={tick.y}
                      x2={chartData.width - 25}
                      y2={tick.y}
                      stroke="rgba(255, 255, 255, 0.08)"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={chartData.paddingLeft - 10}
                      y={tick.y + 4}
                      fill="var(--text-dim)"
                      fontSize="11"
                      textAnchor="end"
                    >
                      {tick.label}
                    </text>
                  </g>
                ))}

                {/* Vùng bóng Area Gradient */}
                {chartData.areaPath && (
                  <path d={chartData.areaPath} fill="url(#chartGradient)" />
                )}

                {/* Đường cong Line Chart */}
                {chartData.linePath && (
                  <path
                    d={chartData.linePath}
                    fill="none"
                    stroke={activeTab === "revenue" ? "#e11d48" : "#38bdf8"}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    filter="url(#glow)"
                  />
                )}

                {/* Các điểm dữ liệu & nhãn ngày */}
                {chartData.coords.map((c, i) => {
                  const isHovered = hoveredPoint?.date === c.point.date;
                  const showDateLabel =
                    chartData.coords.length <= 10 ||
                    i === 0 ||
                    i === chartData.coords.length - 1 ||
                    i % Math.ceil(chartData.coords.length / 7) === 0;

                  return (
                    <g key={c.point.date}>
                      {/* Vạch kẻ trục X */}
                      {showDateLabel && (
                        <text
                          x={c.x}
                          y={chartData.height - 12}
                          fill="var(--text-muted)"
                          fontSize="11"
                          textAnchor="middle"
                        >
                          {c.point.date.slice(5)}
                        </text>
                      )}

                      {/* Vùng cảm ứng hover */}
                      <circle
                        cx={c.x}
                        cy={c.y}
                        r="18"
                        fill="transparent"
                        className="interactive-point"
                        onMouseEnter={(e) => {
                          setHoveredPoint(c.point);
                          const rect = e.currentTarget.getBoundingClientRect();
                          setTooltipPos({ x: rect.left + rect.width / 2, y: rect.top });
                        }}
                        onMouseLeave={() => {
                          setHoveredPoint(null);
                          setTooltipPos(null);
                        }}
                      />

                      {/* Điểm hiển thị tròn */}
                      <circle
                        cx={c.x}
                        cy={c.y}
                        r={isHovered ? 6 : 4}
                        fill={isHovered ? "#ffffff" : activeTab === "revenue" ? "#e11d48" : "#38bdf8"}
                        stroke="#0f172a"
                        strokeWidth="2.5"
                        style={{ transition: "all 0.15s ease" }}
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Tooltip khi di chuột */}
              {hoveredPoint && tooltipPos && (
                <div
                  className="chart-tooltip"
                  style={{
                    left: `${tooltipPos.x}px`,
                    top: `${tooltipPos.y - 12}px`,
                  }}
                >
                  <div className="chart-tooltip__date">
                    <Calendar size={13} />
                    <span>{formatDate(hoveredPoint.date)}</span>
                  </div>
                  <div className="chart-tooltip__row">
                    <span className="tooltip-label">Doanh thu:</span>
                    <strong className="tooltip-val tooltip-val--revenue">
                      {formatCurrency(hoveredPoint.revenue)}
                    </strong>
                  </div>
                  <div className="chart-tooltip__row">
                    <span className="tooltip-label">Vé bán ra:</span>
                    <strong className="tooltip-val tooltip-val--tickets">
                      {hoveredPoint.tickets} vé
                    </strong>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="chart-empty">
              <Calendar size={36} className="chart-empty__icon" />
              <p>Chưa có dữ liệu doanh thu trong khoảng thời gian này</p>
            </div>
          )}
        </div>
      </div>

      {/* Hàng 2 cột: Top Phim & Thước đo phòng chiếu */}
      <div className="analytics-two-columns">
        {/* Cột 1: Top Phim ăn khách */}
        <div className="dashboard-section top-movies-card">
          <div className="section-header-flex">
            <div>
              <h2 className="section-title">
                <Award size={20} className="section-title__icon section-title__icon--gold" />
                Top Phim Ăn Khách Nhất
              </h2>
              <p className="section-subtitle">Xếp hạng phim đóng góp doanh thu lớn nhất</p>
            </div>
            <span className="movie-count-badge">
              {data?.top_movies.length ?? 0} phim
            </span>
          </div>

          <div className="top-movies-list">
            {!data?.top_movies || data.top_movies.length === 0 ? (
              <div className="empty-substate">
                <Film size={32} />
                <p>Chưa có dữ liệu phim được đặt vé trong giai đoạn này</p>
              </div>
            ) : (
              (() => {
                const maxMovieRev = Math.max(
                  ...data.top_movies.map((m) => m.total_revenue),
                  1
                );

                return data.top_movies.map((movie, idx) => {
                  const percent = Math.round((movie.total_revenue / maxMovieRev) * 100);
                  const rankClass =
                    idx === 0
                      ? "rank-badge--gold"
                      : idx === 1
                      ? "rank-badge--silver"
                      : idx === 2
                      ? "rank-badge--bronze"
                      : "rank-badge--normal";

                  return (
                    <div key={movie.movie_id} className="top-movie-item">
                      <div className={`rank-badge ${rankClass}`}>{idx + 1}</div>

                      <div className="movie-thumb">
                        {movie.poster_url ? (
                          <img
                            src={movie.poster_url}
                            alt={movie.title}
                            className="movie-thumb__img"
                          />
                        ) : (
                          <div className="movie-thumb__placeholder">
                            <Film size={20} />
                          </div>
                        )}
                      </div>

                      <div className="movie-info-wrap">
                        <div className="movie-info-row">
                          <span className="movie-name" title={movie.title}>
                            {movie.title}
                          </span>
                          <span className="movie-revenue">
                            {formatCurrency(movie.total_revenue)}
                          </span>
                        </div>

                        <div className="movie-sub-row">
                          <span className="movie-tickets-count">
                            <Ticket size={13} /> {movie.tickets_sold} vé
                          </span>
                          <span className="movie-percent-text">{percent}% tỉ trọng</span>
                        </div>

                        <div className="movie-progress-bar">
                          <div
                            className="movie-progress-bar__fill"
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                });
              })()
            )}
          </div>
        </div>

        {/* Cột 2: Thước đo lấp đầy phòng chiếu (Room Occupancy Gauge) */}
        <div className="dashboard-section occupancy-card">
          <div className="section-header-flex">
            <div>
              <h2 className="section-title">
                <Armchair size={20} className="section-title__icon section-title__icon--accent" />
                Tỷ Lệ Lấp Đầy Phòng Chiếu
              </h2>
              <p className="section-subtitle">
                Hiệu suất khai thác ghế giữa phòng Tiêu chuẩn và VIP
              </p>
            </div>
          </div>

          <div className="rooms-container">
            {data?.room_occupancy.map((room) => {
              const isVip = room.room_name === "ROOM_2";
              const roomTitle = isVip ? "Phòng 2 (ROOM_2 - VIP)" : "Phòng 1 (ROOM_1 - Standard)";
              const roomDesc = isVip
                ? "Không gian sang trọng, ghế bọc da cao cấp"
                : "Phòng chiếu rộng rãi tiêu chuẩn âm thanh vòm";

              return (
                <div key={room.room_name} className="room-gauge-card">
                  <div className="room-gauge-card__head">
                    <div>
                      <div className="room-title">
                        {roomTitle}
                        {isVip ? (
                          <span className="badge-vip-pill">VIP Cinema</span>
                        ) : (
                          <span className="badge-standard-pill">Standard</span>
                        )}
                      </div>
                      <div className="room-desc">{roomDesc}</div>
                    </div>

                    <div className="occupancy-pct-badge">
                      <span className="occupancy-pct-val">{room.occupancy_rate}%</span>
                      <span className="occupancy-pct-lbl">lấp đầy</span>
                    </div>
                  </div>

                  {/* Thanh Gauge lấp đầy */}
                  <div className="room-gauge-bar">
                    <div
                      className={`room-gauge-bar__fill ${
                        isVip ? "room-gauge-bar__fill--vip" : "room-gauge-bar__fill--standard"
                      }`}
                      style={{ width: `${Math.min(100, room.occupancy_rate)}%` }}
                    />
                  </div>

                  <div className="room-metrics-row">
                    <div className="room-metric-col">
                      <span className="metric-lbl">Ghế đã đặt</span>
                      <strong className="metric-val">{room.booked_seats} ghế</strong>
                    </div>
                    <div className="room-metric-col">
                      <span className="metric-lbl">Sức chứa phục vụ</span>
                      <strong className="metric-val">{room.total_capacity} chỗ</strong>
                    </div>
                    <div className="room-metric-col">
                      <span className="metric-lbl">Quy mô phòng</span>
                      <strong className="metric-val">{room.total_seats} ghế/suất</strong>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {roomComparisonText && (
            <div className="room-insight-box">
              <Sparkles size={18} className="room-insight-box__icon" />
              <span>{roomComparisonText}</span>
            </div>
          )}
        </div>
      </div>

      {/* Bảng giao dịch đặt vé gần đây (Recent Bookings Table) */}
      <div className="dashboard-section recent-bookings-card">
        <div className="section-header-flex">
          <div>
            <h2 className="section-title">
              <Ticket size={20} className="section-title__icon" />
              Giao Dịch Đặt Vé Mới Nhất
            </h2>
            <p className="section-subtitle">
              Danh sách 10 giao dịch đặt vé gần đây nhất trong toàn hệ thống
            </p>
          </div>
          <span className="recent-badge">
            {data?.recent_bookings.length ?? 0} giao dịch gần đây
          </span>
        </div>

        <div className="table-responsive">
          <table className="recent-table">
            <thead>
              <tr>
                <th>Mã Đơn</th>
                <th>Khách Hàng</th>
                <th>Phim & Suất Chiếu</th>
                <th>Phòng & Ghế</th>
                <th>Tổng Tiền</th>
                <th>Trạng Thái</th>
                <th>Thời Gian Đặt</th>
              </tr>
            </thead>
            <tbody>
              {!data?.recent_bookings || data.recent_bookings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="table-empty-cell">
                    Chưa có giao dịch đặt vé nào được ghi nhận.
                  </td>
                </tr>
              ) : (
                data.recent_bookings.map((item) => (
                  <tr key={item.booking_id}>
                    <td>
                      <span className="booking-code">#{item.booking_id}</span>
                    </td>
                    <td>
                      <div className="customer-cell">
                        <strong className="customer-name">{item.customer_name}</strong>
                        <span className="customer-email">{item.customer_email}</span>
                      </div>
                    </td>
                    <td>
                      <div className="movie-showtime-cell">
                        <strong className="movie-title-text">{item.movie_title}</strong>
                        <span className="showtime-time-text">
                          {formatDateTime(item.showtime_start)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="seats-cell">
                        <span className="room-tag">{item.room_name}</span>
                        <div className="seat-labels-wrap">
                          {item.seat_labels.length > 0 ? (
                            item.seat_labels.map((lbl) => (
                              <span key={lbl} className="seat-pill">
                                {lbl}
                              </span>
                            ))
                          ) : (
                            <span className="seat-pill-empty">--</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <strong className="amount-text">
                        {formatCurrency(item.total_amount)}
                      </strong>
                    </td>
                    <td>
                      {item.status === "CONFIRMED" ? (
                        <span className="status-badge status-badge--confirmed">
                          <CheckCircle2 size={13} />
                          Đã Xác Nhận
                        </span>
                      ) : (
                        <span className="status-badge status-badge--cancelled">
                          <XCircle size={13} />
                          Đã Hủy
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="created-at-text">
                        {formatDateTime(item.created_at)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
export default AdminDashboardPage;

