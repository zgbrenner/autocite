import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const root = path.resolve(import.meta.dirname, "..");

describe("launch content", () => {
  it("publishes at least six substantive legal citation guides", () => {
    const guideDirectory = path.join(root, "src/content/guides");
    const guides = fs.readdirSync(guideDirectory).filter((file) => file.endsWith(".md"));
    expect(guides.length).toBeGreaterThanOrEqual(6);
    for (const guide of guides) {
      const content = fs.readFileSync(path.join(guideDirectory, guide), "utf8");
      expect(content).toMatch(/^---\n[\s\S]+?title:/u);
      expect(content).toMatch(/description:/u);
      expect(content).toMatch(/publishedAt: 2026-/u);
      expect(content.length).toBeGreaterThan(2500);
    }
  });

  it("publishes required crawl and AI discovery artifacts", () => {
    for (const relative of [
      "public/robots.txt",
      "public/llms.txt",
      "public/site.webmanifest",
      "public/favicon.svg",
    ]) {
      expect(fs.existsSync(path.join(root, relative)), relative).toBe(true);
    }
  });
});
