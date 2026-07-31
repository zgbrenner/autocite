import { describe, expect, it } from "vitest";

import {
  countWords,
  extractHeadings,
  htmlToMarkdown,
  issueExcerpt,
  markdownToHtml,
  sanitizeHtml,
} from "./document";

describe("document utilities", () => {
  it("removes executable markup and unsafe links", () => {
    const sanitized = sanitizeHtml(
      '<p onclick="alert(1)">Text <a href="javascript:alert(1)">link</a></p><script>alert(2)</script>',
    );

    expect(sanitized).toContain("Text");
    expect(sanitized).not.toContain("onclick");
    expect(sanitized).not.toContain("javascript:");
    expect(sanitized).not.toContain("script");
  });

  it("round trips ordinary legal Markdown without changing the text", () => {
    const markdown = "# Argument\n\nSee **42 U.S.C. § 1983**.\n\n- First point\n- Second point";
    const html = markdownToHtml(markdown);
    const returned = htmlToMarkdown(html);

    expect(returned).toContain("# Argument");
    expect(returned).toContain("**42 U.S.C. § 1983**");
    expect(returned).toContain("- First point");
  });

  it("extracts a hierarchical document outline", () => {
    expect(extractHeadings("<h1>Argument</h1><p>Text</p><h2>Standard</h2>")).toEqual([
      { id: "heading-0", level: 1, text: "Argument" },
      { id: "heading-1", level: 2, text: "Standard" },
    ]);
  });

  it("counts Unicode words and produces bounded issue context", () => {
    const text = "The court’s judgment cites 410 U.S. 113.";
    expect(countWords(text)).toBe(8);
    expect(issueExcerpt(text, 27, 39, 8)).toEqual({
      before: " cites ",
      target: "410 U.S. 113",
      after: ".",
    });
  });
});
