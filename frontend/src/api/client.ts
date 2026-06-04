import { useAuth } from "@/lib/auth";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

// Single in-flight refresh shared across all callers, so a burst of 401s triggers
// exactly one /auth/refresh round-trip (docs/11 §1).
let refreshInFlight: Promise<string | null> | null = null;

/**
 * Exchange the stored refresh token for a fresh access token. Returns the new access
 * token, or null (and logs out) if there's no refresh token or the refresh is rejected.
 * Uses raw fetch — never `api()` — to avoid recursing through the 401 handler.
 */
export function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setSession, logout } = useAuth.getState();
  if (!refreshToken) {
    logout();
    return Promise.resolve(null);
  }
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          logout();
          return null;
        }
        const data = await res.json();
        setSession({ accessToken: data.access_token, refreshToken: data.refresh_token });
        return data.access_token as string;
      } catch {
        logout();
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const token = useAuth.getState().accessToken;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  // Access token expired → refresh once and replay the request. Skip for /auth/* so a
  // bad login/refresh doesn't loop.
  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    const newToken = await refreshAccessToken();
    if (newToken) return api<T>(path, init, false);
  }

  if (!res.ok) {
    const problem = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, problem.detail ?? "request failed");
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

/** Multipart POST (file upload). No Content-Type header so the browser sets the boundary. */
export async function apiUpload<T>(path: string, form: FormData, retry = true): Promise<T> {
  const token = useAuth.getState().accessToken;
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: form,
  });
  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) return apiUpload<T>(path, form, false);
  }
  if (!res.ok) {
    const problem = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, problem.detail ?? "upload failed");
  }
  return (await res.json()) as T;
}
