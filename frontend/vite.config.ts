import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      'framer-motion': path.resolve(__dirname, 'node_modules/framer-motion/dist/es/index.mjs'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['app.orthoflowsolutions.com', 'localhost'],
  },
})
