// Typed client for the PropWise backend. Every page goes through this file.

import type {
  AdminStats,
  ChatResponse,
  ChatTurn,
  DocumentDeclaration,
  ListingInput,
  Locality,
  Meta,
  CompareResponse,
  ModelInfo,
  Preferences,
  RecommendationConfig,
  RecommendationResponse,
  SimilarResponse,
  PriceEstimate,
  PriceEstimateInput,
  PropertyDetail,
  PropertyList,
  PropertySummary,
  TokenResponse,
  User,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "propwise.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: { field: string | null; issue: string }[] = [],
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: session lasts for this page only */
  }
}

export function mediaUrl(path: string | null): string | null {
  return path ? `${API_BASE}${path}` : null;
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>;

export function toQueryString(q: Query): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.filter(Boolean).forEach((x) => sp.append(k, x));
    else sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function request<T>(path: string, init: RequestInit & { query?: Query } = {}): Promise<T> {
  const { query, headers, ...rest } = init;
  const token = getToken();
  const h = new Headers(headers);
  if (token) h.set("Authorization", `Bearer ${token}`);
  if (rest.body && !(rest.body instanceof FormData)) h.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1${path}${query ? toQueryString(query) : ""}`, { ...rest, headers: h });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the PropWise server. Is the backend running?");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const e = body?.error;
    if (res.status === 401 && token) setToken(null);
    throw new ApiError(res.status, e?.code ?? "http_error", e?.message ?? `Request failed (${res.status})`, e?.details);
  }
  return body as T;
}

const json = (data: unknown) => JSON.stringify(data);

export const api = {
  health: () => request<{ status: string; database: boolean }>("/health"),
  meta: () => request<Meta>("/meta/enums"),
  localities: (city?: string) => request<Locality[]>("/localities", { query: { city } }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: json({ email, password }) }),
  register: (name: string, email: string, password: string, role: "buyer" | "seller") =>
    request<TokenResponse>("/auth/register", { method: "POST", body: json({ name, email, password, role }) }),
  me: () => request<User>("/users/me"),

  searchProperties: (q: Query) => request<PropertyList>("/properties", { query: q }),
  getProperty: (id: string) => request<PropertyDetail>(`/properties/${id}`),
  createProperty: (data: ListingInput) =>
    request<PropertyDetail>("/properties", { method: "POST", body: json(data) }),
  updateProperty: (id: string, data: Partial<ListingInput>) =>
    request<PropertyDetail>(`/properties/${id}`, { method: "PATCH", body: json(data) }),
  archiveProperty: (id: string) => request<void>(`/properties/${id}`, { method: "DELETE" }),
  setDocuments: (id: string, documents: DocumentDeclaration[]) =>
    request<PropertyDetail>(`/properties/${id}/documents`, { method: "PUT", body: json({ documents }) }),
  uploadImage: (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ id: number; url: string }>(`/properties/${id}/images`, { method: "POST", body: fd });
  },
  deleteImage: (id: string, imageId: number) =>
    request<void>(`/properties/${id}/images/${imageId}`, { method: "DELETE" }),

  favorites: () => request<PropertySummary[]>("/users/me/favorites"),
  addFavorite: (id: string) => request<void>(`/users/me/favorites/${id}`, { method: "PUT" }),
  removeFavorite: (id: string) => request<void>(`/users/me/favorites/${id}`, { method: "DELETE" }),

  adminQueue: (status: string, page = 1) =>
    request<PropertyList>("/admin/properties", { query: { status, page, page_size: 20 } }),
  adminReview: (id: string, action: "approve" | "reject" | "flag", reason?: string) =>
    request<PropertyDetail>(`/admin/properties/${id}/${action}`, { method: "POST", body: json({ reason }) }),
  adminStats: () => request<AdminStats>("/admin/stats"),

  estimatePrice: (input: PriceEstimateInput) =>
    request<PriceEstimate>("/predictions/price", { method: "POST", body: json(input) }),
  modelInfo: () => request<ModelInfo>("/model-info"),

  recommend: (prefs: Preferences, limit = 10) =>
    request<RecommendationResponse>("/recommendations", { method: "POST", body: json({ ...prefs, limit }) }),
  recommendationConfig: () => request<RecommendationConfig>("/recommendations/config"),
  compare: (ids: string[], preferences?: Preferences | null) =>
    request<CompareResponse>("/properties/compare", { method: "POST", body: json({ property_ids: ids, preferences: preferences ?? null }) }),
  chat: (message: string, history: ChatTurn[], preferences?: Preferences | null) =>
    request<ChatResponse>("/ai/chat", { method: "POST", body: json({ message, history, preferences: preferences ?? null }) }),
  similar: (id: string) => request<SimilarResponse>(`/properties/${id}/similar`),
  getPreferences: () => request<{ other: { advisor?: Preferences } | null } | null>("/users/me/preferences"),
  savePreferences: (prefs: Preferences) =>
    request<unknown>("/users/me/preferences", {
      method: "PUT",
      body: json({
        minimum_budget: prefs.min_budget || null,
        maximum_budget: prefs.max_budget || null,
        preferred_locality_ids: prefs.locality_ids,
        preferred_cities: prefs.cities,
        preferred_property_types: prefs.property_types,
        objective: prefs.objective ?? null,
        other: { advisor: prefs },
      }),
    }),
};
