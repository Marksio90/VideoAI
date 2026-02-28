"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { publishingApi, usersApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import toast from "react-hot-toast";
import { FiUser, FiLink, FiCreditCard, FiTrash2 } from "react-icons/fi";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const [fullName, setFullName] = useState(user?.full_name || "");

  const updateMutation = useMutation({
    mutationFn: (data: { full_name: string }) => usersApi.updateMe(data),
    onSuccess: () => {
      fetchUser();
      toast.success("Profil zaktualizowany");
    },
  });

  const { data: connections } = useQuery({
    queryKey: ["connections"],
    queryFn: () => publishingApi.listConnections().then((r) => r.data),
  });

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Ustawienia</h1>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Profile */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <FiUser className="w-5 h-5 text-brand-400" />
            <h2 className="text-lg font-semibold text-white">Profil</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="label">E-mail</label>
              <input className="input-field" value={user?.email || ""} disabled />
            </div>
            <div>
              <label className="label">Imie i nazwisko</label>
              <input
                className="input-field"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
            <button
              onClick={() => updateMutation.mutate({ full_name: fullName })}
              className="btn-primary"
              disabled={updateMutation.isPending}
            >
              Zapisz zmiany
            </button>
          </div>
        </div>

        {/* Connected Platforms */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <FiLink className="w-5 h-5 text-brand-400" />
            <h2 className="text-lg font-semibold text-white">Podlaczone platformy</h2>
          </div>

          <div className="space-y-3">
            {["youtube", "tiktok", "instagram"].map((platform) => {
              const conn = connections?.find((c) => c.platform === platform);
              return (
                <div
                  key={platform}
                  className="flex items-center justify-between py-3 border-b border-dark-400 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-dark-500 flex items-center justify-center text-sm font-bold text-white uppercase">
                      {platform[0]}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white capitalize">{platform}</div>
                      {conn ? (
                        <div className="text-xs text-green-400">
                          Polaczony ({conn.platform_username || conn.channel_name || "aktywny"})
                        </div>
                      ) : (
                        <div className="text-xs text-dark-200">Niepodlaczony</div>
                      )}
                    </div>
                  </div>
                  {conn ? (
                    <button className="btn-secondary text-sm text-red-400 hover:border-red-500">
                      Odlacz
                    </button>
                  ) : (
                    <button className="btn-primary text-sm">Polacz</button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Subscription */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <FiCreditCard className="w-5 h-5 text-brand-400" />
            <h2 className="text-lg font-semibold text-white">Subskrypcja</h2>
          </div>

          <div className="bg-dark-800 rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-dark-200">Aktualny plan</div>
                <div className="text-xl font-bold text-white">
                  {user?.max_videos_per_month === 3 ? "Free" : "Pro"}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-dark-200">Limit</div>
                <div className="text-lg font-semibold text-white">
                  {user?.max_videos_per_month} wideo/mc
                </div>
              </div>
            </div>
          </div>

          <button className="btn-primary w-full">Ulepsz plan</button>
        </div>

        {/* Danger Zone */}
        <div className="card border-red-900/50">
          <div className="flex items-center gap-3 mb-4">
            <FiTrash2 className="w-5 h-5 text-red-400" />
            <h2 className="text-lg font-semibold text-red-400">Strefa niebezpieczna</h2>
          </div>
          <p className="text-sm text-dark-200 mb-4">
            Usuniecie konta jest nieodwracalne. Wszystkie dane zostana utracone.
          </p>
          <button className="btn-danger">Usun konto</button>
        </div>
      </div>
    </DashboardLayout>
  );
}
