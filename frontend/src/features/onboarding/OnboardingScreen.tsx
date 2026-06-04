import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { getProfile, updateProfile, type ProfileUpdate } from "@/api/profile";
import { Aurora } from "@/features/branding/Aurora";
import { BrandMark } from "@/features/branding/BrandMark";
import { OptionCard, SliderField, type Option } from "./parts";

type Goal = "lose" | "build" | "fit" | "health";
type Sex = "male" | "female" | "other";
type Activity = "sedentary" | "light" | "moderate" | "active" | "athlete";
type Persona = "hype" | "balanced" | "zen" | "drill";
type Units = "metric" | "imperial";

const GOALS: Option<Goal>[] = [
  { value: "lose", label: "Lose fat", hint: "Lean down, keep strength", icon: "🔥" },
  { value: "build", label: "Build muscle", hint: "Add size and power", icon: "💪" },
  { value: "fit", label: "Get fit", hint: "Energy, stamina, mobility", icon: "⚡" },
  { value: "health", label: "Stay healthy", hint: "Feel good, move daily", icon: "🌱" },
];

const SEXES: Option<Sex>[] = [
  { value: "male", label: "Male", icon: "♂" },
  { value: "female", label: "Female", icon: "♀" },
  { value: "other", label: "Prefer not to say", icon: "•" },
];

const ACTIVITIES: Option<Activity>[] = [
  { value: "sedentary", label: "Mostly sitting", hint: "Little exercise", icon: "🪑" },
  { value: "light", label: "Lightly active", hint: "1–2 days / week", icon: "🚶" },
  { value: "moderate", label: "Moderately active", hint: "3–4 days / week", icon: "🏃" },
  { value: "active", label: "Very active", hint: "5–6 days / week", icon: "🏋️" },
  { value: "athlete", label: "Athlete", hint: "Daily / twice a day", icon: "🥇" },
];

const PERSONAS: Option<Persona>[] = [
  { value: "hype", label: "Hype Beast", hint: "Loud, fired-up, all gas", icon: "📣" },
  { value: "balanced", label: "Balanced Pro", hint: "Supportive and clear", icon: "🤝" },
  { value: "zen", label: "Calm & Mindful", hint: "Gentle, no pressure", icon: "🧘" },
  { value: "drill", label: "Drill Sergeant", hint: "Tough love, no excuses", icon: "🎖️" },
];

const QUESTION_COUNT = 6; // goal, sex, dob, body, activity, persona

// --- Draft persistence: keep answers across reloads so a refresh mid-flow doesn't reset.
const DRAFT_KEY = "forge.onboarding";

interface Draft {
  step: number;
  goal: Goal | null;
  sex: Sex | null;
  dob: string;
  units: Units;
  heightCm: number;
  weightKg: number;
  bodyFat: number;
  knowsBodyFat: boolean;
  activity: Activity | null;
  persona: Persona | null;
}

function loadDraft(): Partial<Draft> {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? (JSON.parse(raw) as Partial<Draft>) : {};
  } catch {
    return {};
  }
}
const clearDraft = () => localStorage.removeItem(DRAFT_KEY);

const cmToInches = (cm: number) => cm / 2.54;
const inchesToCm = (inch: number) => Math.round(inch * 2.54);
const kgToLb = (kg: number) => kg * 2.2046;
const lbToKg = (lb: number) => Math.round((lb / 2.2046) * 10) / 10;
const ftIn = (cm: number) => {
  const total = Math.round(cmToInches(cm));
  return `${Math.floor(total / 12)}'${total % 12}"`;
};

/** Multi-step animated onboarding. Collects profile data and PATCHes /profile/me,
 *  then drops the user into the app. Skippable — nothing here blocks the session. */
export function OnboardingScreen() {
  const navigate = useNavigate();

  // Hydrate from a saved draft (if any) so a refresh resumes where the user left off.
  const draft = useRef(loadDraft()).current;

  // step 0 = intro, 1..QUESTION_COUNT = questions, QUESTION_COUNT+1 = building.
  // Never resume on the terminal "building" step — re-enter the last question instead.
  const [step, setStep] = useState(Math.min(draft.step ?? 0, QUESTION_COUNT));
  const [dir, setDir] = useState<1 | -1>(1);
  const [name, setName] = useState<string>("");

  const [goal, setGoal] = useState<Goal | null>(draft.goal ?? null);
  const [sex, setSex] = useState<Sex | null>(draft.sex ?? null);
  const [dob, setDob] = useState(draft.dob ?? "");
  const [units, setUnits] = useState<Units>(draft.units ?? "metric");
  const [heightCm, setHeightCm] = useState(draft.heightCm ?? 173);
  const [weightKg, setWeightKg] = useState(draft.weightKg ?? 72);
  const [bodyFat, setBodyFat] = useState(draft.bodyFat ?? 20);
  const [knowsBodyFat, setKnowsBodyFat] = useState(draft.knowsBodyFat ?? false);
  const [activity, setActivity] = useState<Activity | null>(draft.activity ?? null);
  const [persona, setPersona] = useState<Persona | null>(draft.persona ?? null);

  const [error, setError] = useState<string | null>(null);

  // Persist the draft on every change so a reload keeps the filled-in answers.
  useEffect(() => {
    const snapshot: Draft = {
      step, goal, sex, dob, units, heightCm, weightKg, bodyFat, knowsBodyFat, activity, persona,
    };
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(snapshot));
    } catch {
      /* storage full / unavailable — non-fatal */
    }
  }, [step, goal, sex, dob, units, heightCm, weightKg, bodyFat, knowsBodyFat, activity, persona]);

  // Greet by first name if we can read it back from the just-created profile.
  useEffect(() => {
    let alive = true;
    getProfile()
      .then((p) => alive && setName(p.first_name ?? p.display_name ?? ""))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const go = (next: number) => {
    setDir(next > step ? 1 : -1);
    setError(null);
    setStep(next);
  };
  const back = () => go(Math.max(0, step - 1));
  const next = () => go(step + 1);

  // Selecting a single-choice card advances automatically for momentum.
  const choose = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    window.setTimeout(next, 260);
  };

  const submitted = useRef(false);
  const submit = async () => {
    if (submitted.current) return;
    submitted.current = true;
    const patch: ProfileUpdate = {
      ...(sex ? { sex } : {}),
      ...(dob ? { dob } : {}),
      height_cm: heightCm,
      weight_kg: weightKg,
      ...(knowsBodyFat ? { body_fat_pct: bodyFat } : {}),
      ...(activity ? { activity_level: activity } : {}),
      ...(persona ? { coach_persona: persona } : {}),
    };
    try {
      await updateProfile(patch);
      clearDraft(); // finished — drop the saved answers
      // Brief beat so the "forging" animation reads as finishing, then enter the app.
      window.setTimeout(() => navigate("/feed", { replace: true }), 900);
    } catch (err) {
      submitted.current = false;
      setError(err instanceof ApiError ? err.detail : "Couldn't save your profile.");
    }
  };

  const skip = () => {
    clearDraft();
    navigate("/feed", { replace: true });
  };

  // Kick off the save once we land on the building step.
  useEffect(() => {
    if (step === QUESTION_COUNT + 1) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const progressPct = useMemo(() => {
    if (step <= 0) return 0;
    if (step > QUESTION_COUNT) return 100;
    return ((step - 1) / QUESTION_COUNT) * 100;
  }, [step]);

  const dobValid = dob !== "" && new Date(dob) < new Date() && new Date(dob) > new Date("1900-01-01");

  return (
    <div className="onb">
      <Aurora />

      {step > 0 && step <= QUESTION_COUNT && (
        <header className="onb__top">
          <button type="button" className="onb__back" onClick={back} aria-label="Back">
            ←
          </button>
          <div className="onb__progress">
            <span className="onb__progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <button type="button" className="onb__skip" onClick={skip}>
            Skip
          </button>
        </header>
      )}

      <div className="onb__stage">
        <div className="onb__step" key={step} data-dir={dir}>
          {step === 0 && (
            <section className="onb__intro">
              <BrandMark size={72} />
              <h1 className="onb__hi">{name ? `Welcome, ${name}.` : "Welcome to Forge."}</h1>
              <p className="onb__lede">
                A few quick questions and your coach will tailor everything — workouts, food
                targets, and tone — to you. Takes about a minute.
              </p>
              <button className="btn-primary" type="button" onClick={next}>
                <span className="btn-primary__label">Let's go</span>
                <span className="btn-primary__shine" aria-hidden="true" />
              </button>
            </section>
          )}

          {step === 1 && (
            <Question title="What's your main goal?" subtitle="We'll shape your plan around this.">
              <div className="opt-grid">
                {GOALS.map((o, i) => (
                  <OptionCard key={o.value} option={o} index={i} selected={goal === o.value} onSelect={choose(setGoal)} />
                ))}
              </div>
            </Question>
          )}

          {step === 2 && (
            <Question title="A bit about you" subtitle="Used to estimate your calorie needs.">
              <div className="opt-grid">
                {SEXES.map((o, i) => (
                  <OptionCard key={o.value} option={o} index={i} selected={sex === o.value} onSelect={choose(setSex)} />
                ))}
              </div>
            </Question>
          )}

          {step === 3 && (
            <Question title="When's your birthday?" subtitle="Age helps fine-tune your targets.">
              <label className="dob">
                <input
                  type="date"
                  value={dob}
                  max={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setDob(e.target.value)}
                />
              </label>
              <StepNav onNext={next} disabled={!dobValid} />
            </Question>
          )}

          {step === 4 && (
            <Question title="Your measurements" subtitle="Slide to set — you can change these anytime.">
              <div className="units">
                <button
                  type="button"
                  className={units === "metric" ? "units__btn is-on" : "units__btn"}
                  onClick={() => setUnits("metric")}
                >
                  Metric
                </button>
                <button
                  type="button"
                  className={units === "imperial" ? "units__btn is-on" : "units__btn"}
                  onClick={() => setUnits("imperial")}
                >
                  Imperial
                </button>
              </div>

              {units === "metric" ? (
                <>
                  <SliderField label="Height" value={heightCm} min={120} max={220} unit="cm" onChange={setHeightCm} />
                  <SliderField label="Weight" value={weightKg} min={35} max={200} unit="kg" onChange={setWeightKg} />
                </>
              ) : (
                <>
                  <SliderField
                    label="Height"
                    value={Math.round(cmToInches(heightCm))}
                    min={48}
                    max={84}
                    unit=""
                    format={() => ftIn(heightCm)}
                    onChange={(inch) => setHeightCm(inchesToCm(inch))}
                  />
                  <SliderField
                    label="Weight"
                    value={Math.round(kgToLb(weightKg))}
                    min={80}
                    max={440}
                    unit="lb"
                    onChange={(lb) => setWeightKg(lbToKg(lb))}
                  />
                </>
              )}

              <label className="bf-toggle">
                <input type="checkbox" checked={knowsBodyFat} onChange={(e) => setKnowsBodyFat(e.target.checked)} />
                <span>I know my body fat %</span>
              </label>
              {knowsBodyFat && (
                <SliderField label="Body fat" value={bodyFat} min={5} max={50} unit="%" onChange={setBodyFat} />
              )}

              <StepNav onNext={next} disabled={false} />
            </Question>
          )}

          {step === 5 && (
            <Question title="How active are you?" subtitle="Be honest — we calibrate from here.">
              <div className="opt-grid">
                {ACTIVITIES.map((o, i) => (
                  <OptionCard
                    key={o.value}
                    option={o}
                    index={i}
                    selected={activity === o.value}
                    onSelect={choose(setActivity)}
                  />
                ))}
              </div>
            </Question>
          )}

          {step === 6 && (
            <Question title="Pick your coach's vibe" subtitle="How should your coach talk to you?">
              <div className="opt-grid">
                {PERSONAS.map((o, i) => (
                  <OptionCard
                    key={o.value}
                    option={o}
                    index={i}
                    selected={persona === o.value}
                    onSelect={choose(setPersona)}
                  />
                ))}
              </div>
            </Question>
          )}

          {step === QUESTION_COUNT + 1 && (
            <section className="onb__building">
              <div className="forge-loader" aria-hidden="true">
                <span className="forge-loader__ring" />
                <span className="forge-loader__ring" />
                <BrandMark size={56} animated={false} />
              </div>
              <h2 className="onb__hi">{error ? "Hmm, that didn't save" : "Forging your plan…"}</h2>
              <p className="onb__lede">
                {error ?? "Crunching your goals, body, and activity into a starting plan."}
              </p>
              {error && (
                <button
                  className="btn-primary"
                  type="button"
                  onClick={() => {
                    submitted.current = false;
                    submit();
                  }}
                >
                  <span className="btn-primary__label">Try again</span>
                  <span className="btn-primary__shine" aria-hidden="true" />
                </button>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

function Question({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="q">
      <h2 className="q__title">{title}</h2>
      {subtitle && <p className="q__sub">{subtitle}</p>}
      <div className="q__body">{children}</div>
    </section>
  );
}

function StepNav({ onNext, disabled }: { onNext: () => void; disabled: boolean }) {
  return (
    <button className="btn-primary q__next" type="button" onClick={onNext} disabled={disabled}>
      <span className="btn-primary__label">Continue</span>
      <span className="btn-primary__shine" aria-hidden="true" />
    </button>
  );
}
