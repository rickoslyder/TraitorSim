/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom gray shades
        gray: {
          750: '#2d3748',
        },
        // Traitor theme colors
        traitor: {
          red: '#dc2626',
          dark: '#991b1b',
        },
        faithful: {
          blue: '#2563eb',
          dark: '#1d4ed8',
        },
        // Archetype colors
        archetype: {
          prodigy: '#8b5cf6',
          sociopath: '#ec4899',
          survivor: '#6b7280',
          psychic: '#f59e0b',
          bitter: '#dc2626',
          infatuated: '#f472b6',
          outsider: '#22c55e',
          authority: '#78716c',
          zealot: '#a855f7',
          romantic: '#fb7185',
          smug: '#fbbf24',
          operator: '#14b8a6',
          leader: '#3b82f6',
        },
        // Trust scale
        trust: {
          high: '#22c55e',
          neutral: '#eab308',
          low: '#ef4444',
        },
      },
    },
  },
  plugins: [],
}
