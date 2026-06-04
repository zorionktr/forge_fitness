import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api } from "@/api/client";
import {
  getMeasurements,
  getProfile,
  updateProfile,
  uploadAvatar,
  type Measurement,
  type Profile,
} from "@/api/profile";
import { AvatarCropper } from "./AvatarCropper";

type FormState = {
  first_name: string;
  last_name: string;
  sex: string;
  dob: string;
  height_cm: string;
  weight_kg: string;
  body_fat_pct: string;
};

function toForm(p: Profile): FormState {
  return {
    first_name: p.first_name ?? "",
    last_name: p.last_name ?? "",
    sex: p.sex ?? "",
    dob: p.dob ?? "",
    height_cm: p.height_cm?.toString() ?? "",
    weight_kg: p.weight_kg?.toString() ?? "",
    body_fat_pct: p.body_fat_pct?.toString() ?? "",
  };
}

const dash = (v: unknown) => (v === null || v === undefined || v === "" ? "—" : String(v));

export function ProfileScreen() {
  const navigate = useNavigate();
  const logout = useAuth((s) => s.logout);

  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [cropSrc, setCropSrc] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getProfile().then((p) => {
      setProfile(p);
      setForm(toForm(p));
    });
    getMeasurements().then(setMeasurements).catch(() => setMeasurements([]));
  }, []);

  const set = (k: keyof FormState, v: string) => setForm((f) => (f ? { ...f, [k]: v } : f));

  const startEdit = () => {
    if (profile) setForm(toForm(profile));
    setStatus(null);
    setEditing(true);
  };
  const cancelEdit = () => {
    if (profile) setForm(toForm(profile));
    setStatus(null);
    setEditing(false);
  };

  const onSave = async () => {
    if (!form) return;
    setSaving(true);
    setStatus(null);
    const num = (s: string) => (s.trim() === "" ? undefined : Number(s));
    try {
      const updated = await updateProfile({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        sex: form.sex || undefined,
        dob: form.dob || undefined,
        height_cm: num(form.height_cm),
        weight_kg: num(form.weight_kg),
        body_fat_pct: num(form.body_fat_pct),
      });
      setProfile(updated);
      setForm(toForm(updated));
      setMeasurements(await getMeasurements());
      setEditing(false);
    } catch {
      setStatus("Couldn't save — please check the values.");
    } finally {
      setSaving(false);
    }
  };

  // Avatar: pick a file → open the cropper → upload the cropped blob.
  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setCropSrc(URL.createObjectURL(file));
    if (fileRef.current) fileRef.current.value = "";
  };

  const onCropped = async (blob: Blob) => {
    setStatus(null);
    try {
      const file = new File([blob], "avatar.jpg", { type: "image/jpeg" });
      setProfile(await uploadAvatar(file));
    } catch {
      setStatus("Avatar upload failed.");
    } finally {
      if (cropSrc) URL.revokeObjectURL(cropSrc);
      setCropSrc(null);
    }
  };

  const [clearing, setClearing] = useState(false);
  const onClearCoach = async () => {
    if (!window.confirm("Erase all coach chat history and remembered facts? This cannot be undone.")) return;
    setClearing(true);
    try {
      await api<void>("/agent/history", { method: "DELETE" });
      window.alert("Coach data cleared.");
    } catch {
      window.alert("Couldn't clear coach data — please try again.");
    } finally {
      setClearing(false);
    }
  };

  const onLogout = () => {
    logout();
    navigate("/sign-in", { replace: true });
  };

  if (!profile || !form) return <div className="profile">Loading…</div>;

  const initials = (profile.display_name || profile.username).slice(0, 2).toUpperCase();

  return (
    <div className="profile">
      <div className="profile__hero">
        <button
          className={`avatar ${editing ? "avatar--edit" : ""}`}
          onClick={() => editing && fileRef.current?.click()}
          title={editing ? "Change photo" : undefined}
          disabled={!editing}
        >
          {profile.avatar_url ? <img src={profile.avatar_url} alt="avatar" /> : <span>{initials}</span>}
          {editing && <span className="avatar__cam">📷</span>}
        </button>
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPickFile} />
        <div className="profile__heroText">
          <div className="profile__name">{profile.display_name || profile.username}</div>
          <div className="profile__handle">
            @{profile.username}
            {profile.age != null ? ` · ${profile.age} yrs` : ""}
          </div>
        </div>
        {!editing && (
          <button className="profile__editBtn" onClick={startEdit} title="Edit profile">
            ✎ Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="form">
          <div className="form__row">
            <label className="field">
              <span>First name</span>
              <input value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
            </label>
            <label className="field">
              <span>Last name</span>
              <input value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
            </label>
          </div>
          <div className="form__row">
            <label className="field">
              <span>Date of birth</span>
              <input type="date" value={form.dob} onChange={(e) => set("dob", e.target.value)} />
            </label>
            <label className="field">
              <span>Sex</span>
              <select value={form.sex} onChange={(e) => set("sex", e.target.value)}>
                <option value="">—</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </label>
          </div>
          <div className="form__row">
            <label className="field">
              <span>Height (cm)</span>
              <input type="number" step="0.1" value={form.height_cm} onChange={(e) => set("height_cm", e.target.value)} />
            </label>
            <label className="field">
              <span>Weight (kg)</span>
              <input type="number" step="0.1" value={form.weight_kg} onChange={(e) => set("weight_kg", e.target.value)} />
            </label>
            <label className="field">
              <span>Body fat (%)</span>
              <input type="number" step="0.1" value={form.body_fat_pct} onChange={(e) => set("body_fat_pct", e.target.value)} />
            </label>
          </div>

          <div className="form__actions">
            {status && <span className="form__status">{status}</span>}
            <button className="form__cancel" onClick={cancelEdit} disabled={saving}>
              Cancel
            </button>
            <button className="form__save" onClick={onSave} disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </div>
      ) : (
        <div className="details">
          {status && <p className="form__status">{status}</p>}
          <Row label="Full name" value={dash(profile.display_name)} />
          <Row label="Username" value={`@${profile.username}`} />
          <Row label="Email" value={dash(profile.email)} />
          <Row label="Date of birth" value={dash(profile.dob)} />
          <Row label="Age" value={dash(profile.age)} />
          <Row label="Sex" value={dash(profile.sex)} />
          <Row label="Height" value={profile.height_cm != null ? `${profile.height_cm} cm` : "—"} />
          <Row label="Weight" value={profile.weight_kg != null ? `${profile.weight_kg} kg` : "—"} />
          <Row label="Body fat" value={profile.body_fat_pct != null ? `${profile.body_fat_pct} %` : "—"} />
        </div>
      )}

      <div className="history">
        <h3 className="history__title">Weight &amp; height history</h3>
        {measurements.length === 0 ? (
          <p className="history__empty">No measurements yet — update your weight or height to start tracking.</p>
        ) : (
          <ul className="history__list">
            {measurements.map((m) => (
              <li key={m.id} className="history__item">
                <span className="history__when">{new Date(m.measured_at).toLocaleString()}</span>
                <span className="history__vals">
                  {m.weight_kg != null && <b>{m.weight_kg} kg</b>}
                  {m.height_cm != null && <span> · {m.height_cm} cm</span>}
                  {m.body_fat_pct != null && <span> · {m.body_fat_pct}% bf</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="danger">
        <div className="danger__text">
          <div className="danger__title">Coach data</div>
          <div className="danger__hint">Clear your full chat history and everything the coach remembers about you.</div>
        </div>
        <button className="danger__btn" onClick={onClearCoach} disabled={clearing}>
          {clearing ? "Clearing…" : "Clear coach data"}
        </button>
      </div>

      <button className="profile__logout" onClick={onLogout}>
        Log out
      </button>

      {cropSrc && (
        <AvatarCropper
          src={cropSrc}
          onCancel={() => {
            URL.revokeObjectURL(cropSrc);
            setCropSrc(null);
          }}
          onCropped={onCropped}
        />
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="details__row">
      <span className="details__label">{label}</span>
      <span className="details__value">{value}</span>
    </div>
  );
}
