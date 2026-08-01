import type { ReactNode } from "react";

interface StaticContentPageProps {
  title: string;
  children: ReactNode;
}

export function StaticContentPage({ title, children }: StaticContentPageProps) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="mb-6 text-2xl font-bold text-primary-900">{title}</h1>
      <div className="flex flex-col gap-4 leading-relaxed text-gray-700 [&_h2]:mt-4 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-primary-900">
        {children}
      </div>
    </div>
  );
}
