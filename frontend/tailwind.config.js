/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        larteh: {
          50: '#fbf7ee',
          100: '#f5ecda',
          200: '#edd9b5',
          300: '#e3be87',
          400: '#d79f58',
          500: '#c67e2a', // Rich heritage gold/ochre
          600: '#ad5f21',
          700: '#89431e',
          800: '#71361e',
          900: '#5e2e1d',
        },
        forest: {
          50: '#f0f9f4',
          100: '#dbf0e4',
          500: '#1b8a5a', // Akuapem lush forest green
          700: '#135c3e',
          800: '#114a33',
          900: '#0e3e2c',
        },
      },
      animation: {
        'pulse-fast': 'pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ripple': 'ripple 1.5s ease-out infinite',
      },
      keyframes: {
        ripple: {
          '0%': { transform: 'scale(0.95)', opacity: '1' },
          '100%': { transform: 'scale(1.4)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};

