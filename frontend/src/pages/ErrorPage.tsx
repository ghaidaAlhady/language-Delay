import { Link, useRouteError } from "react-router-dom";

import { Button } from "@/components/Button";

/**
 * Route-level error boundary (`errorElement`). Never renders the raw error
 * message/stack — just a safe, generic Arabic message with recovery actions.
 */
export function ErrorPage() {
  useRouteError();

  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-24 text-center">
      <h1 className="text-xl font-semibold text-primary-900">حدث خطأ غير متوقع</h1>
      <p className="text-gray-600">نعتذر عن هذا الخلل. يرجى المحاولة مرة أخرى أو العودة إلى الرئيسية.</p>
      <div className="flex gap-3">
        <Button variant="outline" onClick={() => window.location.reload()}>
          إعادة المحاولة
        </Button>
        <Link to="/">
          <Button>الرئيسية</Button>
        </Link>
      </div>
    </div>
  );
}
