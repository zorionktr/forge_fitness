import { useCallback, useEffect, useRef, useState } from "react";
import { addStoryComment, likeStory, type StoryTray } from "@/api/social";
import { timeAgo } from "@/lib/time";
import { Avatar } from "@/features/social/Avatar";

const ITEM_MS = 5000;

/** Full-screen story viewer with progress bars, auto-advance, like + reply. */
export function StoryViewer({
  trays,
  start,
  onClose,
  onSeen,
}: {
  trays: StoryTray[];
  start: number;
  onClose: () => void;
  onSeen: (id: string) => void;
}) {
  const [ti, setTi] = useState(start);
  const [ii, setIi] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reply, setReply] = useState("");
  const [liked, setLiked] = useState(false);
  const [sentReply, setSentReply] = useState(false);

  const tray = trays[ti];
  const item = tray?.items[ii];

  const next = useCallback(() => {
    setReply("");
    setSentReply(false);
    setIi((curII) => {
      const items = trays[ti]?.items ?? [];
      if (curII < items.length - 1) return curII + 1;
      // move to next tray
      if (ti < trays.length - 1) {
        setTi(ti + 1);
        return 0;
      }
      onClose();
      return curII;
    });
  }, [ti, trays, onClose]);

  const prev = () => {
    setReply("");
    if (ii > 0) setIi(ii - 1);
    else if (ti > 0) {
      const pti = ti - 1;
      setTi(pti);
      setIi((trays[pti]?.items.length ?? 1) - 1);
    }
  };

  // Sync liked state + mark seen whenever the visible item changes.
  useEffect(() => {
    if (!item) return;
    setLiked(item.liked_by_me);
    onSeen(item.id);
  }, [item, onSeen]);

  // Auto-advance timer (paused while replying).
  useEffect(() => {
    if (paused || !item) return;
    const id = window.setTimeout(next, ITEM_MS);
    return () => window.clearTimeout(id);
  }, [ti, ii, paused, item, next]);

  // Keyboard: Esc closes, arrows navigate.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [next]);

  const likedRef = useRef(false);
  likedRef.current = liked;
  const onLike = async () => {
    setLiked((v) => !v);
    try {
      const res = await likeStory(item.id);
      setLiked(res.liked);
    } catch {
      setLiked(likedRef.current);
    }
  };

  const onReply = async () => {
    const body = reply.trim();
    if (!body) return;
    setReply("");
    setSentReply(true);
    try {
      await addStoryComment(item.id, body);
    } catch {
      setSentReply(false);
    }
  };

  if (!tray || !item) return null;
  const media = item.media[0];

  return (
    <div className="sv">
      <div className="sv__progress">
        {tray.items.map((it, idx) => (
          <span className="sv__bar" key={it.id}>
            <span
              className="sv__bar-fill"
              style={{
                width: idx < ii ? "100%" : idx > ii ? "0%" : undefined,
                animation: idx === ii && !paused ? `storyProg ${ITEM_MS}ms linear forwards` : "none",
              }}
              // restart the animation when the active item changes
              key={`${ti}-${ii}-${idx}`}
            />
          </span>
        ))}
      </div>

      <header className="sv__head">
        <Avatar user={tray.author} size={34} />
        <span className="sv__who">{tray.author.display_name || tray.author.username}</span>
        <span className="sv__time">{timeAgo(item.created_at)}</span>
        <button className="sv__close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>

      {/* tap zones */}
      <button className="sv__zone sv__zone--prev" onClick={prev} aria-label="Previous" />
      <button className="sv__zone sv__zone--next" onClick={next} aria-label="Next" />

      <div className="sv__stage">
        {media ? <img className="sv__img" src={media.url} alt="" /> : <div className="sv__img sv__img--empty" />}
        {item.caption && <p className="sv__caption">{item.caption}</p>}
      </div>

      <footer className="sv__foot" onClick={(e) => e.stopPropagation()}>
        <input
          className="sv__reply"
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          onFocus={() => setPaused(true)}
          onBlur={() => setPaused(false)}
          onKeyDown={(e) => e.key === "Enter" && onReply()}
          placeholder={sentReply ? "Sent ✓" : `Reply to ${tray.author.username}…`}
        />
        <button className={`sv__like ${liked ? "sv__like--on" : ""}`} onClick={onLike} aria-label="Like">
          {liked ? "♥" : "♡"}
        </button>
      </footer>
    </div>
  );
}
