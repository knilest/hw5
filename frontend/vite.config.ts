import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The desk talks straight to the FastAPI backend at http://localhost:8000
// (see src/api.ts); the backend allows this page's origin via CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, open: true },
})
