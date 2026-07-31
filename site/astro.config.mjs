import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

const site = process.env.PUBLIC_SITE_URL ?? "https://zgbrenner.github.io/autocite/";

export default defineConfig({
  site,
  output: "static",
  integrations: [sitemap()],
  build: {
    assets: "assets",
  },
  vite: {
    build: {
      sourcemap: true,
    },
  },
});
