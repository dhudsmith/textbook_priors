import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The site is served from https://dhudsmith.github.io/textbook_priors/ (talk/PLAN.md section 6),
// so every asset path is written under that base. `public/` is the committed data snapshot the
// `talk_data` rule writes; Vite copies it to dist/ verbatim.
export default defineConfig({
  plugins: [react()],
  base: "/textbook_priors/",
  build: { outDir: "dist", assetsDir: "assets", chunkSizeWarningLimit: 700 },
});
