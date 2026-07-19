import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: "/Multi-Agent-AI-Data-Lakehouse-Platform-Betting-Site-Data-Intelligence/",
  server: {
    port: 3000,
    host: true
  }
});
