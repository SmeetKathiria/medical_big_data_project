import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Playfair Display"', '"Instrument Serif"', 'Georgia', 'serif'],
        mono: ['Inter', '"SFMono-Regular"', 'Consolas', 'monospace']
      },
      colors: {
        ink: "#1C322D",
        muted: "#667A76",
        line: "#D6DFDB",
        panel: "#F8F3EE",
        surface: "#FFFFFF",
        sage: "#A2C2B3",
        green: "#1C322D",
        mint: "#EAF3EE",
        amber: "#EBB552",
        clay: "#F1CDBE",
        coal: "#10251F",
        night: "#1C322D"
      }
    }
  },
  plugins: []
};
export default config;
