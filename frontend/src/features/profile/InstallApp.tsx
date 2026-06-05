import { useState } from "react";
import { isIos, useInstallPrompt } from "@/lib/pwa";

/* "Install app" card for the profile screen. Adapts to the platform:
   - Android/Chrome/Edge/desktop: a one-tap native install button.
   - iOS/iPadOS (no programmatic install): step-by-step Add-to-Home-Screen help.
   - Already installed: renders nothing. */
export function InstallApp() {
  const { canPrompt, installed, promptInstall } = useInstallPrompt();
  const [showIosHelp, setShowIosHelp] = useState(false);
  const [busy, setBusy] = useState(false);

  if (installed) return null;

  const ios = isIos();

  const onInstall = async () => {
    setBusy(true);
    try {
      await promptInstall();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="install">
      <div className="install__row">
        <div className="install__text">
          <div className="install__title">Install Forge</div>
          <div className="install__hint">
            Add Forge to your home screen for a full-screen, app-like experience.
          </div>
        </div>
        {canPrompt ? (
          <button className="install__btn" onClick={onInstall} disabled={busy}>
            {busy ? "Installing…" : "Install"}
          </button>
        ) : (
          <button className="install__btn" onClick={() => setShowIosHelp((v) => !v)}>
            {showIosHelp ? "Hide" : "How to"}
          </button>
        )}
      </div>

      {showIosHelp && (
        <ol className="install__steps">
          {ios ? (
            <>
              <li>
                Tap the <b>Share</b> button <span aria-hidden>⎋</span> in Safari's toolbar.
              </li>
              <li>
                Scroll down and tap <b>Add to Home Screen</b>.
              </li>
              <li>
                Tap <b>Add</b> — Forge will appear on your home screen like a native app.
              </li>
            </>
          ) : (
            <>
              <li>Open this site in Chrome (Android) or Safari (iPhone/iPad).</li>
              <li>
                Open the browser menu and choose <b>Install app</b> or{" "}
                <b>Add to Home Screen</b>.
              </li>
              <li>Confirm — Forge will open full-screen from your home screen.</li>
            </>
          )}
        </ol>
      )}
    </div>
  );
}
