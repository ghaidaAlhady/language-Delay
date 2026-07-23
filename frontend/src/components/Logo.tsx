/** Original mark — not a reproduction of any third-party asset. */
export function Logo({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} role="img" aria-label="المرشد الذكي">
      <circle cx="20" cy="20" r="19" fill="var(--color-secondary-400)" />
      <path d="M20 33a13 13 0 1 1 13-13 13 13 0 0 1-13 13Z" fill="var(--color-primary-500)" />
      <path
        d="M20 6v4M12.5 8.5l2 3.5M27.5 8.5l-2 3.5M9 15l3.5 2"
        stroke="var(--color-primary-500)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
