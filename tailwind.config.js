/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/adapters/web/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f5f7ff',
          100: '#ebedff',
          500: '#4f46e5',
          600: '#4338ca',
          700: '#3730a3',
        },
      },
    },
  },
  plugins: [],
};
