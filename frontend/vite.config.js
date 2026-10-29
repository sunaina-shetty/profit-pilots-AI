import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Calls to /api/* are forwarded to the Flask backend on port 5000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:5000" },
  },
});
