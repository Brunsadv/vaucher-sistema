/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'vaucher-red': {
          DEFAULT: '#8B1538',
          dark: '#6B1028',
          light: '#B91C3C',
        },
      },
    },
  },
  plugins: [],
}
