import { create } from "zustand";

// Web auth (docs/11 §1): the ideal is access token in memory + refresh via an
// httpOnly cookie. The backend doesn't expose the cookie/refresh flow yet, so for
// now we persist both tokens to localStorage so a reload keeps you signed in.
// Swap to the cookie flow once /auth/refresh + /auth/logout land.
const STORAGE_KEY = "forge.auth";

export interface Session {
  accessToken: string;
  refreshToken: string | null;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  /** Role decoded from the access-token JWT (`user`/`coach`/`admin`/…), or null. */
  role: string | null;
  setSession: (s: Session) => void;
  logout: () => void;
}

/** Decode the `role` claim from a JWT without verifying it (display-only; the API still enforces). */
function roleFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.role === "string" ? payload.role : null;
  } catch {
    return null;
  }
}

function load(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

const initial = load();

export const useAuth = create<AuthState>((set) => ({
  accessToken: initial?.accessToken ?? null,
  refreshToken: initial?.refreshToken ?? null,
  role: roleFromToken(initial?.accessToken ?? null),
  setSession: ({ accessToken, refreshToken }) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ accessToken, refreshToken }));
    set({ accessToken, refreshToken, role: roleFromToken(accessToken) });
  },
  logout: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ accessToken: null, refreshToken: null, role: null });
  },
}));
