"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { videosApi } from "@/lib/api";
import type { Video, VideoStatus } from "@/types";
import toast from "react-hot-toast";
import { FiPlay, FiCheck, FiRefreshCw, FiExternalLink, FiEdit } from "react-icons/fi";

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Wszystkie" },
  { value: "pending", label: "Oczekujace" },
  { value: "ready_for_review", label: "Do akceptacji" },
  { value: "approved", label: "Zatwierdzone" },
  { value: "published", label: "Opublikowane" },
  { value: "failed", label: "Bledy" },
];

export default function VideosPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["videos", statusFilter],
    queryFn: () =>
      videosApi.list({ status_filter: statusFilter || undefined }).then((r) => r.data),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, channels }: { id: string; channels: string[] }) =>
      videosApi.approve(id, channels),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      toast.success("Wideo zatwierdzone do publikacji!");
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: (id: string) => videosApi.regenerate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      toast.success("Ponowna generacja uruchomiona");
    },
  });

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Wideo</h1>
        <p className="text-dark-200 mt-1">Zarzadzaj wygenerowanymi filmami</p>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-brand-600 text-white"
                : "bg-dark-600 text-dark-200 hover:text-white"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Video List */}
      {isLoading ? (
        <div className="text-center py-12 text-dark-200">Ladowanie...</div>
      ) : data?.items?.length ? (
        <div className="space-y-3">
          {data.items.map((video) => (
            <VideoRow
              key={video.id}
              video={video}
              onApprove={(channels) => approveMutation.mutate({ id: video.id, channels })}
              onRegenerate={() => regenerateMutation.mutate(video.id)}
              onSelect={() => setSelectedVideo(video)}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-16">
          <p className="text-dark-200">Brak wideo z tym filtrem</p>
        </div>
      )}

      {/* Video Detail Modal */}
      {selectedVideo && (
        <VideoDetailModal video={selectedVideo} onClose={() => setSelectedVideo(null)} />
      )}
    </DashboardLayout>
  );
}

function VideoRow({
  video,
  onApprove,
  onRegenerate,
  onSelect,
}: {
  video: Video;
  onApprove: (channels: string[]) => void;
  onRegenerate: () => void;
  onSelect: () => void;
}) {
  const statusColors: Record<string, string> = {
    pending: "bg-gray-600/30 text-gray-300",
    generating_script: "bg-blue-600/30 text-blue-300 animate-pulse",
    generating_hook: "bg-blue-600/30 text-blue-300 animate-pulse",
    generating_voice: "bg-purple-600/30 text-purple-300 animate-pulse",
    fetching_media: "bg-yellow-600/30 text-yellow-300 animate-pulse",
    rendering: "bg-orange-600/30 text-orange-300 animate-pulse",
    ready_for_review: "bg-cyan-600/30 text-cyan-300",
    approved: "bg-brand-600/30 text-brand-300",
    published: "bg-green-600/30 text-green-300",
    failed: "bg-red-600/30 text-red-300",
  };

  const isProcessing = [
    "pending",
    "generating_script",
    "generating_hook",
    "generating_voice",
    "fetching_media",
    "rendering",
  ].includes(video.status);

  return (
    <div className="card flex items-center gap-4">
      {/* Preview */}
      <div
        className="w-20 h-36 bg-dark-500 rounded-lg flex-shrink-0 flex items-center justify-center cursor-pointer overflow-hidden"
        onClick={onSelect}
      >
        {video.thumbnail_url ? (
          <img src={video.thumbnail_url} alt="" className="w-full h-full object-cover" />
        ) : (
          <FiPlay className="w-6 h-6 text-dark-300" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3
            className="font-semibold text-white truncate cursor-pointer hover:text-brand-400"
            onClick={onSelect}
          >
            {video.title || `Odcinek ${video.episode_number}`}
          </h3>
          <span className={`status-badge ${statusColors[video.status] || ""}`}>
            {video.status.replace(/_/g, " ")}
          </span>
        </div>

        {video.hook_text && (
          <p className="text-sm text-dark-200 truncate mb-1">Hook: {video.hook_text}</p>
        )}

        <div className="flex items-center gap-4 text-xs text-dark-300">
          <span>{new Date(video.created_at).toLocaleDateString("pl-PL")}</span>
          {video.metrics?.views > 0 && <span>{video.metrics.views} wysw.</span>}
          {video.metrics?.likes > 0 && <span>{video.metrics.likes} polub.</span>}
        </div>

        {video.error_message && (
          <p className="text-xs text-red-400 mt-1 truncate">{video.error_message}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 flex-shrink-0">
        {video.status === "ready_for_review" && (
          <button
            onClick={() => onApprove(["youtube", "tiktok"])}
            className="btn-primary text-sm flex items-center gap-1"
          >
            <FiCheck className="w-3 h-3" />
            Zatwierdz
          </button>
        )}
        {video.status === "failed" && (
          <button
            onClick={onRegenerate}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            <FiRefreshCw className="w-3 h-3" />
            Ponow
          </button>
        )}
        {video.video_url && (
          <a
            href={video.video_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-sm px-3"
          >
            <FiExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </div>
  );
}

function VideoDetailModal({ video, onClose }: { video: Video; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-700 rounded-2xl border border-dark-400 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-dark-400">
          <h2 className="text-xl font-bold text-white">{video.title || "Szczegoly wideo"}</h2>
          <button onClick={onClose} className="text-dark-200 hover:text-white text-xl">
            x
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Video Player */}
          {video.video_url && (
            <div className="aspect-[9/16] max-h-[400px] bg-dark-800 rounded-lg overflow-hidden mx-auto w-fit">
              <video
                src={video.video_url}
                controls
                className="h-full"
                poster={video.thumbnail_url || undefined}
              />
            </div>
          )}

          {/* Script */}
          <div>
            <h3 className="font-semibold text-white mb-2">Skrypt</h3>
            <pre className="bg-dark-800 rounded-lg p-4 text-sm text-dark-100 whitespace-pre-wrap max-h-[300px] overflow-y-auto">
              {video.script || "Brak skryptu"}
            </pre>
          </div>

          {/* Metrics */}
          {video.status === "published" && (
            <div>
              <h3 className="font-semibold text-white mb-2">Metryki</h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-dark-800 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-white">{video.metrics?.views || 0}</div>
                  <div className="text-xs text-dark-200">Wyswietlenia</div>
                </div>
                <div className="bg-dark-800 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-white">{video.metrics?.likes || 0}</div>
                  <div className="text-xs text-dark-200">Polubienia</div>
                </div>
                <div className="bg-dark-800 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-white">{video.metrics?.comments || 0}</div>
                  <div className="text-xs text-dark-200">Komentarze</div>
                </div>
              </div>
            </div>
          )}

          {/* Tags */}
          {video.tags?.length > 0 && (
            <div>
              <h3 className="font-semibold text-white mb-2">Tagi</h3>
              <div className="flex flex-wrap gap-2">
                {video.tags.map((tag, i) => (
                  <span key={i} className="bg-dark-500 text-dark-100 px-2 py-1 rounded text-xs">
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
