import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Where the built assets will be requested from, which depends on who is
  // serving them:
  //   Vercel  — the bundle sits at the domain root, so base '/'. Vercel sets
  //             VERCEL=1 in the build environment; VITE_BASE overrides it by
  //             hand if you ever need to.
  //   Django  — collectstatic picks up frontend/dist and whitenoise serves it
  //             under /static/, so the asset URLs inside index.html must say
  //             /static/ or every one of them 404s.
  //   dev     — base '/', the app is browsed at http://localhost:5173/.
  base:
    process.env.VITE_BASE ||
    (process.env.VERCEL ? '/' : command === 'build' ? '/static/' : '/'),
  server: {
    // Same-origin API in dev: the sessionid/csrftoken cookies only work if
    // the browser talks to one origin, so proxy Django instead of calling
    // http://127.0.0.1:8000 directly. /media serves profile pictures.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
}))
