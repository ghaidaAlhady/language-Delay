import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card bg-primary-50 px-6 py-12 text-center">
      {icon}
      <p className="text-lg font-semibold text-primary-900">{title}</p>
      {description && <p className="text-sm text-gray-600">{description}</p>}
      {action}
    </div>
  );
}
