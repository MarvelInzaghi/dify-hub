import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The admin SPA talks to the FastAPI backend. In dev, proxy `/api` to the backend
// (default http://localhost:8000). In prod, serve behind a reverse proxy that routes
// `/api` to the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
