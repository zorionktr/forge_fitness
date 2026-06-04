/**
 * Forge flame logo. The flame path draws itself in (stroke dash) and a soft glow
 * pulses behind it. `size` controls the px box; `animated` toggles the intro draw.
 */
export function BrandMark({ size = 72, animated = true }: { size?: number; animated?: boolean }) {
  return (
    <span
      className={animated ? "brandmark brandmark--animated" : "brandmark"}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 512 512" width={size} height={size} role="img" aria-label="Forge">
        <defs>
          <linearGradient id="forge-flame" x1="128" y1="64" x2="384" y2="448" gradientUnits="userSpaceOnUse">
            <stop stopColor="#ffb347" />
            <stop offset="0.5" stopColor="#ff5a36" />
            <stop offset="1" stopColor="#ff2d75" />
          </linearGradient>
        </defs>
        <path
          className="brandmark__flame"
          d="M256 92c14 64-34 86-60 122-30 41-30 86 6 118-12-30 2-52 24-66-6 40 18 56 18 56s-30-44 28-78c40-24 36-70 22-96 40 22 62 64 62 110 0 79-64 132-128 132S100 437 100 358c0-58 36-98 70-140 30-37 70-78 86-126Z"
          fill="url(#forge-flame)"
        />
      </svg>
    </span>
  );
}
