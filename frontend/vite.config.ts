import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Developpement : /api et /media passent par Vite (qui les relaie vers Django). Le navigateur ne parle qu'au port
  // 5173, donc l'application marche depuis n'importe quelle adresse (localhost, reseau local, Tailscale, telephone)
  // sans reglage CORS ni hotes autorises cote backend. Le backend doit tourner sur le port 8000.
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
