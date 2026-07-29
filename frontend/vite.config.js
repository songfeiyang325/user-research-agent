import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时：前端 5173，把 /api 代理到后端 8000（免 CORS，与生产同源一致）
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
