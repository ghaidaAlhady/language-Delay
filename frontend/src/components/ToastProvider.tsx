import { useCallback, useMemo, useState, type ReactNode } from "react";

import { ToastContext, type ToastKind } from "@/components/ToastContext";

interface Toast {
  id: string;
  message: string;
  kind: ToastKind;
}

const KIND_CLASSES: Record<ToastKind, string> = {
  success: "bg-success-500 text-white",
  error: "bg-danger-500 text-white",
  info: "bg-primary-500 text-white",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, kind: ToastKind = "info") => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, kind }]);
    setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4000);
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-2 px-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-full px-5 py-2.5 text-sm font-medium shadow-lg ${KIND_CLASSES[toast.kind]}`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
