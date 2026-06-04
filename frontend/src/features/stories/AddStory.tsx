import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import { createStory, uploadPostMedia } from "@/api/social";

/** Add-to-story sheet: pick an image (camera/gallery), optional caption, publish. */
export function AddStory({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  const pick = (list: FileList | null) => {
    const f = list?.[0];
    if (!f || !f.type.startsWith("image/")) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError(null);
  };

  const share = async () => {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    try {
      const media = await uploadPostMedia([file]);
      await createStory(media, caption.trim() || undefined);
      await queryClient.invalidateQueries({ queryKey: ["stories"] });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't add your story. Try again.");
      setBusy(false);
    }
  };

  return (
    <div className="sheet__overlay" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Add to story">
        <div className="sheet__grip" aria-hidden="true" />
        <header className="sheet__head">
          <button className="sheet__cancel" type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <span className="sheet__title">Add to story</span>
          <button className="sheet__post" type="button" onClick={share} disabled={!file || busy}>
            {busy ? "Sharing…" : "Share"}
          </button>
        </header>

        <div className="sheet__body">
          {preview ? (
            <div className="addstory__preview">
              <img src={preview} alt="" />
            </div>
          ) : (
            <div className="addstory__empty">
              <p>Pick a photo to share for the next 24 hours.</p>
            </div>
          )}

          {preview && (
            <input
              className="tagfield__plain"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Add a caption…"
              maxLength={500}
            />
          )}

          {error && <p className="sheet__error">{error}</p>}
        </div>

        <footer className="sheet__tools">
          <button type="button" className="sheet__tool" onClick={() => cameraInput.current?.click()}>
            📷 Camera
          </button>
          <button type="button" className="sheet__tool" onClick={() => galleryInput.current?.click()}>
            🖼 Gallery
          </button>
          <input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
          <input ref={galleryInput} type="file" accept="image/*" hidden onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
        </footer>
      </div>
    </div>
  );
}
