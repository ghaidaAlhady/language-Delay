interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "h-4 w-full" }: SkeletonProps) {
  return <div className={`animate-pulse rounded-md bg-primary-100 ${className}`} aria-hidden="true" />;
}

export function SkeletonCard() {
  return (
    <div className="flex flex-col gap-3 rounded-card bg-white p-5 shadow-sm ring-1 ring-primary-100">
      <Skeleton className="h-5 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
    </div>
  );
}
