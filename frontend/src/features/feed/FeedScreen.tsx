import { useQuery } from "@tanstack/react-query";
import { getFeed } from "@/api/social";
import { StoriesTray } from "@/features/stories/StoriesTray";
import { PostCard } from "./PostCard";

/** Social feed — stories tray + ranked "For You" timeline. Posting is via the top-bar "+". */
export function FeedScreen() {
  const { data: posts, isLoading } = useQuery({
    queryKey: ["feed"],
    queryFn: getFeed,
  });

  return (
    <div className="feed">
      <StoriesTray />

      {isLoading ? (
        <p className="feed__empty">Loading feed…</p>
      ) : !posts || posts.length === 0 ? (
        <div className="feed__welcome">
          <h2 className="feed__welcome-h">Your feed is empty</h2>
          <p className="feed__welcome-p">
            Follow people on <b>Discover</b>, or tap <b>+</b> to share a workout, a win, or a progress pic. 💪
          </p>
        </div>
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
