import { defineConfig } from "vitest/config";

// The model's tests run in node, with no browser. Vitest reads this file in place of vite.config.ts, so the build
// knows nothing of them.
export default defineConfig({
  test: { include: ["src/**/*.test.ts"], environment: "node", setupFiles: ["./vitest.setup.ts"] },
});
