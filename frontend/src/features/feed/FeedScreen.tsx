import { useInfiniteQuery } from "@tanstack/react-query";
import { getFeed } from "@/api/social";
import { useInfiniteScroll } from "@/lib/useInfiniteScroll";
import { StoriesTray } from "@/features/stories/StoriesTray";
import { PostCard } from "./PostCard";

const PAGE_SIZE = 10;

/** Social feed — stories tray + ranked "For You" timeline, lazy-loaded as you scroll.
 *  Posting is via the top-bar "+". */
export function FeedScreen() {
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } = useInfiniteQuery({
    queryKey: ["feed"],
    queryFn: ({ pageParam }) => getFeed(PAGE_SIZE, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length < PAGE_SIZE ? undefined : allPages.length * PAGE_SIZE,
  });

  const sentinelRef = useInfiniteScroll(fetchNextPage, !!hasNextPage && !isFetchingNextPage);

  const posts = data?.pages.flat() ?? [];

  return (
    <div className="feed">
      <StoriesTray />

      {isLoading ? (
        <p className="feed__empty">Loading feed…</p>
      ) : posts.length === 0 ? (
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
          <div ref={sentinelRef} className="feed__sentinel" aria-hidden="true" />
          {isFetchingNextPage && <p className="feed__empty">Loading more…</p>}
        </div>
      )}
    </div>
  );
}
