import { useEffect, useState } from "react";
import { createPost, getFeed, type Post } from "@/api/social";
import { PostCard } from "./PostCard";

/** Social feed — compose a post + scroll the timeline (docs/06). */
export function FeedScreen() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    getFeed()
      .then(setPosts)
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, []);

  const onPost = async () => {
    const body = draft.trim();
    if (!body || posting) return;
    setPosting(true);
    try {
      const created = await createPost(body);
      setPosts((p) => [created, ...p]); // prepend so it shows immediately
      setDraft("");
    } finally {
      setPosting(false);
    }
  };

  return (
    <div className="feed">
      <div className="composer">
        <textarea
          className="composer__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Share a workout, a win, or ask the community…"
          rows={3}
          maxLength={5000}
        />
        <div className="composer__row">
          <span className="composer__count">{draft.length}/5000</span>
          <button className="composer__post" onClick={onPost} disabled={posting || !draft.trim()}>
            {posting ? "Posting…" : "Post"}
          </button>
        </div>
      </div>

      {loading ? (
        <p className="feed__empty">Loading feed…</p>
      ) : posts.length === 0 ? (
        <p className="feed__empty">No posts yet — be the first to share something! 💪</p>
      ) : (
        <div className="feed__list">
          {posts.map((p) => (
            <PostCard key={p.id} post={p} />
          ))}
        </div>
      )}
    </div>
  );
}
