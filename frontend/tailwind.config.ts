import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cardinalsRed: "#97233F",
        cardinalsBlack: "#000000",
        cardinalsSand: "#FFB612",
      },
    },
  },
  plugins: [],
};

export default config;
