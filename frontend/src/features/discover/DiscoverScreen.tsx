import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSuggestedUsers, searchUsers } from "@/api/social";
import { UserRow } from "@/features/social/UserRow";

/** Discover people: search by username + a "Suggested for you" list to follow. */
export function DiscoverScreen() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");

  // Debounce the query so we don't hit the API on every keystroke.
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(q.trim()), 280);
    return () => window.clearTimeout(id);
  }, [q]);

  const results = useQuery({
    queryKey: ["userSearch", debounced],
    queryFn: () => searchUsers(debounced),
    enabled: debounced.length > 0,
  });

  const suggested = useQuery({
    queryKey: ["suggestedUsers"],
    queryFn: getSuggestedUsers,
  });

  const searching = debounced.length > 0;

  return (
    <div className="discover">
      <div className="discover__search">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-4-4" />
        </svg>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search people by name or @username"
          autoFocus
        />
        {q && (
          <button className="discover__clear" onClick={() => setQ("")} aria-label="Clear">
            ✕
          </button>
        )}
      </div>

      {searching ? (
        <section className="discover__section">
          {results.isLoading && <p className="discover__hint">Searching…</p>}
          {results.data && results.data.length === 0 && (
            <p className="discover__hint">No one matches “{debounced}”.</p>
          )}
          {results.data?.map((u) => (
            <UserRow key={u.id} user={u} />
          ))}
        </section>
      ) : (
        <section className="discover__section">
          <h2 className="discover__title">Suggested for you</h2>
          {suggested.isLoading && <p className="discover__hint">Loading…</p>}
          {suggested.data && suggested.data.length === 0 && (
            <p className="discover__hint">No suggestions yet — check back as the community grows.</p>
          )}
          {suggested.data?.map((u) => (
            <UserRow key={u.id} user={u} />
          ))}
        </section>
      )}
    </div>
  );
}
