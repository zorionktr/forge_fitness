import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getStories, type StoryTray } from "@/api/social";
import { getProfile } from "@/api/profile";
import { Avatar } from "@/features/social/Avatar";
import { StoryViewer } from "./StoryViewer";
import { AddStory } from "./AddStory";

const SEEN_KEY = "forge.seenStories";

function loadSeen(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

/** Instagram-style stories tray at the top of the feed. First chip = "Your story" (add). */
export function StoriesTray() {
  const me = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const { data: trays } = useQuery({ queryKey: ["stories"], queryFn: getStories });

  const [viewerStart, setViewerStart] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [seen, setSeen] = useState<Set<string>>(loadSeen);

  const markSeen = (id: string) =>
    setSeen((prev) => {
      if (prev.has(id)) return prev;
      const nextSet = new Set(prev);
      nextSet.add(id);
      try {
        localStorage.setItem(SEEN_KEY, JSON.stringify([...nextSet]));
      } catch {
        /* ignore */
      }
      return nextSet;
    });

  if (!me.data) return null;

  const all: StoryTray[] = trays ?? [];
  const myId = me.data.id;
  const myTray = all.find((t) => t.author.id === myId);
  const others = all.filter((t) => t.author.id !== myId);
  // The viewer navigates this ordered list (mine first, if any).
  const ordered = myTray ? [myTray, ...others] : others;

  const traySeen = (t: StoryTray) => t.items.every((it) => seen.has(it.id));

  return (
    <div className="tray">
      {/* Your story */}
      <div className="tray__item">
        <span
          className="tray__avatar"
          role="button"
          tabIndex={0}
          onClick={() => (myTray ? setViewerStart(0) : setAdding(true))}
        >
          <Avatar user={me.data} size={62} ring={myTray ? (traySeen(myTray) ? "seen" : "unseen") : "add"} />
          <button
            className="tray__add"
            onClick={(e) => {
              e.stopPropagation();
              setAdding(true);
            }}
            aria-label="Add to your story"
          >
            +
          </button>
        </span>
        <span className="tray__name">Your story</span>
      </div>

      {others.map((t) => {
        const idx = ordered.indexOf(t);
        return (
          <button key={t.author.id} className="tray__item" onClick={() => setViewerStart(idx)}>
            <Avatar user={t.author} size={62} ring={traySeen(t) ? "seen" : "unseen"} />
            <span className="tray__name">{t.author.username}</span>
          </button>
        );
      })}

      {viewerStart !== null && ordered.length > 0 && (
        <StoryViewer trays={ordered} start={viewerStart} onClose={() => setViewerStart(null)} onSeen={markSeen} />
      )}
      {adding && <AddStory onClose={() => setAdding(false)} />}
    </div>
  );
}
