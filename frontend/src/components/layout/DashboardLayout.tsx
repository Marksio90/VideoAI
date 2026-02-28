"use client";

import { useAuthStore } from "@/store/auth-store";
import { redirect } from "next/navigation";
import Sidebar from "./Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) {
    redirect("/auth");
  }

  return (
    <div className="min-h-screen bg-dark-900">
      <Sidebar />
      <main className="ml-64 p-8">{children}</main>
    </div>
  );
}
