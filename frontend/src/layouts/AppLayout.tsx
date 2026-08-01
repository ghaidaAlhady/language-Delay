import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Logo } from "@/components/Logo";
import { useAuth } from "@/features/auth/useAuth";

const NAV_LINKS = [
  { to: "/dashboard", label: "الرئيسية" },
  { to: "/children", label: "أطفالي" },
  { to: "/profile", label: "الإعدادات" },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout(): Promise<void> {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-primary-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <NavLink to="/dashboard" className="flex items-center gap-2 font-bold text-primary-700">
            <Logo />
            <span className="hidden sm:inline">المرشد الذكي</span>
          </NavLink>

          <nav className="flex flex-wrap items-center gap-1 text-sm font-medium" aria-label="التنقل الرئيسي">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-2 transition-colors ${
                    isActive ? "bg-primary-500 text-white" : "text-primary-700 hover:bg-primary-50"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3 text-sm">
            {user && <span className="hidden text-gray-600 sm:inline">مرحبًا، {user.display_name}</span>}
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="rounded-full border border-primary-200 px-3 py-2 font-medium text-primary-700 hover:bg-primary-50"
            >
              تسجيل الخروج
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
