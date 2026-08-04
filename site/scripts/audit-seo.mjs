import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

import * as cheerio from "cheerio";

async function walk(directory) {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(fullPath)));
    else files.push(fullPath);
  }
  return files;
}

function routeForHtml(distDirectory, filename) {
  const relative = path.relative(distDirectory, filename).replaceAll(path.sep, "/");
  if (relative === "index.html") return "/";
  return `/${relative.replace(/index\.html$/u, "").replace(/\.html$/u, "/")}`.replace(/\/+/gu, "/");
}

function targetForHref(distDirectory, href) {
  const clean = href.split(/[?#]/u, 1)[0];
  if (!clean || clean === "/") return path.join(distDirectory, "index.html");
  const relative = clean.replace(/^\/+/, "");
  if (path.extname(relative)) return path.join(distDirectory, relative);
  return path.join(distDirectory, relative, "index.html");
}

export async function auditDirectory(distDirectory) {
  const absoluteDist = path.resolve(distDirectory);
  const allFiles = await walk(absoluteDist);
  const htmlFiles = allFiles.filter((filename) => filename.endsWith(".html"));
  const errors = [];
  const pages = [];
  const titles = new Map();
  const canonicals = new Map();

  for (const filename of htmlFiles) {
    const html = await fs.readFile(filename, "utf8");
    const $ = cheerio.load(html);
    const route = routeForHtml(absoluteDist, filename);
    const title = $("title").first().text().trim();
    const description = $('meta[name="description"]').attr("content")?.trim() ?? "";
    const canonical = $('link[rel="canonical"]').attr("href")?.trim() ?? "";
    const h1Count = $("h1").length;
    const noindex = ($('meta[name="robots"]').attr("content") ?? "").includes("noindex");

    if (!title) errors.push(`${route}: missing title`);
    if (title.length > 65) errors.push(`${route}: title exceeds 65 characters`);
    if (!description) errors.push(`${route}: missing meta description`);
    if (description.length < 70 || description.length > 180) {
      errors.push(`${route}: description must be 70-180 characters`);
    }
    if (!canonical || !/^https:\/\//u.test(canonical)) errors.push(`${route}: missing absolute HTTPS canonical`);
    if (h1Count !== 1) errors.push(`${route}: expected one H1, found ${h1Count}`);
    if (noindex && route !== "/404/") errors.push(`${route}: unexpected noindex`);
    if (!noindex && route === "/404/") errors.push(`${route}: 404 page must be noindex`);

    if (title) {
      const existing = titles.get(title);
      if (existing) errors.push(`${route}: duplicate title also used by ${existing}`);
      else titles.set(title, route);
    }
    if (canonical) {
      const existing = canonicals.get(canonical);
      if (existing) errors.push(`${route}: duplicate canonical also used by ${existing}`);
      else canonicals.set(canonical, route);
    }

    $('script[type="application/ld+json"]').each((_, element) => {
      try {
        JSON.parse($(element).text());
      } catch (error) {
        errors.push(`${route}: invalid JSON-LD (${error instanceof Error ? error.message : String(error)})`);
      }
    });

    for (const element of $("a[href]").toArray()) {
      const href = $(element).attr("href") ?? "";
      if (!href.startsWith("/") || href.startsWith("//")) continue;
      const target = targetForHref(absoluteDist, href);
      try {
        await fs.access(target);
      } catch {
        errors.push(`${route}: broken internal link ${href}`);
      }
    }

    pages.push({ route, title, description, canonical, h1Count, noindex });
  }

  for (const required of ["robots.txt", "llms.txt", "site.webmanifest", "favicon.svg", "rss.xml"]) {
    try {
      await fs.access(path.join(absoluteDist, required));
    } catch {
      errors.push(`missing required public artifact: ${required}`);
    }
  }

  const sitemapExists = allFiles.some((filename) => /sitemap(?:-index|-\d+)?\.xml$/u.test(filename));
  if (!sitemapExists) errors.push("missing generated sitemap XML");

  const report = {
    generatedAt: new Date().toISOString(),
    pageCount: pages.length,
    pages,
    errors,
  };
  const reportDirectory = path.join(path.dirname(absoluteDist), "reports");
  await fs.mkdir(reportDirectory, { recursive: true });
  await fs.writeFile(path.join(reportDirectory, "seo-audit.json"), `${JSON.stringify(report, null, 2)}\n`);
  return report;
}

async function main() {
  const dist = process.argv[2] ?? "dist";
  const report = await auditDirectory(dist);
  if (report.errors.length > 0) {
    console.error(report.errors.join("\n"));
    process.exitCode = 1;
    return;
  }
  console.log(`SEO audit passed for ${report.pageCount} pages.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  await main();
}
