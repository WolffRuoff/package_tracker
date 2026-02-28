import resolve from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";
import typescript from "rollup-plugin-typescript2";

export default {
  input: "src/package-tracker-card.ts",
  output: {
    file: "../custom_components/package_tracker/frontend/package-tracker-card.js",
    format: "es",
  },
  plugins: [
    resolve(),
    typescript(),
    terser(),
  ],
};
