// vite.config.js — SETTINGS FOR VITE (the tool that runs and builds the frontend).

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // Turn on React support and Tailwind CSS.
  plugins: [react(), tailwindcss()],
  server: {
    // While developing, any request starting with /api is forwarded to the
    // FastAPI backend on port 8000. So the frontend just calls "/api/..."
    proxy: { "/api": "http://localhost:8000" },
  },
});
