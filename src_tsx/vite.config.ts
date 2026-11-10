// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// CARINA CCO Videowall Interface (Vite Configuration)
export default defineConfig({
  base: '/cco/',
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/cco/stream': 'http://localhost:2201',
      '/cco/topology': 'http://localhost:2201',
    },
  },
});
