import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  // FastAPI serves the build from the package.
  build: { outDir: "../src/blattwerk/static", emptyOutDir: true },
  server: { proxy: { "/api": backend, "/impressum": backend, "/datenschutz": backend } },
});
