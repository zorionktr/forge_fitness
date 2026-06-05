/**
 * Resolve a stored media URL to one the browser can actually reach.
 *
 * Uploads are stored with the backend's S3/MinIO endpoint baked into the URL
 * (e.g. `http://localhost:9000/...`). That host is the *server's* loopback, so on any
 * non-local deployment the browser can't load it. We rewrite loopback hosts to whatever
 * host is serving the app (MinIO is published on the same machine, port 9000), which fixes
 * both already-stored and newly-uploaded media without a DB migration.
 */
const LOOPBACK = new Set(["localhost", "127.0.0.1", "0.0.0.0"]);

export function mediaUrl(url: string | null | undefined): string {
  if (!url) return "";
  try {
    const u = new URL(url, window.location.origin);
    if (LOOPBACK.has(u.hostname)) u.hostname = window.location.hostname;
    return u.toString();
  } catch {
    return url;
  }
}
