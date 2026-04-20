/**
 * FILE: frontend/vite.config.js
 * =====================================
 * Vite Build Tool Configuration
 * =====================================
 *
 * Vite is a next-generation frontend build tool.
 * In development: serves files with native ES modules (no bundling = instant HMR).
 * In production:  bundles with Rollup (fast, tree-shaking, code splitting).
 *
 * WHY VITE OVER CREATE-REACT-APP?
 *   CRA uses Webpack — cold start takes 10-30s, HMR takes 1-5s per change.
 *   Vite uses native ES modules — cold start <1s, HMR <100ms per change.
 *
 * DEV SERVER PROXY:
 *   Without the proxy, the React dev server (localhost:5173) can't call the
 *   FastAPI server (localhost:8000) due to CORS restrictions.
 *   The proxy forwards /api/* requests to localhost:8000, bypassing CORS.
 *
 *   ws: true also proxies WebSocket connections — critical for our live feed.
 *
 *   In production, nginx or a load balancer handles this routing.
 *
 * INTERVIEW TALKING POINT:
 *   "I configured Vite's dev proxy so the frontend talks to the backend
 *   through the same origin during development. This mirrors the production
 *   setup where nginx routes /api to the backend and / to the React static files."
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react(),  // Enables JSX transform, Fast Refresh (HMR for React components)
  ],

  server: {
    port: 5173,
    host: "0.0.0.0",  // Listen on all interfaces (needed for Docker + LAN access)

    proxy: {
      // Forward all /api requests to the FastAPI backend
      "/api": {
        target:      "http://localhost:8000",
        changeOrigin: true,  // Rewrites the Host header to match the target
        ws:           true,   // Also proxy WebSocket connections (/api/accidents/ws)
      },
    },
  },

  build: {
    outDir:    "dist",       // Production output directory
    sourcemap: true,         // Generate source maps for debugging production errors
    rollupOptions: {
      output: {
        // Code splitting: separate vendor libs from app code
        // This improves caching — vendor code changes less often than app code
        manualChunks: {
          vendor:   ["react", "react-dom", "react-router-dom"],
          charts:   ["recharts"],
          utils:    ["axios", "date-fns"],
        },
      },
    },
  },
});
