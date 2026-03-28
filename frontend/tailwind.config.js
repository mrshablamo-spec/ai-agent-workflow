/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nexus: {
          bg: "#0a0e1a",
          panel: "#0f1629",
          border: "#1e2d4a",
          accent: "#1a6aff",
          accent2: "#00d4ff",
          text: "#c8d6f0",
          muted: "#4a5a7a",
          up: "#00e676",
          down: "#ff1744",
          neutral: "#ffab00",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
