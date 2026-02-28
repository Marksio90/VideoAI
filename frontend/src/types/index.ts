// ── Użytkownik ──
export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  max_series: number;
  max_videos_per_month: number;
  videos_generated_this_month: number;
  created_at: string;
}

// ── Auth ──
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Seria ──
export interface ScheduleConfig {
  frequency: string;
  days: string[];
  time_utc: string;
  timezone: string;
}

export interface VisualStyle {
  font: string;
  font_size: number;
  font_color: string;
  subtitle_position: string;
  transition: string;
  background_music: boolean;
  branding_text: string;
}

export interface PublishChannels {
  youtube: boolean;
  tiktok: boolean;
  instagram: boolean;
}

export interface Series {
  id: string;
  user_id: string;
  title: string;
  description: string;
  topic: string;
  prompt_template: string;
  language: string;
  tone: string;
  target_duration_seconds: number;
  schedule_config: ScheduleConfig;
  publish_channels: PublishChannels;
  visual_style: VisualStyle;
  voice_id: string | null;
  tts_provider: string;
  is_active: boolean;
  total_episodes: number;
  created_at: string;
  updated_at: string;
}

export interface SeriesCreateInput {
  title: string;
  description?: string;
  topic: string;
  prompt_template?: string;
  language?: string;
  tone?: string;
  target_duration_seconds?: number;
  schedule_config?: Partial<ScheduleConfig>;
  publish_channels?: Partial<PublishChannels>;
  visual_style?: Partial<VisualStyle>;
  voice_id?: string;
  tts_provider?: string;
}

// ── Wideo ──
export type VideoStatus =
  | "pending"
  | "generating_script"
  | "generating_hook"
  | "generating_voice"
  | "fetching_media"
  | "rendering"
  | "ready_for_review"
  | "approved"
  | "publishing"
  | "published"
  | "failed"
  | "cancelled";

export interface VideoMetrics {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  watch_time_seconds: number;
  avg_view_duration: number;
  retention_rate: number;
}

export interface Video {
  id: string;
  series_id: string;
  episode_number: number;
  title: string;
  hook_text: string;
  script: string;
  description: string;
  tags: string[];
  status: VideoStatus;
  error_message: string | null;
  voice_url: string | null;
  voice_duration_seconds: number | null;
  video_url: string | null;
  thumbnail_url: string | null;
  scenes: Scene[];
  media_assets: { images: string[]; clips: string[]; music_track: string | null };
  scheduled_publish_at: string | null;
  published_at: string | null;
  metrics: VideoMetrics;
  platform_ids: { youtube_id: string | null; tiktok_id: string | null; instagram_id: string | null };
  created_at: string;
  updated_at: string;
}

export interface Scene {
  text: string;
  visual_description?: string;
  media_url?: string;
  start_time?: number;
  end_time?: number;
  duration_hint?: string;
}

// ── Analityka ──
export interface DashboardStats {
  total_series: number;
  total_videos: number;
  published_videos: number;
  total_views: number;
  total_likes: number;
  avg_retention_rate: number;
  videos_this_month: number;
}

// ── Połączenia platform ──
export interface PlatformConnection {
  id: string;
  platform: string;
  platform_username: string | null;
  channel_name: string | null;
  is_active: boolean;
  created_at: string;
}

// ── Paginacja ──
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
