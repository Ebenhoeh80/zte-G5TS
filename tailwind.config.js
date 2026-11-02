/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
        },
        ha: {
          blue: '#03a9f4',
          dark: '#10172a',
          card: '#1e293b',
          border: '#334155'
        }
      }
    },
  },
  plugins: [],
}
