import { useState } from "react";
import { createFood, type FoodDraft } from "@/api/nutrition";

type FormState = Record<string, string>;

const NUM_FIELDS: { key: string; label: string }[] = [
  { key: "calories", label: "Calories" },
  { key: "protein_g", label: "Protein (g)" },
  { key: "carbs_g", label: "Carbs (g)" },
  { key: "fat_g", label: "Fat (g)" },
  { key: "fiber_g", label: "Fiber (g)" },
  { key: "sugar_g", label: "Sugar (g)" },
  { key: "sodium_mg", label: "Sodium (mg)" },
];

function initial(draft: FoodDraft): FormState {
  const s: FormState = {
    name: draft.name ?? "",
    brand: draft.brand ?? "",
    serving_size: draft.serving_size ?? "",
    ingredients: draft.ingredients ?? "",
  };
  const d = draft as unknown as Record<string, unknown>;
  for (const { key } of NUM_FIELDS) {
    const v = d[key];
    s[key] = v === null || v === undefined ? "" : String(v);
  }
  return s;
}

/** Review/edit OCR-extracted fields, name the food, and save it to the user's DB. */
export function FoodReview({
  draft,
  onCancel,
  onSaved,
}: {
  draft: FoodDraft;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => initial(draft));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const fromLabel = Boolean(draft.image_url); // OCR scan vs. manual entry

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const num = (s: string) => (s.trim() === "" ? null : Number(s));

  const onSave = async () => {
    if (!form.name.trim()) {
      setErr("Please give this food a name.");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      await createFood({
        name: form.name.trim(),
        brand: form.brand || null,
        serving_size: form.serving_size || null,
        ingredients: form.ingredients || null,
        calories: num(form.calories),
        protein_g: num(form.protein_g),
        carbs_g: num(form.carbs_g),
        fat_g: num(form.fat_g),
        fiber_g: num(form.fiber_g),
        sugar_g: num(form.sugar_g),
        sodium_mg: num(form.sodium_mg),
        image_url: draft.image_url,
        raw: draft.raw,
      });
      onSaved();
    } catch {
      setErr("Couldn't save — please check the values.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="review__overlay" onClick={() => !saving && onCancel()}>
      <div className="review" onClick={(e) => e.stopPropagation()}>
        <h3 className="review__title">{fromLabel ? "Review & name this food" : "Add a food"}</h3>
        <p className="review__hint">
          {fromLabel
            ? "We read these from the label — fix anything that's off, then give it a name."
            : "Enter the nutrition details (per serving). Only the name is required — fill in what you know."}
        </p>

        {draft.image_url && <img className="review__img" src={draft.image_url} alt="label" />}

        <label className="field">
          <span>Name *</span>
          <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Morning Yogurt" />
        </label>
        <div className="form__row">
          <label className="field">
            <span>Brand</span>
            <input value={form.brand} onChange={(e) => set("brand", e.target.value)} />
          </label>
          <label className="field">
            <span>Serving size</span>
            <input value={form.serving_size} onChange={(e) => set("serving_size", e.target.value)} />
          </label>
        </div>

        <div className="review__macros">
          {NUM_FIELDS.map(({ key, label }) => (
            <label className="field" key={key}>
              <span>{label}</span>
              <input type="number" step="0.1" value={form[key]} onChange={(e) => set(key, e.target.value)} />
            </label>
          ))}
        </div>

        <label className="field">
          <span>Ingredients</span>
          <textarea rows={3} value={form.ingredients} onChange={(e) => set("ingredients", e.target.value)} />
        </label>

        {err && <p className="review__err">{err}</p>}
        <div className="review__actions">
          <button className="form__cancel" onClick={onCancel} disabled={saving}>Cancel</button>
          <button className="form__save" onClick={onSave} disabled={saving}>
            {saving ? "Saving…" : "Save food"}
          </button>
        </div>
      </div>
    </div>
  );
}
