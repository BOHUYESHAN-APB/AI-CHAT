import { defineConfig } from 'vite'

// Vite dev server proxy to forward API requests to Flask backend running on 127.0.0.1:8080
export default defineConfig({
  server: {
    proxy: {
      '/rooms': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false
      },
      '/config': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false
      },
      // catch-all for other API-like paths if you later use /api/...
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})