import { Link } from "react-router-dom";

import { Button } from "@/components/Button";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-24 text-center">
      <p className="text-6xl font-bold text-primary-300">404</p>
      <h1 className="text-xl font-semibold text-primary-900">الصفحة غير موجودة</h1>
      <p className="text-gray-600">الصفحة التي تبحث عنها غير موجودة أو تم نقلها.</p>
      <Link to="/">
        <Button>العودة إلى الرئيسية</Button>
      </Link>
    </div>
  );
}
