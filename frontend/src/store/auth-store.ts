/**
 * Store autentykacji — Zustand.
 */

import { create } from "zustand";
import type { User } from "@/types";
import { authApi, clearTokens, loadTokens, setTokens, usersApi } from "@/lib/api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email, password) => {
    const { data } = await authApi.login(email, password);
    setTokens(data.access_token, data.refresh_token);
    const { data: user } = await usersApi.getMe();
    set({ user, isAuthenticated: true });
  },

  register: async (email, password, fullName) => {
    const { data } = await authApi.register(email, password, fullName);
    setTokens(data.access_token, data.refresh_token);
    const { data: user } = await usersApi.getMe();
    set({ user, isAuthenticated: true });
  },

  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    try {
      const { data } = await usersApi.getMe();
      set({ user: data, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  initialize: async () => {
    loadTokens();
    try {
      const { data } = await usersApi.getMe();
      set({ user: data, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
