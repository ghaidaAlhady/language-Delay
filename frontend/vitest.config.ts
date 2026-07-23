import { fileURLToPath, URL } from "node:url";

import { defineConfig, mergeConfig } from "vitest/config";

import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/tests/setup.ts"],
      css: true,
      exclude: ["**/node_modules/**", "**/e2e/**", "**/dist/**"],
      coverage: {
        provider: "v8",
        reporter: ["text", "html"],
        exclude: ["e2e/**", "src/main.tsx", "src/tests/**"],
      },
    },
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
  }),
);
