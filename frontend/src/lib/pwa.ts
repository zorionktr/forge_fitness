import { useEffect, useState } from "react";

/* The `beforeinstallprompt` event isn't in the standard TS lib yet. */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((fn) => fn());

if (typeof window !== "undefined") {
  // Chrome/Android fire this when the app is installable; stash it so we can
  // trigger the native install prompt later from a user gesture (a button).
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    notify();
  });
}

/** True when the app is already running as an installed standalone app. */
export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS Safari exposes this non-standard flag instead of display-mode.
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

/** True for iOS/iPadOS, where installs are manual (Share → Add to Home Screen). */
export function isIos(): boolean {
  if (typeof window === "undefined") return false;
  const ua = window.navigator.userAgent;
  const iOS = /iPad|iPhone|iPod/.test(ua);
  // iPadOS 13+ reports as a Mac, but is a touch device.
  const iPadOS = /Macintosh/.test(ua) && "ontouchend" in document;
  return iOS || iPadOS;
}

export type InstallState = {
  /** A native install prompt is available (Android/Chrome/Edge/desktop). */
  canPrompt: boolean;
  /** App is already installed / running standalone. */
  installed: boolean;
  /** Trigger the native install dialog. Returns true if the user accepted. */
  promptInstall: () => Promise<boolean>;
};

/** React hook exposing PWA install availability and a trigger. */
export function useInstallPrompt(): InstallState {
  const [canPrompt, setCanPrompt] = useState(!!deferredPrompt);
  const [installed, setInstalled] = useState(isStandalone());

  useEffect(() => {
    const update = () => {
      setCanPrompt(!!deferredPrompt);
      setInstalled(isStandalone());
    };
    listeners.add(update);
    return () => {
      listeners.delete(update);
    };
  }, []);

  const promptInstall = async () => {
    if (!deferredPrompt) return false;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    notify();
    return outcome === "accepted";
  };

  return { canPrompt, installed, promptInstall };
}

/** Register the service worker. Call once on app start, in production builds. */
export function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* SW registration is best-effort; the app works fine without it. */
    });
  });
}
