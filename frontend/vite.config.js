import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = process.env.QUIZBLAST_DEV_BACKEND || "http://localhost:8001";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: backend,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: backend,
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
