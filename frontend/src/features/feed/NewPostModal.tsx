import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import { createPost, uploadPostMedia } from "@/api/social";
import { useKeyboardInset } from "@/lib/useKeyboardInset";

const MAX_TAGS = 10;
const MAX_IMAGES = 10;

type Mode = "post" | "pr";

interface Pick {
  file: File;
  url: string; // object URL for preview
}

function sanitizeTag(raw: string): string {
  return raw.trim().replace(/^#+/, "").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 30);
}

/** Bottom-sheet composer: a normal post, or a "New PR" announcement for an exercise.
    Both support text + up to 10 #tags + up to 10 images (camera or gallery). */
export function NewPostModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<Mode>("post");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [picks, setPicks] = useState<Pick[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // PR-announcement fields.
  const [exercise, setExercise] = useState("");
  const [weight, setWeight] = useState("");
  const [unit, setUnit] = useState<"kg" | "lb">("kg");
  const [reps, setReps] = useState("");

  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const kbInset = useKeyboardInset();

  // Revoke any remaining preview object URLs once, on unmount (removePick handles the rest).
  const picksRef = useRef<Pick[]>([]);
  picksRef.current = picks;
  useEffect(() => () => picksRef.current.forEach((p) => URL.revokeObjectURL(p.url)), []);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const canPost = useMemo(() => {
    if (busy) return false;
    if (mode === "pr") return exercise.trim().length > 0 && weight.trim().length > 0;
    return body.trim().length > 0 || picks.length > 0;
  }, [busy, mode, body, picks, exercise, weight]);

  const addTag = (raw: string) => {
    const t = sanitizeTag(raw);
    setTagDraft("");
    if (!t || tags.includes(t) || tags.length >= MAX_TAGS) return;
    setTags((prev) => [...prev, t]);
  };

  const onTagKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "," || e.key === " ") {
      e.preventDefault();
      addTag(tagDraft);
    } else if (e.key === "Backspace" && tagDraft === "" && tags.length > 0) {
      setTags((prev) => prev.slice(0, -1));
    }
  };

  const onPickFiles = (list: FileList | null) => {
    if (!list) return;
    const imgs = Array.from(list).filter((f) => f.type.startsWith("image/"));
    setPicks((prev) => {
      const room = MAX_IMAGES - prev.length;
      const next = imgs.slice(0, Math.max(0, room)).map((file) => ({ file, url: URL.createObjectURL(file) }));
      return [...prev, ...next];
    });
    setError(null);
  };

  const removePick = (url: string) =>
    setPicks((prev) => {
      const gone = prev.find((p) => p.url === url);
      if (gone) URL.revokeObjectURL(gone.url);
      return prev.filter((p) => p.url !== url);
    });

  const submit = async () => {
    if (!canPost) return;
    setBusy(true);
    setError(null);
    try {
      const media = picks.length ? await uploadPostMedia(picks.map((p) => p.file)) : [];
      if (mode === "pr") {
        const ex = exercise.trim();
        const repPart = reps.trim() ? ` × ${reps.trim()}` : "";
        const note = body.trim() ? `\n${body.trim()}` : "";
        const headline = `🏆 New PR — ${ex}: ${weight.trim()} ${unit}${repPart}${note}`;
        const prTags = [sanitizeTag(ex), "pr", ...tags].filter(Boolean);
        await createPost({
          kind: "pr",
          body: headline,
          tags: Array.from(new Set(prTags)).slice(0, MAX_TAGS),
          media,
        });
      } else {
        await createPost({ body: body.trim() || undefined, tags, media });
      }
      await queryClient.invalidateQueries({ queryKey: ["feed"] });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't share your post. Try again.");
      setBusy(false);
    }
  };

  return (
    <div className="sheet__overlay" onClick={onClose} style={{ paddingBottom: kbInset || undefined }}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="New post">
        <div className="sheet__grip" aria-hidden="true" />
        <header className="sheet__head">
          <button className="sheet__cancel" type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <span className="sheet__title">{mode === "pr" ? "New PR" : "New post"}</span>
          <button className="sheet__post" type="button" onClick={submit} disabled={!canPost}>
            {busy ? "Posting…" : mode === "pr" ? "Announce" : "Post"}
          </button>
        </header>

        <div className="seg" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "post"}
            className={`seg__btn ${mode === "post" ? "seg__btn--on" : ""}`}
            onClick={() => setMode("post")}
          >
            Post
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "pr"}
            className={`seg__btn ${mode === "pr" ? "seg__btn--on" : ""}`}
            onClick={() => setMode("pr")}
          >
            🏆 New PR
          </button>
        </div>

        <div className="sheet__body">
          {mode === "pr" && (
            <div className="pr-form">
              <label className="pr-form__field pr-form__field--ex">
                <span>Exercise</span>
                <input
                  value={exercise}
                  onChange={(e) => setExercise(e.target.value)}
                  placeholder="e.g. Bench Press"
                  maxLength={60}
                  autoFocus
                />
              </label>
              <label className="pr-form__field">
                <span>Weight</span>
                <input
                  type="number"
                  inputMode="decimal"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  placeholder="100"
                  min="0"
                />
              </label>
              <label className="pr-form__field pr-form__field--unit">
                <span>Unit</span>
                <select value={unit} onChange={(e) => setUnit(e.target.value as "kg" | "lb")}>
                  <option value="kg">kg</option>
                  <option value="lb">lb</option>
                </select>
              </label>
              <label className="pr-form__field">
                <span>Reps</span>
                <input
                  type="number"
                  inputMode="numeric"
                  value={reps}
                  onChange={(e) => setReps(e.target.value)}
                  placeholder="5"
                  min="0"
                />
              </label>
            </div>
          )}

          <textarea
            className="sheet__text"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder={
              mode === "pr"
                ? "Add a note — how did it feel? (optional)"
                : "Share a workout, a win, or ask the community…"
            }
            rows={mode === "pr" ? 2 : 4}
            maxLength={5000}
            autoFocus={mode === "post"}
          />

          {picks.length > 0 && (
            <div className={`sheet__imgs sheet__imgs--n${Math.min(picks.length, 4)}`}>
              {picks.map((p) => (
                <div className="sheet__img" key={p.url}>
                  <img src={p.url} alt="" />
                  <button type="button" className="sheet__img-x" onClick={() => removePick(p.url)} aria-label="Remove image">
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {tags.length > 0 && (
            <div className="tagrow">
              {tags.map((t) => (
                <span className="tag" key={t}>
                  #{t}
                  <button type="button" className="tag__x" onClick={() => setTags((p) => p.filter((x) => x !== t))} aria-label={`Remove ${t}`}>
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="tagfield">
            <span className="tagfield__hash">#</span>
            <input
              value={tagDraft}
              onChange={(e) => setTagDraft(e.target.value)}
              onKeyDown={onTagKey}
              onBlur={() => addTag(tagDraft)}
              placeholder={tags.length >= MAX_TAGS ? "Tag limit reached" : "Add a tag — press enter"}
              disabled={tags.length >= MAX_TAGS}
              maxLength={30}
            />
            <span className="tagfield__count">{tags.length}/{MAX_TAGS}</span>
          </div>

          {error && <p className="sheet__error">{error}</p>}
        </div>

        <footer className="sheet__tools">
          <button type="button" className="sheet__tool" onClick={() => cameraInput.current?.click()} disabled={picks.length >= MAX_IMAGES}>
            📷 Camera
          </button>
          <button type="button" className="sheet__tool" onClick={() => galleryInput.current?.click()} disabled={picks.length >= MAX_IMAGES}>
            🖼 Gallery
          </button>
          <span className="sheet__imgcount">{picks.length}/{MAX_IMAGES}</span>

          <input
            ref={cameraInput}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(e) => {
              onPickFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <input
            ref={galleryInput}
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={(e) => {
              onPickFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </footer>
      </div>
    </div>
  );
}
