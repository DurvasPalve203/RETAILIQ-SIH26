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
        retail: {
          dark: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          primary: '#0ea5e9',
          accent: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          subtle: '#64748b'
        }
      }
    },
  },
  plugins: [],
}
