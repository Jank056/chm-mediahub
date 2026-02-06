import axios from "axios";
import Cookies from "js-cookie";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = Cookies.get("refresh_token");
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh`, null, {
            params: { refresh_token: refreshToken },
          });

          const { access_token, refresh_token } = response.data;
          Cookies.set("access_token", access_token);
          Cookies.set("refresh_token", refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch {
          // Refresh failed, clear tokens
          Cookies.remove("access_token");
          Cookies.remove("refresh_token");
          window.location.href = "/login";
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await api.post("/auth/login", { email, password });
    return response.data;
  },

  me: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  invite: async (email: string, role: string) => {
    const response = await api.post("/auth/invite", { email, role });
    return response.data;
  },

  acceptInvite: async (token: string, password: string) => {
    const response = await api.post("/auth/accept-invite", { token, password });
    return response.data;
  },

  listInvitations: async () => {
    const response = await api.get("/auth/invitations");
    return response.data;
  },

  revokeInvitation: async (id: string) => {
    const response = await api.delete(`/auth/invitations/${id}`);
    return response.data;
  },

  validateInvite: async (token: string) => {
    const response = await api.get("/auth/validate-invite", {
      params: { token },
    });
    return response.data as { valid: boolean; email: string | null };
  },

  acceptInviteGoogle: async (state: string, gotrueAccessToken: string) => {
    const response = await api.post("/auth/accept-invite/google", {
      state,
      gotrue_access_token: gotrueAccessToken,
    });
    return response.data;
  },

  loginGoogle: async (gotrueAccessToken: string) => {
    const response = await api.post("/auth/login/google", {
      gotrue_access_token: gotrueAccessToken,
    });
    return response.data;
  },
};

// Users API
export const usersApi = {
  list: async () => {
    const response = await api.get("/users");
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },

  update: async (id: string, data: { role?: string; is_active?: boolean }) => {
    const response = await api.patch(`/users/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    const response = await api.delete(`/users/${id}`);
    return response.data;
  },
};

// Analytics Types
export interface MediaItem {
  type?: string;
  url?: string;
  width?: number;
  height?: number;
  duration_ms?: number;
}

export interface PostMetrics {
  id: string;
  clip_id: string | null;
  shoot_id: string | null;
  platform: string;
  provider_post_id: string | null;
  title: string | null;
  posted_at: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  share_count: number;
  impression_count: number;
  stats_synced_at: string | null;
  // Rich metadata
  thumbnail_url: string | null;
  content_url: string | null;
  content_type: string | null;
  duration_seconds: number | null;
  is_short: boolean | null;
  language: string | null;
  hashtags: string[] | null;
  mentions: string[] | null;
  media_urls: MediaItem[] | null;
  platform_metadata: Record<string, unknown> | null;
}

export interface ShootMetrics {
  id: string;
  name: string;
  doctors: string[];
  shoot_date: string | null;
  post_count: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
}

export interface PlatformStats {
  platform: string;
  post_count: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
}

export interface TimelineEntry {
  date: string;
  post_count: number;
  views: number;
  likes: number;
}

export interface AnalyticsSummary {
  total_clips: number;
  total_posts: number;
  total_shoots: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  clips_by_platform: Record<string, number>;
  clips_by_status: Record<string, number>;
  posts_by_platform: Record<string, number>;
  last_updated: string | null;
}

export interface DoctorStats {
  doctor: string;
  shoot_count: number;
  post_count: number;
  total_views: number;
  total_likes: number;
}

export interface ClipWithPosts {
  id: string;
  title: string | null;
  platform: string | null;
  description: string | null;
  tags: string[];
  is_short: boolean | null;
  publish_at: string | null;
  published_at: string | null;
  video_preview_url: string | null;
  status: string;
  synced_at: string;
  earliest_posted_at: string | null;  // When first posted to any platform
  post_count: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  posts: PostMetrics[];
}

// Trend entry for growth charts
export interface TrendEntry {
  date: string;
  value: number;
}

// Analytics API
export const analyticsApi = {
  getSummary: async (params?: {
    source?: "official" | "branded";
  }): Promise<AnalyticsSummary> => {
    const response = await api.get("/analytics/summary", { params });
    return response.data;
  },

  getClips: async () => {
    const response = await api.get("/analytics/clips");
    return response.data;
  },

  getPosts: async (params?: {
    platform?: string;
    shoot_id?: string;
    source?: "official" | "branded";
    sort_by?: "views" | "likes" | "posted_at";
    limit?: number;
    offset?: number;
  }): Promise<PostMetrics[]> => {
    const response = await api.get("/analytics/posts", { params });
    return response.data;
  },

  getTopPosts: async (params?: {
    platform?: string;
    source?: "official" | "branded";
    limit?: number;
  }): Promise<PostMetrics[]> => {
    const response = await api.get("/analytics/posts/top", { params });
    return response.data;
  },

  getShoots: async (params?: {
    sort_by?: "views" | "posts" | "name";
  }): Promise<ShootMetrics[]> => {
    const response = await api.get("/analytics/shoots", { params });
    return response.data;
  },

  getShoot: async (shootId: string): Promise<ShootMetrics> => {
    const response = await api.get(`/analytics/shoots/${shootId}`);
    return response.data;
  },

  getPlatforms: async (params?: {
    source?: "official" | "branded";
  }): Promise<PlatformStats[]> => {
    const response = await api.get("/analytics/platforms", { params });
    return response.data;
  },

  getTimeline: async (params?: {
    days?: number;
    platform?: string;
    source?: "official" | "branded";
  }): Promise<TimelineEntry[]> => {
    const response = await api.get("/analytics/timeline", { params });
    return response.data;
  },

  getTrends: async (params: {
    platform: string;
    metric_name: string;
    days?: number;
  }): Promise<TrendEntry[]> => {
    const response = await api.get("/analytics/trends", { params });
    return response.data;
  },

  getDoctors: async (): Promise<DoctorStats[]> => {
    const response = await api.get("/analytics/doctors");
    return response.data;
  },

  searchClips: async (params?: {
    q?: string;
    platform?: string;
    status?: string;
    sort_by?: "views" | "likes" | "recent" | "title" | "posted";
    limit?: number;
    offset?: number;
  }): Promise<ClipWithPosts[]> => {
    const response = await api.get("/analytics/clips/search", { params });
    return response.data;
  },

  getShootTranscript: async (shootId: string): Promise<{
    shoot_id: string;
    name: string;
    doctors: string[];
    transcript: string;
    length: number;
  }> => {
    const response = await api.get(`/analytics/shoots/${shootId}/transcript`);
    return response.data;
  },

  getShootTranscriptDownloadUrl: (shootId: string): string => {
    return `${API_URL}/analytics/shoots/${shootId}/transcript/download`;
  },
};

// Facebook API
export const facebookApi = {
  getStats: async () => {
    const response = await api.get("/api/facebook/stats");
    return response.data;
  },

  syncStats: async () => {
    const response = await api.post("/api/facebook/stats/sync");
    return response.data;
  },

  syncPosts: async () => {
    const response = await api.post("/api/facebook/posts/sync");
    return response.data;
  },

  getPosts: async (params?: { limit?: number; offset?: number }) => {
    const response = await api.get("/api/facebook/posts", { params });
    return response.data;
  },
};

// Instagram API
export const instagramApi = {
  getStats: async () => {
    const response = await api.get("/api/instagram/stats");
    return response.data;
  },

  syncStats: async () => {
    const response = await api.post("/api/instagram/stats/sync");
    return response.data;
  },

  syncPosts: async () => {
    const response = await api.post("/api/instagram/posts/sync");
    return response.data;
  },

  getPosts: async (params?: { limit?: number; offset?: number }) => {
    const response = await api.get("/api/instagram/posts", { params });
    return response.data;
  },
};

// Reports API
export const reportsApi = {
  uploadFile: async (file: File, fileType: "transcript" | "survey") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType);
    const response = await api.post("/reports/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  listUploads: async () => {
    const response = await api.get("/reports/uploads");
    return response.data;
  },

  generateReport: async (data: {
    event_name: string;
    event_date: string;
    transcript_file_id: string;
    survey_file_id: string;
  }) => {
    const response = await api.post("/reports/generate", data);
    return response.data;
  },

  listJobs: async () => {
    const response = await api.get("/reports/jobs");
    return response.data;
  },

  getJob: async (jobId: string) => {
    const response = await api.get(`/reports/jobs/${jobId}`);
    return response.data;
  },

  downloadReport: async (jobId: string) => {
    const response = await api.get(`/reports/jobs/${jobId}/download`, {
      responseType: "blob",
    });
    return response.data;
  },
};

// Chat API Types
export interface ChunkMetadata {
  source_type: string;
  title?: string;
  doctors?: string;
  date?: string;
  url?: string;
  youtube_url?: string;
  thumbnail_url?: string;
  start_time?: number;
  end_time?: number;
  summary?: string;
}

export interface ChunkResult {
  id: string;
  text: string;
  distance: number;
  metadata: ChunkMetadata;
}

export interface ChunkSearchResponse {
  chunks: ChunkResult[];
  total_indexed: number;
  query_time_ms: number;
}

// Source types for Content Library
export interface SourceInfo {
  id: string;
  source_type: string;
  title: string;
  doctors?: string;
  youtube_url?: string;
  thumbnail_url?: string;
  url?: string;
  chunk_count: number;
  date?: string;
}

export interface SourcesResponse {
  sources: SourceInfo[];
  totals: Record<string, number>;
}

export interface SourceChunk {
  id: string;
  text: string;
  start_time?: number;
  end_time?: number;
  page_num?: number;
}

export interface SourceChunksResponse {
  source_id: string;
  chunks: SourceChunk[];
  count: number;
}

export interface ChunkPosition {
  id: string;
  start_char: number;
  end_char: number;
  start_time?: number;
  end_time?: number;
  page_num?: number;
}

export interface SourceFullTextResponse {
  source_id: string;
  full_text: string;
  chunk_positions: ChunkPosition[];
  chunk_count: number;
  source_type?: string;
  title?: string;
  doctors?: string;
  youtube_url?: string;
}

// Client/Multi-tenant Types (match backend schemas)
export interface ClientSummary {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  is_active: boolean;
  project_count: number;
  total_clips: number;
  total_views: number;
}

export interface ProjectSummary {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_active: boolean;
  kol_group_count: number;
  clip_count: number;
  total_views: number;
}

export interface KOLSummary {
  id: string;
  name: string;
  title: string | null;
  specialty: string | null;
  institution: string | null;
  photo_url: string | null;
}

export interface KOLGroupSummary {
  id: string;
  name: string;
  video_count: number | null;
  publish_day: string | null;
  kol_count: number;
  clip_count: number;
  total_views: number;
}

export interface ClipSummary {
  id: string;
  title: string | null;
  description: string | null;
  platform: string | null;
  status: string;
  is_short: boolean | null;
  aspect: string | null;
  video_preview_url: string | null;
  earliest_posted_at: string | null;
  post_count: number;
  total_views: number;
  total_likes: number;
}

export interface ShootSummary {
  id: string;
  name: string;
  doctors: string[];
  shoot_date: string | null;
  clip_count: number;
  total_views: number;
  clips: ClipSummary[];
}

export interface KOLGroupDetail extends KOLGroupSummary {
  kols: KOLSummary[];
  shoots: ShootSummary[];
  project_code: string;
  project_name: string;
  client_slug: string;
}

export interface ClientDetail extends ClientSummary {
  primary_contact_name: string | null;
  primary_contact_email: string | null;
  projects: ProjectSummary[];
}

export interface ProjectDetail extends ProjectSummary {
  kol_groups: KOLGroupSummary[];
  client_name: string;
  client_slug: string;
}

export interface ClientAnalytics {
  total_clips: number;
  total_posts: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_impressions: number;
  kol_count: number;
  kol_group_count: number;
}

// Clients API - matches backend /api/clients routes
export const clientsApi = {
  // List all clients
  list: async (): Promise<ClientSummary[]> => {
    const response = await api.get("/api/clients");
    return response.data;
  },

  // Get a single client with projects
  get: async (slug: string): Promise<ClientDetail> => {
    const response = await api.get(`/api/clients/${slug}`);
    return response.data;
  },

  // Get analytics summary for a client
  getAnalytics: async (slug: string): Promise<ClientAnalytics> => {
    const response = await api.get(`/api/clients/${slug}/analytics/summary`);
    return response.data;
  },

  // List projects for a client
  getProjects: async (slug: string): Promise<ProjectSummary[]> => {
    const response = await api.get(`/api/clients/${slug}/projects`);
    return response.data;
  },

  // Get a single project with KOL groups
  getProject: async (slug: string, projectCode: string): Promise<ProjectDetail> => {
    const response = await api.get(`/api/clients/${slug}/projects/${projectCode}`);
    return response.data;
  },

  // List KOL groups for a project
  getKOLGroups: async (slug: string, projectCode: string): Promise<KOLGroupSummary[]> => {
    const response = await api.get(`/api/clients/${slug}/projects/${projectCode}/kol-groups`);
    return response.data;
  },

  // Get a single KOL group with members
  getKOLGroup: async (slug: string, projectCode: string, groupId: string): Promise<KOLGroupDetail> => {
    const response = await api.get(`/api/clients/${slug}/projects/${projectCode}/kol-groups/${groupId}`);
    return response.data;
  },

  // List all KOLs
  listKOLs: async (): Promise<KOLSummary[]> => {
    const response = await api.get("/api/clients/kols");
    return response.data;
  },
};

// Chat API
export const chatApi = {
  query: async (query: string, topK: number = 5) => {
    const response = await api.post("/chat/query", { query, top_k: topK });
    return response.data;
  },

  health: async () => {
    const response = await api.get("/chat/health");
    return response.data;
  },

  listPdfs: async () => {
    const response = await api.get("/chat/pdfs");
    return response.data;
  },

  searchChunks: async (
    query: string,
    topK: number = 10,
    sourceTypeFilter?: string
  ): Promise<ChunkSearchResponse> => {
    const payload: { query: string; top_k: number; source_type_filter?: string } = {
      query,
      top_k: topK,
    };
    if (sourceTypeFilter) {
      payload.source_type_filter = sourceTypeFilter;
    }
    const response = await api.post("/chat/search/chunks", payload);
    return response.data;
  },

  listSources: async (): Promise<SourcesResponse> => {
    const response = await api.get("/chat/sources");
    return response.data;
  },

  getSourceChunks: async (sourceId: string): Promise<SourceChunksResponse> => {
    const response = await api.get(`/chat/sources/${encodeURIComponent(sourceId)}/chunks`);
    return response.data;
  },

  getSourceFullText: async (sourceId: string): Promise<SourceFullTextResponse> => {
    const response = await api.get(`/chat/sources/${encodeURIComponent(sourceId)}/full`);
    return response.data;
  },
};
