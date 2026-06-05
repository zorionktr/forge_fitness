import { useState } from "react";
import { addComment, getComments, toggleLike, type Comment, type Post } from "@/api/social";
import { timeAgo } from "@/lib/time";
import { mediaUrl } from "@/lib/media";

function initials(p: Post): string {
  const name = p.author.display_name || p.author.username;
  return name.slice(0, 2).toUpperCase();
}

export function PostCard({ post }: { post: Post }) {
  const [liked, setLiked] = useState(post.liked_by_me);
  const [likeCount, setLikeCount] = useState(post.like_count);
  const [commentCount, setCommentCount] = useState(post.comment_count);
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const onLike = async () => {
    // Optimistic toggle, reconcile with the server count.
    setLiked((v) => !v);
    setLikeCount((c) => c + (liked ? -1 : 1));
    try {
      const res = await toggleLike(post.id);
      setLiked(res.liked);
      setLikeCount(res.like_count);
    } catch {
      setLiked(post.liked_by_me); // revert on failure
    }
  };

  const onToggleComments = async () => {
    const next = !open;
    setOpen(next);
    if (next && comments === null) {
      try {
        setComments(await getComments(post.id));
      } catch {
        setComments([]);
      }
    }
  };

  const onComment = async () => {
    const body = draft.trim();
    if (!body || busy) return;
    setBusy(true);
    try {
      const c = await addComment(post.id, body);
      setComments((cs) => [...(cs ?? []), c]);
      setCommentCount((n) => n + 1);
      setDraft("");
    } finally {
      setBusy(false);
    }
  };

  const isPr = post.kind === "pr";

  return (
    <article className={`post ${isPr ? "post--pr" : ""}`}>
      <header className="post__head">
        <div className="post__avatar">{initials(post)}</div>
        <div className="post__who">
          <span className="post__name">{post.author.display_name || post.author.username}</span>
          <span className="post__meta">@{post.author.username} · {timeAgo(post.created_at)}</span>
        </div>
        {isPr ? (
          <span className="post__prbadge">🏆 PR</span>
        ) : (
          post.reason && <span className="post__reason">{post.reason}</span>
        )}
      </header>

      {post.body && <p className={`post__body ${isPr ? "post__body--pr" : ""}`}>{post.body}</p>}

      {post.media.length > 0 && (
        <div className={`post__media post__media--n${Math.min(post.media.length, 4)}`}>
          {post.media.slice(0, 4).map((m, i) => (
            <div className="post__media-cell" key={m.url}>
              <img src={mediaUrl(m.url)} alt="" loading="lazy" />
              {i === 3 && post.media.length > 4 && (
                <span className="post__media-more">+{post.media.length - 4}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {post.tags.length > 0 && (
        <div className="post__tags">
          {post.tags.map((t) => (
            <span className="post__tag" key={t}>#{t}</span>
          ))}
        </div>
      )}

      <footer className="post__actions">
        <button className={`post__action ${liked ? "post__action--on" : ""}`} onClick={onLike}>
          {liked ? "♥" : "♡"} {likeCount}
        </button>
        <button className="post__action" onClick={onToggleComments}>
          💬 {commentCount}
        </button>
      </footer>

      {open && (
        <div className="post__comments">
          {comments === null && <p className="post__hint">Loading…</p>}
          {comments?.map((c) => (
            <div key={c.id} className="comment">
              <span className="comment__name">{c.author.display_name || c.author.username}</span>
              <span className="comment__body">{c.body}</span>
            </div>
          ))}
          <div className="comment__compose">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onComment()}
              placeholder="Add a comment…"
            />
            <button onClick={onComment} disabled={busy || !draft.trim()}>
              Post
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
