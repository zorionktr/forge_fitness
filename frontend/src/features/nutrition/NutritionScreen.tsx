import { useEffect, useRef, useState } from "react";
import {
  analyzeLabel,
  deleteFood,
  getDay,
  listFoods,
  logMeal,
  removeLog,
  type DayNutrition,
  type Food,
  type FoodDraft,
} from "@/api/nutrition";
import { FoodReview } from "./FoodReview";

const MEALS = ["breakfast", "lunch", "dinner", "snack"];

const BLANK_FOOD: FoodDraft = {
  name: null, brand: null, serving_size: null, calories: null, protein_g: null,
  carbs_g: null, fat_g: null, fiber_g: null, sugar_g: null, sodium_mg: null,
  ingredients: null, image_url: null, raw: {},
};

const localDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const TODAY = localDay(new Date());

function shiftDay(day: string, delta: number): string {
  const [y, m, d] = day.split("-").map(Number);
  return localDay(new Date(y, m - 1, d + delta));
}

function dayLabel(day: string): string {
  if (day === TODAY) return "Today";
  if (day === shiftDay(TODAY, -1)) return "Yesterday";
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function FoodCard({ food, onLog, onDelete }: { food: Food; onLog: (meal: string) => void; onDelete: () => void }) {
  const [meal, setMeal] = useState("breakfast");
  return (
    <div className="food">
      <div className="food__top">
        <div className="food__name">{food.name}</div>
        <button className="food__del" onClick={onDelete} title="Delete food">✕</button>
      </div>
      <div className="food__macros">
        <span><b>{food.calories ?? "—"}</b> kcal</span>
        <span><b>{food.protein_g ?? "—"}</b>g P</span>
        <span><b>{food.carbs_g ?? "—"}</b>g C</span>
        <span><b>{food.fat_g ?? "—"}</b>g F</span>
      </div>
      {food.serving_size && <div className="food__serving">per {food.serving_size}</div>}
      <div className="food__log">
        <select value={meal} onChange={(e) => setMeal(e.target.value)}>
          {MEALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <button onClick={() => onLog(meal)}>+ Log</button>
      </div>
    </div>
  );
}

export function NutritionScreen() {
  const [foods, setFoods] = useState<Food[]>([]);
  const [selectedDay, setSelectedDay] = useState(TODAY);
  const [day, setDay] = useState<DayNutrition | null>(null);
  const [draft, setDraft] = useState<FoodDraft | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listFoods().then(setFoods).catch(() => setFoods([]));
  }, []);

  useEffect(() => {
    getDay(selectedDay).then(setDay).catch(() => setDay(null));
  }, [selectedDay]);

  const reloadDay = () => getDay(selectedDay).then(setDay).catch(() => {});

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (fileRef.current) fileRef.current.value = "";
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    try {
      setDraft(await analyzeLabel(file));
    } catch {
      setError("Couldn't read that image — try a clearer, well-lit photo of the label.");
    } finally {
      setAnalyzing(false);
    }
  };

  const onLog = async (food: Food, meal: string) => {
    await logMeal(food.id, meal, 1, selectedDay);
    await reloadDay();
  };

  const onRemove = async (logId: string) => {
    await removeLog(logId);
    await reloadDay();
  };

  const t = day?.totals;
  const isToday = selectedDay === TODAY;

  return (
    <div className="nutrition">
      <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={onFile} />
      <div className="scan__row">
        <button className="scan" onClick={() => fileRef.current?.click()} disabled={analyzing}>
          {analyzing ? "Reading label…" : "📷 Scan a nutrition label"}
        </button>
        <button className="scan scan--ghost" onClick={() => setDraft(BLANK_FOOD)} disabled={analyzing}>
          ✏️ Add manually
        </button>
      </div>
      {error && <p className="nutrition__error">{error}</p>}

      <div className="totals">
        <div className="day__nav">
          <button onClick={() => setSelectedDay((d) => shiftDay(d, -1))} title="Previous day">‹</button>
          <span className="day__label">{dayLabel(selectedDay)}</span>
          <button onClick={() => setSelectedDay((d) => shiftDay(d, 1))} disabled={isToday} title="Next day">›</button>
        </div>
        {t && (
          <div className="totals__grid">
            <span><b>{t.calories}</b> kcal</span>
            <span><b>{t.protein_g}</b>g protein</span>
            <span><b>{t.carbs_g}</b>g carbs</span>
            <span><b>{t.fat_g}</b>g fat</span>
          </div>
        )}
        {day && day.entries.length > 0 ? (
          <ul className="totals__entries">
            {day.entries.map((e) => (
              <li key={e.id}>
                <span>{e.food_name} · {e.meal_type} ×{e.servings}</span>
                <span className="totals__right">
                  <span className="totals__kcal">{e.calories ?? "—"} kcal</span>
                  <button className="totals__del" onClick={() => onRemove(e.id)} title="Remove from this day">✕</button>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="totals__empty">Nothing logged {isToday ? "today" : "this day"}.</p>
        )}
      </div>

      <h3 className="nutrition__h">My foods{!isToday && <span className="nutrition__sub"> · logging to {dayLabel(selectedDay)}</span>}</h3>
      {foods.length === 0 ? (
        <p className="nutrition__empty">No foods yet — scan a label or add one manually.</p>
      ) : (
        <div className="food__grid">
          {foods.map((f) => (
            <FoodCard
              key={f.id}
              food={f}
              onLog={(meal) => onLog(f, meal)}
              onDelete={async () => {
                await deleteFood(f.id);
                setFoods(await listFoods());
                await reloadDay();
              }}
            />
          ))}
        </div>
      )}

      {draft && (
        <FoodReview
          draft={draft}
          onCancel={() => setDraft(null)}
          onSaved={async () => {
            setDraft(null);
            setFoods(await listFoods());
          }}
        />
      )}
    </div>
  );
}
