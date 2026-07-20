import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  root: fileURLToPath(new URL('./public-site', import.meta.url)),
  publicDir: fileURLToPath(new URL('./public', import.meta.url)),
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 4177,
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 4177,
    strictPort: true,
  },
  build: {
    outDir: fileURLToPath(new URL('./dist-public', import.meta.url)),
    emptyOutDir: true,
  },
})
