import { create } from "zustand";
import Cookies from "js-cookie";
import { authApi } from "./api";

export interface User {
  id: string;
  email: string;
  name?: string;
  role: "superadmin" | "admin" | "editor" | "viewer";
  is_active: boolean;
  client_ids: string[];
  has_client_access: boolean;
  job_title?: string;
  company?: string;
  phone?: string;
  timezone?: string;
  created_at?: string;
  last_login?: string;
  auth_method?: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  loginWithTokens: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  setUser: (user: User | null) => void;
}

// Cookie options - secure flag set dynamically at runtime
const getCookieOptions = () => ({
  secure: typeof window !== "undefined" && window.location.protocol === "https:",
  sameSite: "lax" as const,
});

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    const tokens = await authApi.login(email, password);

    const opts = getCookieOptions();
    Cookies.set("access_token", tokens.access_token, { ...opts, expires: 1 });
    Cookies.set("refresh_token", tokens.refresh_token, { ...opts, expires: 7 });

    await get().fetchUser();
  },

  loginWithTokens: async (accessToken: string, refreshToken: string) => {
    const opts = getCookieOptions();
    Cookies.set("access_token", accessToken, { ...opts, expires: 1 });
    Cookies.set("refresh_token", refreshToken, { ...opts, expires: 7 });
    await get().fetchUser();
  },

  logout: () => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    set({ user: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    set({ isLoading: true });

    const token = Cookies.get("access_token");
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      const user = await authApi.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      Cookies.remove("access_token");
      Cookies.remove("refresh_token");
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  setUser: (user: User | null) => {
    set({ user, isAuthenticated: !!user });
  },
}));
