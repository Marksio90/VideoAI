"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { seriesApi, videosApi } from "@/lib/api";
import type { Series, SeriesCreateInput } from "@/types";
import toast from "react-hot-toast";
import { FiPlus, FiPlay, FiEdit, FiTrash2, FiCalendar } from "react-icons/fi";

export default function SeriesPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list().then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => seriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["series"] });
      toast.success("Seria usunięta");
    },
  });

  const generateMutation = useMutation({
    mutationFn: (seriesId: string) => videosApi.generate(seriesId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recent-videos"] });
      toast.success("Generowanie wideo uruchomione!");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Blad generowania");
    },
  });

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Serie wideo</h1>
          <p className="text-dark-200 mt-1">Zarzadzaj swoimi seriami</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <FiPlus className="w-4 h-4" />
          Nowa seria
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && <CreateSeriesModal onClose={() => setShowCreate(false)} />}

      {/* Series List */}
      {isLoading ? (
        <div className="text-center py-12 text-dark-200">Ladowanie...</div>
      ) : data?.items?.length ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((series) => (
            <SeriesCard
              key={series.id}
              series={series}
              onGenerate={() => generateMutation.mutate(series.id)}
              onDelete={() => {
                if (confirm("Czy na pewno chcesz usunac ta serie?")) {
                  deleteMutation.mutate(series.id);
                }
              }}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-16">
          <FiFilm className="w-12 h-12 text-dark-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Brak serii</h3>
          <p className="text-dark-200 mb-6">Utwórz pierwsza serie, aby zaczac generowac wideo</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            Utwórz serie
          </button>
        </div>
      )}
    </DashboardLayout>
  );
}

function SeriesCard({
  series,
  onGenerate,
  onDelete,
}: {
  series: Series;
  onGenerate: () => void;
  onDelete: () => void;
}) {
  const schedule = series.schedule_config;
  const channels = series.publish_channels;

  return (
    <div className="card group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white truncate">{series.title}</h3>
          <p className="text-sm text-dark-200 mt-1 line-clamp-2">{series.topic}</p>
        </div>
        <span
          className={`status-badge ${
            series.is_active ? "bg-green-600/30 text-green-300" : "bg-dark-400/30 text-dark-200"
          }`}
        >
          {series.is_active ? "Aktywna" : "Wstrzymana"}
        </span>
      </div>

      <div className="text-xs text-dark-200 space-y-1 mb-4">
        <div className="flex items-center gap-2">
          <FiCalendar className="w-3 h-3" />
          {schedule?.days?.length || 0}x / tydzien o {schedule?.time_utc || "14:00"}
        </div>
        <div>
          Jezyk: {series.language} | Ton: {series.tone} | {series.target_duration_seconds}s
        </div>
        <div>
          Odcinki: {series.total_episodes} |
          {channels?.youtube ? " YT" : ""}
          {channels?.tiktok ? " TikTok" : ""}
          {channels?.instagram ? " IG" : ""}
          {!channels?.youtube && !channels?.tiktok && !channels?.instagram ? " Brak kanalow" : ""}
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={onGenerate} className="btn-primary flex-1 text-sm flex items-center justify-center gap-1">
          <FiPlay className="w-3 h-3" />
          Generuj
        </button>
        <button className="btn-secondary text-sm px-3">
          <FiEdit className="w-3 h-3" />
        </button>
        <button onClick={onDelete} className="btn-secondary text-sm px-3 hover:border-red-500 hover:text-red-400">
          <FiTrash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ── Modal tworzenia serii ──

import { FiFilm, FiX } from "react-icons/fi";

function CreateSeriesModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<SeriesCreateInput>({
    title: "",
    topic: "",
    description: "",
    language: "pl",
    tone: "edukacyjny",
    target_duration_seconds: 60,
    tts_provider: "elevenlabs",
  });

  const createMutation = useMutation({
    mutationFn: (data: SeriesCreateInput) => seriesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["series"] });
      toast.success("Seria utworzona!");
      onClose();
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Blad tworzenia serii");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-700 rounded-2xl border border-dark-400 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-dark-400">
          <h2 className="text-xl font-bold text-white">Nowa seria</h2>
          <button onClick={onClose} className="text-dark-200 hover:text-white">
            <FiX className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="label">Tytul serii *</label>
            <input
              className="input-field"
              placeholder="np. Finanse osobiste"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="label">Temat/Opis tematyki *</label>
            <textarea
              className="input-field min-h-[80px]"
              placeholder="np. Praktyczne porady dotyczace oszczedzania, inwestowania i zarzadzania budztem"
              value={formData.topic}
              onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="label">Opis serii</label>
            <textarea
              className="input-field"
              placeholder="Opcjonalny opis..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Jezyk</label>
              <select
                className="input-field"
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              >
                <option value="pl">Polski</option>
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="es">Espanol</option>
              </select>
            </div>

            <div>
              <label className="label">Ton narracji</label>
              <select
                className="input-field"
                value={formData.tone}
                onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
              >
                <option value="edukacyjny">Edukacyjny</option>
                <option value="rozrywkowy">Rozrywkowy</option>
                <option value="motywacyjny">Motywacyjny</option>
                <option value="informacyjny">Informacyjny</option>
                <option value="humorystyczny">Humorystyczny</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label">Dlugosc wideo (sekundy)</label>
            <input
              type="number"
              className="input-field"
              min={15}
              max={180}
              value={formData.target_duration_seconds}
              onChange={(e) =>
                setFormData({ ...formData, target_duration_seconds: parseInt(e.target.value) || 60 })
              }
            />
          </div>

          <div>
            <label className="label">Provider TTS</label>
            <select
              className="input-field"
              value={formData.tts_provider}
              onChange={(e) => setFormData({ ...formData, tts_provider: e.target.value })}
            >
              <option value="elevenlabs">ElevenLabs (najlepsza jakosc)</option>
              <option value="google">Google TTS</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Anuluj
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "Tworzenie..." : "Utwórz serie"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
