import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/generate_graphs': 'http://localhost:8080',
      '/static': 'http://localhost:8080',
      '/api/analysis': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/analysis/, '/analysis'),
      },
    }
  }
});
