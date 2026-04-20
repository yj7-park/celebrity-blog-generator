import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves from /celebrity-blog-generator/ in CI
  base: process.env.GITHUB_ACTIONS ? "/celebrity-blog-generator/" : "/",
  server: {
    host: true,
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
