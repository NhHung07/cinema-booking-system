interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="alert alert--error" role="alert">
      <span>{message}</span>
      {onRetry ? (
        <button className="button button--secondary button--small" type="button" onClick={onRetry}>
          Thử lại
        </button>
      ) : null}
    </div>
  );
}
