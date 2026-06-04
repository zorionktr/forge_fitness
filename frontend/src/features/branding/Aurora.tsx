/**
 * Animated ambient background: three slow-drifting blurred color blobs over a
 * dark base, plus a faint grid. Pure CSS (see styles/branding.css) — no canvas,
 * GPU-friendly, and respects prefers-reduced-motion. Used behind auth + onboarding.
 */
export function Aurora() {
  return (
    <div className="aurora" aria-hidden="true">
      <span className="aurora__blob aurora__blob--1" />
      <span className="aurora__blob aurora__blob--2" />
      <span className="aurora__blob aurora__blob--3" />
      <div className="aurora__grid" />
      <div className="aurora__vignette" />
    </div>
  );
}
