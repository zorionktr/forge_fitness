/* Forge service worker — enables installability (PWA) and basic offline support.
   Strategy:
   - Never touch the API or non-GET requests — those always go to the network.
   - Navigations: network-first, falling back to the cached app shell when offline.
   - Same-origin assets (JS/CSS/icons): stale-while-revalidate so the app loads
     instantly and quietly updates in the background. */

const CACHE = "forge-v1";
const SHELL = "/index.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll([SHELL, "/", "/manifest.webmanifest"])),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle same-origin GETs; let the API and everything else pass through.
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  // App navigations: try the network first so users get fresh HTML, fall back
  // to the cached shell when offline (SPA — the shell boots any route).
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(SHELL, copy));
          return res;
        })
        .catch(() => caches.match(SHELL).then((r) => r || caches.match("/"))),
    );
    return;
  }

  // Static assets: serve from cache immediately, refresh in the background.
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
