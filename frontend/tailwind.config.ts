import type { Config } from "tailwindcss";

// Theme from the "Real Estate Landing Page" Figma design: sky blue + dark ink, Gilroy-like geometric type.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef5fc", 100: "#d9e8f7", 200: "#b9d4ef", 300: "#80b2df", 400: "#5b97d3", 500: "#3d7fc6",
          600: "#2f6aac", 700: "#275a92", 800: "#214a77", 900: "#1d3f63",
        },
        ink: { 900: "#050810", 800: "#1a1d22", 700: "#35393e", 500: "#737579", 400: "#adadad" },
        sky: { hero: "#80b2df" },
      },
      backgroundImage: {
        "ink-gradient": "linear-gradient(180deg, #35393e 0%, #31353a 6.25%, #050810 74.4%)",
        "sky-fade": "linear-gradient(180deg, #80b2df 0%, rgba(128,178,223,0) 100%)",
      },
      fontFamily: {
        sans: ["Urbanist", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      },
      borderRadius: { design: "10px" },
      boxShadow: {
        card: "0 1px 2px rgba(10,13,17,.05), 0 4px 16px rgba(10,13,17,.06)",
        float: "32px -16px 73px 0 rgba(10,13,17,.08)",
      },
    },
  },
  plugins: [],
};
export default config;
