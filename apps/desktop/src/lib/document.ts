import { marked } from "marked";
import TurndownService from "turndown";

import type { HeadingItem } from "../types";

const turndown = new TurndownService({
  headingStyle: "atx",
  bulletListMarker: "-",
  codeBlockStyle: "fenced",
  emDelimiter: "*",
  strongDelimiter: "**",
});

turndown.addRule("preservePageMarker", {
  filter: (node) =>
    node.nodeType === Node.COMMENT_NODE &&
    (node.nodeValue ?? "").trim().startsWith("page:"),
  replacement: (_content, node) => `\n\n<!-- ${(node.nodeValue ?? "").trim()} -->\n\n`,
});

marked.setOptions({
  gfm: true,
  breaks: false,
});

const BLOCKED_ELEMENTS = new Set([
  "SCRIPT",
  "STYLE",
  "IFRAME",
  "OBJECT",
  "EMBED",
  "FORM",
  "INPUT",
  "BUTTON",
  "TEXTAREA",
  "SELECT",
  "OPTION",
  "META",
  "LINK",
  "BASE",
  "SVG",
  "MATH",
]);

function isSafeUrl(value: string): boolean {
  const trimmed = value.trim().toLowerCase();
  return (
    trimmed === "" ||
    trimmed.startsWith("#") ||
    trimmed.startsWith("http://") ||
    trimmed.startsWith("https://") ||
    trimmed.startsWith("mailto:") ||
    trimmed.startsWith("tel:")
  );
}

export function sanitizeHtml(html: string): string {
  const parser = new DOMParser();
  const document = parser.parseFromString(html, "text/html");
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  const elements: Element[] = [];
  let current = walker.nextNode();
  while (current) {
    elements.push(current as Element);
    current = walker.nextNode();
  }

  for (const element of elements) {
    if (BLOCKED_ELEMENTS.has(element.tagName)) {
      element.remove();
      continue;
    }
    for (const attribute of Array.from(element.attributes)) {
      const name = attribute.name.toLowerCase();
      if (name.startsWith("on") || name === "style" || name === "srcdoc") {
        element.removeAttribute(attribute.name);
        continue;
      }
      if ((name === "href" || name === "src") && !isSafeUrl(attribute.value)) {
        element.removeAttribute(attribute.name);
      }
    }
    if (element.tagName === "A") {
      element.setAttribute("rel", "noreferrer noopener");
      element.setAttribute("target", "_blank");
    }
  }
  return document.body.innerHTML;
}

export function markdownToHtml(markdown: string): string {
  const rendered = marked.parse(markdown, { async: false });
  return sanitizeHtml(typeof rendered === "string" ? rendered : "");
}

export function htmlToMarkdown(html: string): string {
  return turndown.turndown(sanitizeHtml(html)).replace(/\n{3,}/g, "\n\n").trim();
}

export function extractHeadings(html: string): HeadingItem[] {
  const document = new DOMParser().parseFromString(html, "text/html");
  return Array.from(document.querySelectorAll("h1, h2, h3, h4, h5, h6"))
    .map((heading, index) => {
      const text = heading.textContent?.trim() ?? "";
      const level = Number.parseInt(heading.tagName.slice(1), 10);
      return {
        id: heading.id || `heading-${index}`,
        level,
        text,
      };
    })
    .filter((heading) => heading.text.length > 0);
}

export function countWords(text: string): number {
  return text.match(/[\p{L}\p{N}’'-]+/gu)?.length ?? 0;
}

export function countCharacters(text: string): number {
  return Array.from(text).length;
}

export function selectedTextStats(text: string): { words: number; characters: number } {
  return { words: countWords(text), characters: countCharacters(text) };
}

export function normalizeDocumentTitle(value: string): string {
  const normalized = value.replace(/[\u0000-\u001f<>:"/\\|?*]/g, " ").trim();
  return normalized || "Untitled document";
}

export function issueExcerpt(
  documentText: string,
  start: number,
  end: number,
  radius = 90,
): { before: string; target: string; after: string } {
  const boundedStart = Math.max(0, Math.min(start, documentText.length));
  const boundedEnd = Math.max(boundedStart, Math.min(end, documentText.length));
  return {
    before: documentText.slice(Math.max(0, boundedStart - radius), boundedStart),
    target: documentText.slice(boundedStart, boundedEnd),
    after: documentText.slice(boundedEnd, Math.min(documentText.length, boundedEnd + radius)),
  };
}

export function formatRelativeTime(iso: string): string {
  const value = Date.parse(iso);
  if (Number.isNaN(value)) return "Unknown";
  const delta = Date.now() - value;
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (delta < minute) return "Just now";
  if (delta < hour) return `${Math.floor(delta / minute)}m ago`;
  if (delta < day) return `${Math.floor(delta / hour)}h ago`;
  if (delta < 7 * day) return `${Math.floor(delta / day)}d ago`;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: new Date(value).getFullYear() === new Date().getFullYear() ? undefined : "numeric",
  }).format(new Date(value));
}

export function scrollToText(text: string): boolean {
  if (!text) return false;
  const root = document.querySelector(".autocite-editor .ProseMirror");
  if (!root) return false;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const content = node.textContent ?? "";
    const offset = content.indexOf(text);
    if (offset >= 0) {
      const range = document.createRange();
      range.setStart(node, offset);
      range.setEnd(node, Math.min(content.length, offset + text.length));
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
      (node.parentElement ?? root).scrollIntoView({ behavior: "smooth", block: "center" });
      return true;
    }
    node = walker.nextNode();
  }
  return false;
}
