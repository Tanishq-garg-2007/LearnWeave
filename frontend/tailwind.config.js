/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        surface: {
          DEFAULT: "rgb(var(--surface) / <alpha-value>)",
          border: "rgb(var(--surface-border) / <alpha-value>)",
        },
        ink: "rgb(var(--ink) / <alpha-value>)",
        text: {
          DEFAULT: "rgb(var(--text) / <alpha-value>)",
          muted: "rgb(var(--text-muted) / <alpha-value>)",
        },
        muted: "rgb(var(--text-muted) / <alpha-value>)",
        primary: {
          DEFAULT: "rgb(var(--primary) / <alpha-value>)",
          foreground: "rgb(var(--primary-foreground) / <alpha-value>)",
        },
        accent: {
          from: "rgb(var(--accent-from) / <alpha-value>)",
          to: "rgb(var(--accent-to) / <alpha-value>)",
        },
        focus: "rgb(var(--focus-ring) / <alpha-value>)",
        success: "rgb(var(--success) / <alpha-value>)",
        warning: "rgb(var(--warning) / <alpha-value>)",
        danger: "rgb(var(--danger) / <alpha-value>)",
        info: "rgb(var(--info) / <alpha-value>)",
        cream: "rgb(var(--cream) / <alpha-value>)",
        sky: "rgb(var(--sky) / <alpha-value>)",
        blush: "rgb(var(--blush) / <alpha-value>)",
        lavender: "rgb(var(--lavender) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "system-ui", "-apple-system", "sans-serif"],
        display: ["'Instrument Serif'", "Georgia", "serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        soft: "0 8px 30px -4px rgba(37, 34, 41, 0.06), 0 4px 12px -2px rgba(37, 34, 41, 0.04)",
        glass: "0 16px 40px -12px rgba(37, 34, 41, 0.08), 0 4px 12px -2px rgba(37, 34, 41, 0.03)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        "float-delayed": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(6px)" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "float-delayed": "float-delayed 7s ease-in-out infinite 1s",
      },
    },
  },
  plugins: [],
};
