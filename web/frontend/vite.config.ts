import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the Flask backend (default port 5015).
// In production, `npm run build` outputs to `dist/`, which Flask serves.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5015",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
