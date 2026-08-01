import type { HTMLAttributes } from "react";

export function Card({ className = "", children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-card bg-white p-5 shadow-sm ring-1 ring-primary-100 ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
