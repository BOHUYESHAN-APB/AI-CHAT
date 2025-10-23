import { defineConfig } from 'vite'

// Vite dev server proxy to forward API requests to Flask backend running on localhost:8080
export default defineConfig({
  server: {
    proxy: {
      '/config': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      },
      '/rooms': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      }
    }
  }
})