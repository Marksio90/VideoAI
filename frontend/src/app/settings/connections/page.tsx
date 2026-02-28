"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { publishingApi } from "@/lib/api";
import toast from "react-hot-toast";
import { FiLink, FiUnlink, FiYoutube } from "react-icons/fi";

const PLATFORMS = [
  {
    id: "youtube",
    name: "YouTube",
    description: "Publikuj jako YouTube Shorts",
    color: "bg-red-600",
  },
  {
    id: "tiktok",
    name: "TikTok",
    description: "Publikuj filmy na TikToku",
    color: "bg-black",
  },
  {
    id: "instagram",
    name: "Instagram",
    description: "Publikuj jako Instagram Reels",
    color: "bg-gradient-to-r from-purple-600 to-pink-600",
  },
];

export default function ConnectionsPage() {
  const queryClient = useQueryClient();

  const { data: connections, isLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: () => publishingApi.listConnections().then((r) => r.data),
  });

  const disconnectMutation = useMutation({
    mutationFn: (id: string) => publishingApi.disconnect(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connections"] });
      toast.success("Platforma odlaczona");
    },
  });

  const getConnection = (platformId: string) =>
    connections?.find((c) => c.platform === platformId && c.is_active);

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Polaczenia z platformami</h1>
        <p className="text-dark-200 mt-1">
          Polacz swoje konta, aby automatycznie publikowac wideo
        </p>
      </div>

      <div className="max-w-2xl space-y-4">
        {PLATFORMS.map((platform) => {
          const conn = getConnection(platform.id);

          return (
            <div key={platform.id} className="card">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={`w-12 h-12 rounded-xl ${platform.color} flex items-center justify-center text-white font-bold text-lg`}
                  >
                    {platform.name[0]}
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{platform.name}</h3>
                    <p className="text-sm text-dark-200">{platform.description}</p>
                    {conn && (
                      <p className="text-xs text-green-400 mt-1">
                        Polaczony: {conn.platform_username || conn.channel_name || "aktywny"}
                      </p>
                    )}
                  </div>
                </div>

                <div>
                  {conn ? (
                    <button
                      onClick={() => disconnectMutation.mutate(conn.id)}
                      className="btn-secondary text-sm flex items-center gap-2 text-red-400 hover:border-red-500"
                    >
                      <FiUnlink className="w-4 h-4" />
                      Odlacz
                    </button>
                  ) : (
                    <button
                      onClick={() =>
                        toast("Przekierowanie do autoryzacji " + platform.name, {
                          icon: "🔗",
                        })
                      }
                      className="btn-primary text-sm flex items-center gap-2"
                    >
                      <FiLink className="w-4 h-4" />
                      Polacz
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info */}
      <div className="max-w-2xl mt-8 p-4 bg-dark-600 rounded-lg border border-dark-400">
        <h3 className="text-sm font-semibold text-dark-100 mb-2">Jak to dziala?</h3>
        <ol className="text-sm text-dark-200 space-y-1 list-decimal list-inside">
          <li>Kliknij "Polacz" przy wybranej platformie</li>
          <li>Zaloguj sie na swoje konto platformy</li>
          <li>Zezwol AutoShorts na publikowanie w Twoim imieniu</li>
          <li>Gotowe! Wideo beda automatycznie publikowane wg harmonogramu</li>
        </ol>
      </div>
    </DashboardLayout>
  );
}
