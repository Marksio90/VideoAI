"use client";

import { useQuery } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { analyticsApi } from "@/lib/api";
import { FiTrendingUp, FiEye, FiThumbsUp, FiClock } from "react-icons/fi";

export default function AnalyticsPage() {
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => analyticsApi.dashboard().then((r) => r.data),
  });

  const { data: seriesStats } = useQuery({
    queryKey: ["series-stats"],
    queryFn: () => analyticsApi.seriesStats().then((r) => r.data),
  });

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Analityka</h1>
        <p className="text-dark-200 mt-1">Statystyki i wyniki Twoich wideo</p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <FiEye className="w-5 h-5 text-green-400" />
            <span className="text-sm text-dark-200">Lacznie wysw.</span>
          </div>
          <div className="text-3xl font-bold text-white">
            {stats?.total_views?.toLocaleString() ?? 0}
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <FiThumbsUp className="w-5 h-5 text-pink-400" />
            <span className="text-sm text-dark-200">Polubienia</span>
          </div>
          <div className="text-3xl font-bold text-white">
            {stats?.total_likes?.toLocaleString() ?? 0}
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <FiTrendingUp className="w-5 h-5 text-brand-400" />
            <span className="text-sm text-dark-200">Sr. retencja</span>
          </div>
          <div className="text-3xl font-bold text-white">
            {stats?.avg_retention_rate ?? 0}%
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <FiClock className="w-5 h-5 text-yellow-400" />
            <span className="text-sm text-dark-200">Wideo / mc</span>
          </div>
          <div className="text-3xl font-bold text-white">
            {stats?.videos_this_month ?? 0}
          </div>
        </div>
      </div>

      {/* Series Table */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Wyniki per seria</h2>
        {seriesStats?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-400 text-left text-sm text-dark-200">
                  <th className="py-3 pr-4">Seria</th>
                  <th className="py-3 pr-4">Odcinki</th>
                  <th className="py-3 pr-4">Opublikowane</th>
                  <th className="py-3 pr-4">Wyswietlenia</th>
                  <th className="py-3 pr-4">Sr. wysw.</th>
                  <th className="py-3">Polubienia</th>
                </tr>
              </thead>
              <tbody>
                {seriesStats.map((s: any) => (
                  <tr key={s.series_id} className="border-b border-dark-500 last:border-0">
                    <td className="py-3 pr-4 text-white font-medium">{s.title}</td>
                    <td className="py-3 pr-4 text-dark-200">{s.total_episodes}</td>
                    <td className="py-3 pr-4 text-dark-200">{s.published}</td>
                    <td className="py-3 pr-4 text-white">{s.total_views.toLocaleString()}</td>
                    <td className="py-3 pr-4 text-dark-200">{s.avg_views.toLocaleString()}</td>
                    <td className="py-3 text-dark-200">{s.total_likes.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-dark-200 text-sm text-center py-8">
            Brak danych. Opublikuj wideo, aby zobaczyc statystyki.
          </p>
        )}
      </div>
    </DashboardLayout>
  );
}
