/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cockpit: {
          dark: '#0b0f19',
          panel: '#111827',
          border: '#1f293d',
          accent: '#06b6d4',
          bull: '#10b981',
          bear: '#ef4444',
          warn: '#f59e0b',
          muted: '#64748b'
        }
      }
    },
  },
  plugins: [],
}

