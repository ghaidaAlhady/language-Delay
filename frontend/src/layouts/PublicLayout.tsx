import { Link, Outlet } from "react-router-dom";

import { Logo } from "@/components/Logo";
import { useAuth } from "@/features/auth/useAuth";

const NAV_LINKS = [
  { to: "/about", label: "عن المرشد الذكي" },
  { to: "/how-it-works", label: "كيف يعمل النظام" },
  { to: "/privacy", label: "الخصوصية" },
  { to: "/disclaimer", label: "إخلاء المسؤولية" },
];

export function PublicLayout() {
  const { status } = useAuth();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-primary-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 font-bold text-primary-700">
            <Logo />
            <span>المرشد الذكي</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-4 text-sm text-primary-700">
            {NAV_LINKS.map((link) => (
              <Link key={link.to} to={link.to} className="hover:text-primary-500">
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            {status === "authenticated" ? (
              <Link
                to="/dashboard"
                className="rounded-full bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600"
              >
                لوحة التحكم
              </Link>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-primary-700 hover:text-primary-500">
                  تسجيل الدخول
                </Link>
                <Link
                  to="/register"
                  className="rounded-full bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600"
                >
                  إنشاء حساب
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-primary-100 bg-white px-4 py-6 text-center text-sm text-gray-500">
        <p>
          هذا التطبيق أداة داعمة لولي الأمر ولا يغني عن التقييم أو العلاج من قبل أخصائي تخاطب
          مؤهل، ولا يقدّم تشخيصًا طبيًا.
        </p>
      </footer>
    </div>
  );
}
