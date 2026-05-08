// vite.config.ts — Vite build config.
// `base` + `outDir` make the bundle land in university_crm/static/dist/
// so Odoo can serve it. Dev `proxy` forwards Odoo paths to localhost:8069.
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

export default defineConfig({
  plugins: [vue()],
  base: "/university_crm/static/dist/",
  build: {
    outDir: "../../static/dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/web": { target: "http://127.0.0.1:8069", changeOrigin: true, secure: false },
      "/student": { target: "http://127.0.0.1:8069", changeOrigin: true, secure: false },
      "/api": { target: "http://127.0.0.1:8069", changeOrigin: true, secure: false },
    },
  },
})
