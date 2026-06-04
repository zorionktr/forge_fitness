import { api, apiUpload } from "@/api/client";

export interface FoodFields {
  brand?: string | null;
  serving_size?: string | null;
  calories?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
  sugar_g?: number | null;
  sodium_mg?: number | null;
  ingredients?: string | null;
}

export interface FoodDraft extends FoodFields {
  name: string | null;
  image_url: string | null;
  raw: Record<string, unknown>;
}

export interface Food extends FoodFields {
  id: string;
  name: string;
  image_url: string | null;
  created_at: string;
}

export interface MealEntry {
  id: string;
  food_id: string;
  food_name: string;
  meal_type: string;
  servings: number;
  calories: number | null;
  protein_g: number | null;
  logged_at: string;
}

export interface DayNutrition {
  day: string;
  totals: { calories: number; protein_g: number; carbs_g: number; fat_g: number };
  entries: MealEntry[];
}

export function analyzeLabel(file: File): Promise<FoodDraft> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<FoodDraft>("/nutrition/analyze", form);
}

export const createFood = (payload: FoodFields & { name: string; image_url?: string | null; raw?: unknown }) =>
  api<Food>("/nutrition/foods", { method: "POST", body: JSON.stringify(payload) });

export const listFoods = () => api<Food[]>("/nutrition/foods");

export const deleteFood = (id: string) =>
  api<void>(`/nutrition/foods/${id}`, { method: "DELETE" });

export const logMeal = (food_id: string, meal_type: string, servings: number, logged_on?: string) =>
  api<MealEntry>("/nutrition/log", {
    method: "POST",
    body: JSON.stringify({ food_id, meal_type, servings, logged_on: logged_on ?? null }),
  });

export const removeLog = (logId: string) =>
  api<void>(`/nutrition/log/${logId}`, { method: "DELETE" });

/** Nutrition for a given day (YYYY-MM-DD); omit for today. */
export const getDay = (on?: string) =>
  api<DayNutrition>(`/nutrition/day${on ? `?on=${on}` : ""}`);
