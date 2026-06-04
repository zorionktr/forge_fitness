import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import { createPost, uploadPostMedia } from "@/api/social";

const MAX_TAGS = 10;
const MAX_IMAGES = 10;

interface Pick {
  file: File;
  url: string; // object URL for preview
}

function sanitizeTag(raw: string): string {
  return raw.trim().replace(/^#+/, "").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 30);
}

/** Bottom-sheet composer: text + up to 10 #tags + up to 10 images (camera or gallery). */
export function NewPostModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();

  const [body, setBody] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [picks, setPicks] = useState<Pick[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);

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

  const canPost = useMemo(
    () => !busy && (body.trim().length > 0 || picks.length > 0),
    [busy, body, picks],
  );

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
      await createPost({ body: body.trim() || undefined, tags, media });
      await queryClient.invalidateQueries({ queryKey: ["feed"] });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't share your post. Try again.");
      setBusy(false);
    }
  };

  return (
    <div className="sheet__overlay" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="New post">
        <div className="sheet__grip" aria-hidden="true" />
        <header className="sheet__head">
          <button className="sheet__cancel" type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <span className="sheet__title">New post</span>
          <button className="sheet__post" type="button" onClick={submit} disabled={!canPost}>
            {busy ? "Posting…" : "Post"}
          </button>
        </header>

        <div className="sheet__body">
          <textarea
            className="sheet__text"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Share a workout, a win, or ask the community…"
            rows={4}
            maxLength={5000}
            autoFocus
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
