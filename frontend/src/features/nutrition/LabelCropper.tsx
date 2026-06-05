import { useCallback, useState } from "react";
import Cropper, { type Area } from "react-easy-crop";
import { cropToBlob } from "./labelCrop";

const PRESETS = [
  { key: "panel", label: "Panel", aspect: 3 / 4 },
  { key: "square", label: "Square", aspect: 1 },
  { key: "wide", label: "Wide", aspect: 4 / 3 },
] as const;

/** Modal to frame just the nutrition panel / ingredients before OCR. Rectangular crop with a
    few aspect presets (panels are tall, ingredient lists are wide) + pan/zoom. */
export function LabelCropper({
  src,
  onCancel,
  onCropped,
}: {
  src: string;
  onCancel: () => void;
  onCropped: (blob: Blob) => Promise<void> | void;
}) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [aspect, setAspect] = useState<number>(3 / 4);
  const [areaPixels, setAreaPixels] = useState<Area | null>(null);
  const [busy, setBusy] = useState(false);

  const onComplete = useCallback((_area: Area, px: Area) => setAreaPixels(px), []);

  const save = async () => {
    if (!areaPixels) return;
    setBusy(true);
    try {
      await onCropped(await cropToBlob(src, areaPixels));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cropper__overlay" onClick={() => !busy && onCancel()}>
      <div className="cropper" onClick={(e) => e.stopPropagation()}>
        <p className="cropper__hint">Frame the nutrition facts or ingredients, then scan.</p>
        <div className="cropper__area">
          <Cropper
            image={src}
            crop={crop}
            zoom={zoom}
            aspect={aspect}
            showGrid
            objectFit="contain"
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onComplete}
          />
        </div>

        <div className="cropper__aspects">
          {PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`cropper__aspect ${Math.abs(aspect - p.aspect) < 0.001 ? "cropper__aspect--on" : ""}`}
              onClick={() => setAspect(p.aspect)}
              disabled={busy}
            >
              {p.label}
            </button>
          ))}
        </div>

        <input
          className="cropper__zoom"
          type="range"
          min={1}
          max={3}
          step={0.01}
          value={zoom}
          onChange={(e) => setZoom(Number(e.target.value))}
          aria-label="Zoom"
        />
        <div className="cropper__actions">
          <button className="cropper__cancel" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="cropper__save" onClick={save} disabled={busy || !areaPixels}>
            {busy ? "Cropping…" : "Scan this"}
          </button>
        </div>
      </div>
    </div>
  );
}
