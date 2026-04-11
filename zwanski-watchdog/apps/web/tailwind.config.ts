import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        watchdog: {
          bg: "#050608",
          card: "#0f1419",
          accent: "#22d3ee",
          warn: "#f97316",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
