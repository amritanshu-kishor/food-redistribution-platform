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
          ivory: '#FAF9F6',      // Warm natural ivory white
          charcoal: '#1C1C1C',   // Deep solid charcoal
          stone: {
            DEFAULT: '#F5F5F4',  // Warm light grey
            dark: '#E7E5E4',     // Border grey
            light: '#FBFBFA',
          },
          green: {
            DEFAULT: '#2D5A27',  // Primary brand green
            light: '#E2E8DD',    // Background soft green
            dark: '#1B3B18',
          },
          sage: '#A3B18A',       // Accent sage
          amber: '#D97706',      // Restrained warning amber
          red: '#DC2626',        // Restrained error red
          blue: '#2563EB',       // Restrained link/info blue
        }
      },
      fontFamily: {
        serif: ['Georgia', 'serif'],
        sans: ['Inter', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
