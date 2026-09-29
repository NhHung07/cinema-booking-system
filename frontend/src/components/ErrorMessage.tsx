import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="alert alert--error" role="alert">
      <div className="alert-content">
        <AlertTriangle size={20} className="alert-icon" />
        <span>{message}</span>
      </div>
      {onRetry ? (
        <button
          className="button button--secondary button--small"
          type="button"
          onClick={onRetry}
        >
          <RotateCcw size={14} />
          <span>Thử lại</span>
        </button>
      ) : null}
    </div>
  );
}
