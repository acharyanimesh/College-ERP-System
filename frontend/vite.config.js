import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Production builds are served by Django: collectstatic picks up
  // frontend/dist, so the hashed assets live under /static/. The dev server
  // keeps base '/' (the app is browsed at http://localhost:5173/).
  base: command === 'build' ? '/static/' : '/',
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
