import { api } from "@/api/client";
import type { Author } from "@/api/social";

export interface StreaksToday {
  day: string;
  gym_checked_in: boolean;
  muscles: string[];
  protein_target_g: number | null;
  protein_logged_g: number;
  protein_met: boolean;
}

/** Muscle groups offered at check-in (must match the backend MUSCLE_GROUPS set). */
export const MUSCLE_GROUPS = [
  "chest", "back", "shoulders", "biceps", "triceps", "forearms",
  "core", "quads", "hamstrings", "glutes", "calves", "cardio",
] as const;

export interface MyStreaks {
  gym_streak: number;
  protein_streak: number;
  today: StreaksToday;
}

export interface CheckinResult {
  gym_checked_in: boolean;
  gym_streak: number;
  muscles: string[];
}

export interface LeaderboardEntry {
  user: Author;
  gym_streak: number;
  protein_streak: number;
  gym_days: number;
  protein_days: number;
  score: number;
  is_me: boolean;
}

export interface Leaderboard {
  window_days: number;
  entries: LeaderboardEntry[];
}

export const getMyStreaks = () => api<MyStreaks>("/streaks/me");

export const gymCheckin = (muscles: string[] = []) =>
  api<CheckinResult>("/streaks/checkin", {
    method: "POST",
    body: JSON.stringify({ muscles }),
  });

export const undoGymCheckin = () => api<CheckinResult>("/streaks/checkin", { method: "DELETE" });

export const getLeaderboard = () => api<Leaderboard>("/streaks/leaderboard");
