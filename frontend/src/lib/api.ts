/**
 * Klient API — centralne zarządzanie zapytaniami HTTP.
 * Ulepszenie: automatyczny refresh tokena + interceptory + error handling.
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type {
  DashboardStats,
  PaginatedResponse,
  PlatformConnection,
  Series,
  SeriesCreateInput,
  TokenResponse,
  User,
  Video,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// ── Token management ──

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  }
}

export function loadTokens() {
  if (typeof window !== "undefined") {
    accessToken = localStorage.getItem("access_token");
    refreshToken = localStorage.getItem("refresh_token");
  }
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
}

// ── Interceptors ──

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
      originalRequest._retry = true;
      try {
        const { data } = await axios.post<TokenResponse>(`${API_BASE}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        setTokens(data.access_token, data.refresh_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch {
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/auth";
        }
      }
    }

    return Promise.reject(error);
  }
);

// ── Auth ──

export const authApi = {
  register: (email: string, password: string, fullName: string) =>
    api.post<TokenResponse>("/auth/register", { email, password, full_name: fullName }),

  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),

  refresh: (token: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token: token }),
};

// ── Users ──

export const usersApi = {
  getMe: () => api.get<User>("/users/me"),
  updateMe: (data: Partial<User>) => api.patch<User>("/users/me", data),
  deleteMe: () => api.delete("/users/me"),
};

// ── Series ──

export const seriesApi = {
  list: (page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<Series>>("/series", { params: { page, page_size: pageSize } }),

  get: (id: string) => api.get<Series>(`/series/${id}`),

  create: (data: SeriesCreateInput) => api.post<Series>("/series", data),

  update: (id: string, data: Partial<SeriesCreateInput>) =>
    api.patch<Series>(`/series/${id}`, data),

  delete: (id: string) => api.delete(`/series/${id}`),
};

// ── Videos ──

export const videosApi = {
  list: (params?: { series_id?: string; status_filter?: string; page?: number }) =>
    api.get<PaginatedResponse<Video>>("/videos", { params }),

  get: (id: string) => api.get<Video>(`/videos/${id}`),

  generate: (seriesId: string, customTopic?: string) =>
    api.post<Video>("/videos/generate", {
      series_id: seriesId,
      custom_topic: customTopic,
    }),

  update: (id: string, data: Partial<Video>) => api.patch<Video>(`/videos/${id}`, data),

  approve: (id: string, channels: string[], scheduledAt?: string) =>
    api.post<Video>(`/videos/${id}/approve`, {
      publish_channels: channels,
      scheduled_publish_at: scheduledAt,
    }),

  regenerate: (id: string) => api.post<Video>(`/videos/${id}/regenerate`),
};

// ── Analytics ──

export const analyticsApi = {
  dashboard: () => api.get<DashboardStats>("/analytics/dashboard"),
  seriesStats: () => api.get("/analytics/series"),
};

// ── Publishing ──

export const publishingApi = {
  listConnections: () => api.get<PlatformConnection[]>("/publishing/connections"),

  connect: (platform: string, authCode: string, redirectUri: string) =>
    api.post<PlatformConnection>("/publishing/connections", {
      platform,
      auth_code: authCode,
      redirect_uri: redirectUri,
    }),

  disconnect: (connectionId: string) =>
    api.delete(`/publishing/connections/${connectionId}`),

  listJobs: (videoId?: string) =>
    api.get("/publishing/jobs", { params: { video_id: videoId } }),
};

export default api;
