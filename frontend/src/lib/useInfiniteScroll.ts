import { useCallback, useRef } from "react";

/**
 * Lazy-loading sentinel. Returns a ref to attach to an element at the end of a list;
 * when it scrolls into view (and `enabled`), `onLoadMore` fires to fetch the next page.
 * React calls the ref callback with `null` on unmount, which disconnects the observer.
 */
export function useInfiniteScroll(
  onLoadMore: () => void,
  enabled: boolean,
): (node: Element | null) => void {
  const observer = useRef<IntersectionObserver | null>(null);
  const cb = useRef(onLoadMore);
  cb.current = onLoadMore;

  return useCallback(
    (node: Element | null) => {
      observer.current?.disconnect();
      if (!node || !enabled) return;
      observer.current = new IntersectionObserver(
        (entries) => entries[0]?.isIntersecting && cb.current(),
        { rootMargin: "200px" }, // start loading a little before the sentinel is visible
      );
      observer.current.observe(node);
    },
    [enabled],
  );
}
