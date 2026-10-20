import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// The public 3-page app (index / login / events). Lives entirely outside the
// frozen src/ tree (fullstack.md 14.1) — it is a separate Vite root so the
// original app keeps building untouched alongside it.
export default defineConfig({
  root: __dirname,
  // The shared static assets (/data/*.json, /favicon.svg) live in the REPO-ROOT
  // public/ dir, not app/public/. Point Vite there so they are copied verbatim
  // into app/dist/ and served as real files (not swallowed by the SPA rewrite).
  publicDir: path.resolve(__dirname, "..", "public"),
  plugins: [react(), tailwindcss()],
  build: {
    outDir: path.resolve(__dirname, "dist"),
    emptyOutDir: true,
    sourcemap: false,
    minify: "esbuild",
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
});
