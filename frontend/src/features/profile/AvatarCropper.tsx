import { useCallback, useState } from "react";
import Cropper, { type Area } from "react-easy-crop";
import { getCroppedBlob } from "./cropImage";

/** Modal: crop + zoom a picked image into a round avatar, then hand back a small JPEG blob. */
export function AvatarCropper({
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
  const [areaPixels, setAreaPixels] = useState<Area | null>(null);
  const [busy, setBusy] = useState(false);

  const onComplete = useCallback((_area: Area, px: Area) => setAreaPixels(px), []);

  const save = async () => {
    if (!areaPixels) return;
    setBusy(true);
    try {
      await onCropped(await getCroppedBlob(src, areaPixels));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cropper__overlay" onClick={() => !busy && onCancel()}>
      <div className="cropper" onClick={(e) => e.stopPropagation()}>
        <div className="cropper__area">
          <Cropper
            image={src}
            crop={crop}
            zoom={zoom}
            aspect={1}
            cropShape="round"
            showGrid={false}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onComplete}
          />
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
            {busy ? "Saving…" : "Save photo"}
          </button>
        </div>
      </div>
    </div>
  );
}
