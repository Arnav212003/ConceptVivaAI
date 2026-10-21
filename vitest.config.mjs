import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react({ include: /\.(js|jsx)$/ })],
  // Next.js lets .js files contain JSX; tell Vite's Oxc transformer the same.
  oxc: {
    include: /\.(js|jsx)$/,
    exclude: [],
    lang: "jsx",
    jsx: { runtime: "automatic" },
  },
  resolve: {
    alias: { "@": path.join(root, "src") },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.js"],
    include: ["src/**/*.test.{js,jsx}"],
    restoreMocks: true,
  },
});
