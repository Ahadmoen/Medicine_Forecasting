/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eef9f6",
          100: "#d6f1e9",
          500: "#0e9f6e",
          600: "#0b8a5e",
          700: "#076c49",
          900: "#022c1e",
        },
        ink: {
          50:  "#f7f8fa",
          100: "#eceef2",
          200: "#d4d8e0",
          400: "#7e8493",
          600: "#3f4452",
          800: "#1d2230",
          900: "#0d111c",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
