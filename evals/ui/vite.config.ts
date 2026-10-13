import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

// Carbon's Sass references fonts as `~@ibm/plex/...`; map that prefix to the installed package.
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: "./",
  resolve: {
    alias: [{ find: /^~@ibm\/plex/, replacement: fileURLToPath(new URL("../node_modules/@ibm/plex", import.meta.url)) }],
  },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
});
