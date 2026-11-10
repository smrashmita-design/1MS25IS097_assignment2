import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

const proxy = {
  // Optional dev proxy: set VITE_API_BASE_URL=/api to route through Vite.
  // NEXUS_API_PROXY lets you point the proxy at a different backend, e.g. the
  // deterministic UI test harness on port 8010.
  '/api': {
    target: process.env.NEXUS_API_PROXY || 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy,
  },
  preview: {
    port: 4173,
    strictPort: false,
    proxy,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          motion: ['framer-motion'],
          markdown: ['react-markdown', 'remark-gfm', 'rehype-highlight'],
          charts: ['recharts'],
        },
      },
    },
  },
})
