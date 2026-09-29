export function formatDate(value: string | null | undefined): string {
  if (!value) return "Chưa có ngày";
  try {
    const date = new Date(value.includes("T") ? value : `${value}T00:00:00`);
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  } catch {
    return value;
  }
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Không có dữ liệu";
  }
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatTimeOnly(value: string | null | undefined): string {
  if (!value) return "--:--";
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(value));
  } catch {
    return "--:--";
  }
}

export function formatDayOfWeek(value: string | null | undefined): string {
  if (!value) return "";
  try {
    const d = new Date(value);
    const today = new Date();
    const isToday =
      d.getDate() === today.getDate() &&
      d.getMonth() === today.getMonth() &&
      d.getFullYear() === today.getFullYear();

    if (isToday) return "Hôm nay";

    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const isTomorrow =
      d.getDate() === tomorrow.getDate() &&
      d.getMonth() === tomorrow.getMonth() &&
      d.getFullYear() === tomorrow.getFullYear();

    if (isTomorrow) return "Ngày mai";

    return new Intl.DateTimeFormat("vi-VN", { weekday: "short" }).format(d);
  } catch {
    return "";
  }
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(amount);
}

export function calculateEndTime(startTimeStr: string, durationMinutes: number): string {
  try {
    const start = new Date(startTimeStr);
    const end = new Date(start.getTime() + durationMinutes * 60 * 1000);
    return formatTimeOnly(end.toISOString());
  } catch {
    return "";
  }
}
