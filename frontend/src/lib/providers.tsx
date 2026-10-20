"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api";
import type { Meta, User } from "./types";

// ---------------------------------------------------------------- auth

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string, role: "buyer" | "seller") => Promise<User>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const v = useContext(AuthCtx);
  if (!v) throw new Error("useAuth outside provider");
  return v;
}

// ---------------------------------------------------------------- compare tray

const COMPARE_KEY = "propwise.compare";
export const COMPARE_MAX = 3;

interface CompareState {
  ids: string[];
  toggle: (id: string) => void;
  has: (id: string) => boolean;
  clear: () => void;
}

const CompareCtx = createContext<CompareState | null>(null);

export function useCompare(): CompareState {
  const v = useContext(CompareCtx);
  if (!v) throw new Error("useCompare outside provider");
  return v;
}

// ---------------------------------------------------------------- reference data

const MetaCtx = createContext<Meta | null>(null);

export function useMeta(): Meta | null {
  return useContext(MetaCtx);
}

/** Label lookup, e.g. label(meta, "PropertyType", "residential_plot") -> "Residential plot". */
export function label(meta: Meta | null, group: string, code: string | null | undefined): string {
  if (!code) return "—";
  const v = meta?.enums[group]?.[code];
  if (v) return v;
  const s = code.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function Providers({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [ids, setIds] = useState<string[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    if (getToken()) {
      api.me().then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
    } else {
      setReady(true);
    }
    try {
      const saved = JSON.parse(window.localStorage.getItem(COMPARE_KEY) || "[]");
      if (Array.isArray(saved)) setIds(saved.slice(0, COMPARE_MAX));
    } catch {
      /* ignore */
    }
    api.meta().then(setMeta).catch(() => setMeta(null));
  }, []);

  const persist = (next: string[]) => {
    setIds(next);
    try {
      window.localStorage.setItem(COMPARE_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  const login = useCallback(async (email: string, password: string) => {
    const t = await api.login(email, password);
    setToken(t.access_token);
    setUser(t.user);
    return t.user;
  }, []);

  const register = useCallback(async (name: string, email: string, password: string, role: "buyer" | "seller") => {
    const t = await api.register(name, email, password, role);
    setToken(t.access_token);
    setUser(t.user);
    return t.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const auth = useMemo(() => ({ user, ready, login, register, logout }), [user, ready, login, register, logout]);
  const compare = useMemo<CompareState>(
    () => ({
      ids,
      has: (id) => ids.includes(id),
      toggle: (id) =>
        persist(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id].slice(-COMPARE_MAX)),
      clear: () => persist([]),
    }),
    [ids],
  );

  return (
    <AuthCtx.Provider value={auth}>
      <MetaCtx.Provider value={meta}>
        <CompareCtx.Provider value={compare}>{children}</CompareCtx.Provider>
      </MetaCtx.Provider>
    </AuthCtx.Provider>
  );
}
