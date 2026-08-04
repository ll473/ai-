import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '::',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8001',
      '/uploads': 'http://127.0.0.1:8001',
    },
  },
})
