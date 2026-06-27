import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/video_feed": "http://localhost:8000",
      "/incidents": "http://localhost:8000",
      "/domain": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/debug": "http://localhost:8000",
      "/stream": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
});
