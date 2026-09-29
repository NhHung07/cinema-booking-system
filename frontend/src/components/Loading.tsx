import { Loader2 } from "lucide-react";

export function Loading({ message = "Đang tải dữ liệu..." }: { message?: string }) {
  return (
    <div className="loading-container" role="status" aria-live="polite">
      <div className="loading-spinner-box">
        <Loader2 size={36} className="spinner-rotate" />
      </div>
      <p className="loading-text">{message}</p>
    </div>
  );
}
