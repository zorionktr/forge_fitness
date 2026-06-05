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
import { LabelCropper } from "./LabelCropper";

const MEALS = ["breakfast", "lunch", "dinner", "snack"];

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 8.5A2.5 2.5 0 0 1 5.5 6h1.2a1.5 1.5 0 0 0 1.27-.7l.66-1.05A1.5 1.5 0 0 1 9.9 3.5h4.2a1.5 1.5 0 0 1 1.27.7l.66 1.05A1.5 1.5 0 0 0 17.3 6h1.2A2.5 2.5 0 0 1 21 8.5v9A2.5 2.5 0 0 1 18.5 20h-13A2.5 2.5 0 0 1 3 17.5z" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />
    </svg>
  );
}

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
  const [cropSrc, setCropSrc] = useState<string | null>(null);
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

  // Pick/take a photo → open the cropper so the user can frame the label before OCR.
  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (fileRef.current) fileRef.current.value = "";
    if (file) setCropSrc(URL.createObjectURL(file));
  };

  const analyzeFile = async (file: File) => {
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

  const onCropped = async (blob: Blob) => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
    await analyzeFile(new File([blob], "label.jpg", { type: "image/jpeg" }));
  };

  const closeCropper = () => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
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
        <button className="scan scan--primary" onClick={() => fileRef.current?.click()} disabled={analyzing}>
          <span className={`scan__ico ${analyzing ? "scan__ico--busy" : ""}`}><CameraIcon /></span>
          <span className="scan__label">{analyzing ? "Reading label…" : "Scan label"}</span>
          <span className="scan__hint">{analyzing ? "Hold tight" : "Snap the panel"}</span>
        </button>
        <button className="scan scan--ghost" onClick={() => setDraft(BLANK_FOOD)} disabled={analyzing}>
          <span className="scan__ico"><PencilIcon /></span>
          <span className="scan__label">Add manually</span>
          <span className="scan__hint">Enter the macros</span>
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
          <div className="macros">
            <div className="macro macro--kcal"><b>{t.calories}</b><span>kcal</span></div>
            <div className="macro macro--p"><b>{t.protein_g}</b><span>protein</span></div>
            <div className="macro macro--c"><b>{t.carbs_g}</b><span>carbs</span></div>
            <div className="macro macro--f"><b>{t.fat_g}</b><span>fat</span></div>
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

      {cropSrc && <LabelCropper src={cropSrc} onCancel={closeCropper} onCropped={onCropped} />}

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
