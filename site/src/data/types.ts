export interface AudienceSection {
  title: string;
  paragraphs: string[];
  bullets?: string[];
}

export interface AudiencePageData {
  slug: string;
  title: string;
  h1: string;
  description: string;
  lead: string;
  asideTitle: string;
  asideBody: string;
  sections: AudienceSection[];
  faq: Array<{ question: string; answer: string }>;
  ctaHeading?: string;
  ctaBody?: string;
}
