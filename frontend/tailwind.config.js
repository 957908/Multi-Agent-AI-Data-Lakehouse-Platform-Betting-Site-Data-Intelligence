/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          DEFAULT: '#0B0D19',
          card: '#16192B',
          border: 'rgba(255, 255, 255, 0.08)',
          input: '#22253F'
        },
        cyan: {
          accent: '#00F5D4'
        },
        purple: {
          accent: '#7B2CBF'
        }
      },
      fontFamily: {
        outfit: ['Outfit', 'sans-serif'],
        jakarta: ['Plus Jakarta Sans', 'sans-serif']
      }
    },
  },
  plugins: [],
}
