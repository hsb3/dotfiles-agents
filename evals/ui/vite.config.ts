import { defineConfig } from "vite";

export default defineConfig({
  resolve: { alias: { "~@ibm/plex": new URL("./node_modules/@ibm/plex", import.meta.url).pathname } },
  build: { outDir: "dist" },
});
