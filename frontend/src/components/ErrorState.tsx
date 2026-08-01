import { Button } from "@/components/Button";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-card bg-danger-50 px-6 py-10 text-center"
    >
      <p className="text-base font-medium text-danger-600">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          إعادة المحاولة
        </Button>
      )}
    </div>
  );
}
