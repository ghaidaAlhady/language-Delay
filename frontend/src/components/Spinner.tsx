interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
}

const SIZE_PX: Record<NonNullable<SpinnerProps["size"]>, string> = {
  sm: "h-4 w-4 border-2",
  md: "h-8 w-8 border-2",
  lg: "h-12 w-12 border-4",
};

export function Spinner({ size = "md", label = "جارٍ التحميل..." }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={`inline-block animate-spin rounded-full border-current border-t-transparent text-primary-500 ${SIZE_PX[size]}`}
    >
      <span className="sr-only">{label}</span>
    </span>
  );
}
