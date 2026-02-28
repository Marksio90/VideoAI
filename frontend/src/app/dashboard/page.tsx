"use client";

import { useQuery } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { analyticsApi, seriesApi, videosApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { FiFilm, FiEye, FiThumbsUp, FiPlay, FiTrendingUp, FiPlus } from "react-icons/fi";
import Link from "next/link";

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: any;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm text-dark-200">{label}</div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => analyticsApi.dashboard().then((r) => r.data),
  });

  const { data: recentVideos } = useQuery({
    queryKey: ["recent-videos"],
    queryFn: () => videosApi.list({ page: 1 }).then((r) => r.data),
  });

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">
          Witaj, {user?.full_name || "Uzytkowniku"}!
        </h1>
        <p className="text-dark-200 mt-1">
          Panel sterowania AutoShorts
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={FiFilm}
          label="Serie"
          value={stats?.total_series ?? 0}
          color="bg-brand-600"
        />
        <StatCard
          icon={FiPlay}
          label="Wideo"
          value={stats?.total_videos ?? 0}
          color="bg-purple-600"
        />
        <StatCard
          icon={FiEye}
          label="Wyswietlenia"
          value={stats?.total_views?.toLocaleString() ?? 0}
          color="bg-green-600"
        />
        <StatCard
          icon={FiThumbsUp}
          label="Polubienia"
          value={stats?.total_likes?.toLocaleString() ?? 0}
          color="bg-pink-600"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <Link href="/series?new=true" className="card hover:border-brand-600 transition-colors group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand-600/20 flex items-center justify-center group-hover:bg-brand-600 transition-colors">
              <FiPlus className="w-6 h-6 text-brand-400 group-hover:text-white" />
            </div>
            <div>
              <div className="font-semibold text-white">Nowa seria</div>
              <div className="text-sm text-dark-200">Utwórz nowa serie wideo</div>
            </div>
          </div>
        </Link>

        <Link href="/analytics" className="card hover:border-brand-600 transition-colors group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-green-600/20 flex items-center justify-center group-hover:bg-green-600 transition-colors">
              <FiTrendingUp className="w-6 h-6 text-green-400 group-hover:text-white" />
            </div>
            <div>
              <div className="font-semibold text-white">Analityka</div>
              <div className="text-sm text-dark-200">Statystyki i wyniki</div>
            </div>
          </div>
        </Link>
      </div>

      {/* Limits info */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-white mb-4">Uzycie limitu</h2>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-dark-200">Wideo w tym miesiacu</span>
              <span className="text-white">
                {user?.videos_generated_this_month ?? 0} / {user?.max_videos_per_month ?? 10}
              </span>
            </div>
            <div className="h-2 bg-dark-500 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-600 rounded-full transition-all"
                style={{
                  width: `${Math.min(
                    ((user?.videos_generated_this_month ?? 0) / (user?.max_videos_per_month ?? 10)) * 100,
                    100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Videos */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Ostatnie wideo</h2>
          <Link href="/dashboard/videos" className="text-sm text-brand-400 hover:text-brand-300">
            Zobacz wszystkie
          </Link>
        </div>

        {recentVideos?.items?.length ? (
          <div className="space-y-3">
            {recentVideos.items.slice(0, 5).map((video) => (
              <div
                key={video.id}
                className="flex items-center justify-between py-3 border-b border-dark-400 last:border-0"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">
                    {video.title || `Odcinek ${video.episode_number}`}
                  </div>
                  <div className="text-xs text-dark-200">
                    {new Date(video.created_at).toLocaleDateString("pl-PL")}
                  </div>
                </div>
                <StatusBadge status={video.status} />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-dark-200 text-sm text-center py-8">
            Brak wideo. Utwórz pierwsza serie, aby zaczac!
          </p>
        )}
      </div>
    </DashboardLayout>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-gray-600/30 text-gray-300",
    generating_script: "bg-blue-600/30 text-blue-300",
    generating_hook: "bg-blue-600/30 text-blue-300",
    generating_voice: "bg-purple-600/30 text-purple-300",
    fetching_media: "bg-yellow-600/30 text-yellow-300",
    rendering: "bg-orange-600/30 text-orange-300",
    ready_for_review: "bg-cyan-600/30 text-cyan-300",
    approved: "bg-brand-600/30 text-brand-300",
    publishing: "bg-amber-600/30 text-amber-300",
    published: "bg-green-600/30 text-green-300",
    failed: "bg-red-600/30 text-red-300",
    cancelled: "bg-dark-400/30 text-dark-200",
  };

  const labels: Record<string, string> = {
    pending: "Oczekuje",
    generating_script: "Generuje skrypt",
    generating_hook: "Generuje hook",
    generating_voice: "Generuje glos",
    fetching_media: "Pobiera media",
    rendering: "Renderuje",
    ready_for_review: "Do akceptacji",
    approved: "Zatwierdzony",
    publishing: "Publikowanie",
    published: "Opublikowany",
    failed: "Blad",
    cancelled: "Anulowany",
  };

  return (
    <span className={`status-badge ${colors[status] || "bg-gray-600/30 text-gray-300"}`}>
      {labels[status] || status}
    </span>
  );
}
