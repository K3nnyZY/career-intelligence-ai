import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  base: command === 'build' ? '/static/' : '/',
  build: {
    outDir: fileURLToPath(new URL('../career_ai/static', import.meta.url)),
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    cors: false,
    allowedHosts: ['localhost', '127.0.0.1'],
    proxy: Object.fromEntries(
      ['/documents', '/profile', '/compare', '/analyze', '/health', '/openapi.json'].map(
        (path) => [path, { target: 'http://127.0.0.1:8000', changeOrigin: false }],
      ),
    ),
  },
}));
