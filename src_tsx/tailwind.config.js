// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src_cco/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#F7F7F7',
        surface: '#263238',
        'surface-border': '#37474F',
      },
    },
  },
  plugins: [],
}
