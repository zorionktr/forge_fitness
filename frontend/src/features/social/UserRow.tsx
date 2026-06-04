import { useState } from "react";
import { followUser, unfollowUser, type UserCard } from "@/api/social";
import { Avatar } from "./Avatar";

/** A user row with an optimistic Follow / Following toggle. Used in Discover. */
export function UserRow({ user }: { user: UserCard }) {
  const [following, setFollowing] = useState(user.is_following);
  const [count, setCount] = useState(user.follower_count);
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    if (busy) return;
    setBusy(true);
    const next = !following;
    setFollowing(next);
    setCount((c) => Math.max(0, c + (next ? 1 : -1)));
    try {
      const res = next ? await followUser(user.id) : await unfollowUser(user.id);
      setFollowing(res.following);
      setCount(res.follower_count);
    } catch {
      setFollowing(!next); // revert
      setCount((c) => Math.max(0, c + (next ? -1 : 1)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="urow">
      <Avatar user={user} size={46} />
      <div className="urow__meta">
        <span className="urow__name">{user.display_name || user.username}</span>
        <span className="urow__sub">
          @{user.username} · {count} follower{count === 1 ? "" : "s"}
        </span>
      </div>
      <button
        className={`urow__btn ${following ? "urow__btn--on" : ""}`}
        onClick={toggle}
        disabled={busy}
      >
        {following ? "Following" : "Follow"}
      </button>
    </div>
  );
}
