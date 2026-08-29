import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/events/live': {
        target: 'ws://localhost:8000',
        ws: true
      },
      '/video/feed': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/video/privacy-feed': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
