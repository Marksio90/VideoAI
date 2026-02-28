"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  FiHome,
  FiFilm,
  FiBarChart2,
  FiSettings,
  FiLogOut,
  FiPlay,
  FiLink,
} from "react-icons/fi";
import { useAuthStore } from "@/store/auth-store";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: FiHome },
  { href: "/series", label: "Serie", icon: FiFilm },
  { href: "/dashboard/videos", label: "Wideo", icon: FiPlay },
  { href: "/analytics", label: "Analityka", icon: FiBarChart2 },
  { href: "/settings", label: "Ustawienia", icon: FiSettings },
  { href: "/settings/connections", label: "Platformy", icon: FiLink },
];

export default function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-dark-700 border-r border-dark-400 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-dark-400">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white font-bold text-lg">
            A
          </div>
          <div>
            <div className="font-bold text-lg text-white">AutoShorts</div>
            <div className="text-xs text-dark-200">Generuj. Publikuj. Skaluj.</div>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-600/20 text-brand-400"
                  : "text-dark-100 hover:bg-dark-500 hover:text-white"
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User info */}
      <div className="p-4 border-t border-dark-400">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-brand-700 flex items-center justify-center text-sm font-bold text-white">
            {user?.full_name?.[0] || user?.email?.[0] || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">
              {user?.full_name || "Użytkownik"}
            </div>
            <div className="text-xs text-dark-200 truncate">{user?.email}</div>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-dark-200 hover:text-red-400 transition-colors w-full"
        >
          <FiLogOut className="w-4 h-4" />
          Wyloguj
        </button>
      </div>
    </aside>
  );
}
