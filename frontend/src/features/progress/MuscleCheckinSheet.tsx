import { useEffect, useState } from "react";
import { MUSCLE_GROUPS } from "@/api/streaks";

/** Display label + emoji for each muscle group key. */
export const MUSCLE_META: Record<string, { label: string; emoji: string }> = {
  chest: { label: "Chest", emoji: "🫀" },
  back: { label: "Back", emoji: "🔙" },
  shoulders: { label: "Shoulders", emoji: "🤷" },
  biceps: { label: "Biceps", emoji: "💪" },
  triceps: { label: "Triceps", emoji: "🦾" },
  forearms: { label: "Forearms", emoji: "🤜" },
  core: { label: "Core", emoji: "🧱" },
  quads: { label: "Quads", emoji: "🦵" },
  hamstrings: { label: "Hamstrings", emoji: "🦿" },
  glutes: { label: "Glutes", emoji: "🍑" },
  calves: { label: "Calves", emoji: "🐐" },
  cardio: { label: "Cardio", emoji: "🏃" },
};

export const muscleLabel = (key: string) => MUSCLE_META[key]?.label ?? key;

/** Bottom-sheet to pick which muscles were trained, then confirm the check-in. */
export function MuscleCheckinSheet({
  initial,
  busy,
  onConfirm,
  onClose,
}: {
  initial: string[];
  busy: boolean;
  onConfirm: (muscles: string[]) => void;
  onClose: () => void;
}) {
  const [picked, setPicked] = useState<string[]>(initial);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const toggle = (m: string) =>
    setPicked((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]));

  return (
    <div className="sheet__overlay" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Log workout">
        <div className="sheet__grip" aria-hidden="true" />
        <header className="sheet__head">
          <button className="sheet__cancel" type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <span className="sheet__title">What did you train?</span>
          <button className="sheet__post" type="button" onClick={() => onConfirm(picked)} disabled={busy}>
            {busy ? "Saving…" : "Check in"}
          </button>
        </header>

        <div className="sheet__body">
          <p className="muscle__hint">Tap the muscle groups you hit today (optional).</p>
          <div className="muscle__grid">
            {MUSCLE_GROUPS.map((m) => {
              const on = picked.includes(m);
              return (
                <button
                  key={m}
                  type="button"
                  className={`muscle__chip ${on ? "muscle__chip--on" : ""}`}
                  aria-pressed={on}
                  onClick={() => toggle(m)}
                >
                  <span className="muscle__emoji" aria-hidden="true">{MUSCLE_META[m].emoji}</span>
                  {MUSCLE_META[m].label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
