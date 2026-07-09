import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Same-origin API in dev: the sessionid/csrftoken cookies only work if
    // the browser talks to one origin, so proxy Django instead of calling
    // http://127.0.0.1:8000 directly. /media serves profile pictures.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
})
