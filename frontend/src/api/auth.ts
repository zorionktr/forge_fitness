import { api } from "@/api/client";

// Mirrors backend app/schemas/auth.py (docs/10 §2).
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UsernameAvailability {
  username: string;
  available: boolean;
  reason: string | null;
}

/** Live availability check for the sign-up form (underscores allowed). */
export function checkUsername(username: string): Promise<UsernameAvailability> {
  return api<UsernameAvailability>(`/auth/username-available?username=${encodeURIComponent(username)}`);
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(
  email: string,
  username: string,
  password: string,
  firstName: string,
  lastName: string,
): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      username,
      password,
      first_name: firstName,
      last_name: lastName || null,
    }),
  });
}
