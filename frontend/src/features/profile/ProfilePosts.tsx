import { useInfiniteQuery } from "@tanstack/react-query";
import { getUserPosts } from "@/api/social";
import { useInfiniteScroll } from "@/lib/useInfiniteScroll";
import { PostCard } from "@/features/feed/PostCard";

const PAGE_SIZE = 10;

/** A user's own posts, newest first, lazy-loaded as you scroll. Shared by the editable
 *  profile and the public "stalk" profile. */
export function ProfilePosts({ userId, emptyText }: { userId: string; emptyText: string }) {
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } = useInfiniteQuery({
    queryKey: ["userPosts", userId],
    queryFn: ({ pageParam }) => getUserPosts(userId, PAGE_SIZE, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length < PAGE_SIZE ? undefined : allPages.length * PAGE_SIZE,
    enabled: !!userId,
  });

  const sentinelRef = useInfiniteScroll(fetchNextPage, !!hasNextPage && !isFetchingNextPage);
  const posts = data?.pages.flat() ?? [];

  if (isLoading) return <p className="profile-posts__empty">Loading posts…</p>;
  if (posts.length === 0) return <p className="profile-posts__empty">{emptyText}</p>;

  return (
    <div className="profile-posts__list">
      {posts.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
      <div ref={sentinelRef} className="feed__sentinel" aria-hidden="true" />
      {isFetchingNextPage && <p className="profile-posts__empty">Loading more…</p>}
    </div>
  );
}
