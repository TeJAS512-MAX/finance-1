import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", '"Segoe UI"', "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "Roboto Mono", "monospace"],
      },
      colors: {
        darkbg: "#020617",
        darkerbg: "#080b12",
        panel: "#0f172a",
        panelcard: "#111726",
        panelborder: "#1e293b",
        brand: {
          50: "#ecfdf5",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          900: "#064e3b",
        },
        accentcyan: "#22d3ee",
        accentpurple: "#8b5cf6",
        warningamber: "#f59e0b",
        dangerrose: "#f43f5e",
      },
      animation: {
        "pulse-glow": "pulseGlow 2.5s infinite ease-in-out",
        "float-slow": "floatSlow 4s infinite ease-in-out",
        "spin-slow": "spin 25s linear infinite",
        "wormhole-spin": "spin 8s linear infinite",
        "mesh-pulse": "meshPulse 6s infinite ease-in-out",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "0.8", transform: "scale(1)" },
          "50%": { opacity: "0.4", transform: "scale(1.04)" },
        },
        floatSlow: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        meshPulse: {
          "0%, 100%": { transform: "scale(1) rotate(0deg)", opacity: "0.4" },
          "50%": { transform: "scale(1.15) rotate(10deg)", opacity: "0.7" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
