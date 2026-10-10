import fc from "fast-check";

// CI draws the same cases every time: a red run there is the code's doing, not the dice's. Elsewhere each run
// draws new ones. A property that fails prints its seed either way.
fc.configureGlobal({ numRuns: 1000, ...(process.env.CI && { seed: 219 }) });
