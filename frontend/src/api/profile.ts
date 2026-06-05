import { api, apiUpload } from "@/api/client";

export interface Profile {
  id: string;
  email: string;
  username: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  bio: string | null;
  sex: string | null;
  goals: string[];
  dob: string | null; // YYYY-MM-DD
  age: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  body_fat_pct: number | null;
  activity_level: string | null;
  coach_persona: string | null;
  streaks_public: boolean;
}

export interface Measurement {
  id: string;
  measured_at: string;
  weight_kg: number | null;
  height_cm: number | null;
  body_fat_pct: number | null;
  source: string;
}

export type ProfileUpdate = Partial<{
  first_name: string;
  last_name: string;
  bio: string;
  sex: string;
  goals: string[];
  dob: string;
  height_cm: number;
  weight_kg: number;
  body_fat_pct: number;
  activity_level: string;
  coach_persona: string;
  streaks_public: boolean;
}>;

export const getProfile = () => api<Profile>("/profile/me");

export const updateProfile = (patch: ProfileUpdate) =>
  api<Profile>("/profile/me", { method: "PATCH", body: JSON.stringify(patch) });

export const getMeasurements = () => api<Measurement[]>("/profile/measurements");

export function uploadAvatar(file: File): Promise<Profile> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<Profile>("/profile/avatar", form);
}
