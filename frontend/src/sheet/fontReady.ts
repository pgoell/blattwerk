// A canvas read while a font is still loading measures the fallback, and a Lineatur keeps that
// descent (#504). When the real fonts are in, drop the read and draw again.

import { useEffect, useLayoutEffect, useState } from "react";
import { forgetMetrics } from "./look";

export function useRealFonts() {
  const [, again] = useState(0);
  // From this render, not from a later status: the lift in the DOM was computed with it.
  const ready = typeof document !== "undefined" && document.fonts.status === "loaded";
  useLayoutEffect(() => {
    if (ready) document.documentElement.dataset.baselines = "1";
  });
  useEffect(() => {
    let gone = false;
    const draw = () => {
      if (gone || document.fonts.status !== "loaded") return;
      forgetMetrics();
      again((n) => n + 1);
    };
    document.fonts.addEventListener("loadingdone", draw);
    void document.fonts.ready.then(draw);
    return () => {
      gone = true;
      document.fonts.removeEventListener("loadingdone", draw);
    };
  }, []);
}
