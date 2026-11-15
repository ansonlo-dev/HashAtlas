import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the built site works from any static path.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 1500 },
});
