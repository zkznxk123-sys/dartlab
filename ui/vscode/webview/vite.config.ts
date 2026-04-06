import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      "$shared": new URL("../../shared", import.meta.url).pathname,
    },
  },
  build: {
    outDir: "../dist/webview",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: "src/main.ts",
        dev: "dev/devEntry.ts",
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name][extname]",
      },
    },
  },
});
