import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}", "./lib/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18202f",
        muted: "#667085",
        line: "#d7dde8",
        panel: "#f8fafc",
        accent: "#0f766e",
        signal: "#b45309",
      },
      fontFamily: {
        heading: ["var(--font-poppins)", "Arial", "Helvetica", "sans-serif"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(16, 24, 40, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
