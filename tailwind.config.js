/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/*.html","./templates/includes/*.html"],
  theme: {
    screens: {
      sm: '480px',
      md: '768px',
      lg: '1020px',
      xl: '1440px',
    },
    extend: {},
  },
  plugins: [require("daisyui")],
}

