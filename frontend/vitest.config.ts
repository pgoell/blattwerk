import { defineConfig } from "vitest/config";

// The model's tests run in node, with no browser. Vitest reads this file in place of vite.config.ts, so the build
// knows nothing of them.
//
// A property runs a few hundred cases: under 1 s alone, but beside a CI shard's browsers, or 8 runs side by side,
// one of them took 6 s and vitest's 5 s a test failed it (#569). The time a test takes says nothing of whether the
// model holds, so each gets a minute; a hang still ends at tests/test_model.py's three minutes for the whole run.
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
    setupFiles: ["./vitest.setup.ts"],
    testTimeout: 60_000,
  },
});
