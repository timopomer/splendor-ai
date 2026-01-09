/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Gem colors
        diamond: '#e8e8e8',
        sapphire: '#3b82f6',
        emerald: '#22c55e',
        ruby: '#ef4444',
        onyx: '#1f2937',
        gold: '#fbbf24',
        // UI colors
        board: '#1e3a2f',
        panel: '#2d4a3e',
        highlight: '#4ade80',
      },
      fontFamily: {
        display: ['Cinzel', 'serif'],
        body: ['Outfit', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-subtle': 'bounce 1s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

