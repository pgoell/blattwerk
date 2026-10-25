// A canvas read while a font is still loading measures the fallback (#504). Draw again when the
// real fonts are in. A face already measured keeps its lift if another font starts loading.

import { useEffect, useLayoutEffect, useState } from "react";

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
