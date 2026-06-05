export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

/** Crop `src` to the selected pixel rectangle, preserving its aspect ratio (unlike the square
    avatar crop) and downscaling so the longest side ≤ `maxDim` — sharp enough for OCR, small
    enough to upload fast. Returns a JPEG blob. */
export async function cropToBlob(src: string, crop: Rect, maxDim = 1600, quality = 0.92): Promise<Blob> {
  const image = await loadImage(src);
  const scale = Math.min(1, maxDim / Math.max(crop.width, crop.height));
  const w = Math.max(1, Math.round(crop.width * scale));
  const h = Math.max(1, Math.round(crop.height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas unsupported");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(image, crop.x, crop.y, crop.width, crop.height, 0, 0, w, h);

  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("crop failed"))), "image/jpeg", quality),
  );
}
