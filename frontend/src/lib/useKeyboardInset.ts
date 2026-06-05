import { useEffect, useState } from "react";

/* Returns the height (px) currently hidden by the on-screen keyboard.
   Bottom-anchored sheets can add this as padding-bottom so their inputs stay
   visible above the keyboard instead of being covered by it.

   Uses the VisualViewport API (the only reliable signal on iOS Safari, which
   does not resize the layout viewport when the keyboard opens). */
export function useKeyboardInset(): number {
  const [inset, setInset] = useState(0);

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const update = () => {
      const hidden = window.innerHeight - vv.height - vv.offsetTop;
      setInset(Math.max(0, Math.round(hidden)));
    };
    update();
    vv.addEventListener("resize", update);
    vv.addEventListener("scroll", update);
    return () => {
      vv.removeEventListener("resize", update);
      vv.removeEventListener("scroll", update);
    };
  }, []);

  return inset;
}
