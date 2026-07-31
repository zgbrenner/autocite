import { SITE, SITE_URL } from "../config";

export function normalizePath(pathname: string): string {
  const withoutQuery = pathname.split(/[?#]/u, 1)[0] ?? "/";
  const withLeadingSlash = withoutQuery.startsWith("/") ? withoutQuery : `/${withoutQuery}`;
  if (withLeadingSlash === "/") return "/";
  return `${withLeadingSlash.replace(/\/+$/u, "")}/`;
}

export function buildCanonical(pathname: string): string {
  const normalized = normalizePath(pathname);
  if (normalized === "/") return new URL(SITE_URL).toString();
  return new URL(normalized.slice(1), SITE_URL).toString();
}

export function buildPageTitle(title: string): string {
  const trimmed = title.trim();
  return trimmed === SITE.name ? SITE.name : `${trimmed} | ${SITE.name}`;
}

export function buildSoftwareApplicationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: SITE.name,
    applicationCategory: "LegalService",
    operatingSystem: "Windows, macOS, Linux",
    description: SITE.shortDescription,
    url: buildCanonical("/"),
    downloadUrl: SITE.releaseUrl,
    codeRepository: SITE.repositoryUrl,
    license: SITE.licenseUrl,
    isAccessibleForFree: true,
    featureList: [
      "Local-first legal citation review",
      "Bluepages and Whitepages workflows",
      "Deterministic citation corrections",
      "DOCX, searchable PDF, Markdown, and TXT support",
      "No application telemetry",
    ],
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
  } as const;
}

export function buildBreadcrumbJsonLd(items: Array<{ name: string; path: string }>) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: buildCanonical(item.path),
    })),
  } as const;
}

export function buildFaqJsonLd(items: Array<{ question: string; answer: string }>) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  } as const;
}
