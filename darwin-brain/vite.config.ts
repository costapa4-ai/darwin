import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3051,
    allowedHosts: ['myserver.local'],
    watch: {
      usePolling: true
    }
  }
})
