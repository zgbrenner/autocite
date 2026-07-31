export const SITE = {
  name: "AutoCite",
  category: "Private legal citation checker",
  shortDescription:
    "Fix supported Bluebook citation problems without rewriting your document or uploading confidential legal work.",
  defaultSiteUrl: "https://zgbrenner.github.io/autocite/",
  repositoryUrl: "https://github.com/zgbrenner/autocite",
  releaseUrl: "https://github.com/zgbrenner/autocite/releases/latest",
  licenseUrl: "https://github.com/zgbrenner/autocite/blob/main/LICENSE",
  privacySummary: "Local-first. No application telemetry. Your source document stays yours.",
  supportedFormats: ["DOCX", "searchable PDF", "Markdown", "TXT"],
  navigation: [
    { href: "/citation-risk-scan/", label: "Free scan" },
    { href: "/bluebook-citation-checker/", label: "Bluebook checker" },
    { href: "/guides/", label: "Guides" },
    { href: "/methodology/", label: "Methodology" },
  ],
} as const;

export const SITE_URL = import.meta.env?.PUBLIC_SITE_URL ?? SITE.defaultSiteUrl;
