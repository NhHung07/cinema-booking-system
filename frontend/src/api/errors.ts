import axios from "axios";

interface FastApiErrorBody {
  detail?: unknown;
}

export function getApiErrorMessage(error: unknown, fallback = "Đã có lỗi xảy ra."): string {
  if (!axios.isAxiosError<FastApiErrorBody>(error)) {
    return fallback;
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (!error.response) {
    return "Không thể kết nối đến backend. Hãy kiểm tra API có đang chạy không.";
  }

  const messages: Record<number, string> = {
    400: "Yêu cầu không hợp lệ.",
    401: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
    404: "Không tìm thấy dữ liệu yêu cầu.",
    409: "Dữ liệu vừa thay đổi. Vui lòng tải lại và thử lại.",
    422: "Dữ liệu nhập vào chưa hợp lệ.",
    500: "Server đang gặp lỗi. Vui lòng thử lại sau.",
  };
  return messages[error.response.status] ?? fallback;
}

export function getApiStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined;
}
