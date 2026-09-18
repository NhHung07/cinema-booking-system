export function Loading({ message = "Đang tải dữ liệu..." }: { message?: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="loading__dot" />
      {message}
    </div>
  );
}
