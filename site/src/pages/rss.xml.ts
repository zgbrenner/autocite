import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import type { APIContext } from "astro";

export async function GET(context: APIContext) {
  const guides = (await getCollection("guides")).sort(
    (a, b) => b.data.publishedAt.valueOf() - a.data.publishedAt.valueOf(),
  );

  return rss({
    title: "AutoCite legal citation guides",
    description:
      "Privacy-aware guides to Bluebook citation review, source verification, short forms, and legal citation workflows.",
    site: context.site ?? "https://zgbrenner-autocite.pages.dev/",
    items: guides.map((guide) => ({
      title: guide.data.title,
      description: guide.data.description,
      pubDate: guide.data.publishedAt,
      link: `/guides/${guide.id}/`,
    })),
    customData: '<language>en-us</language>',
  });
}
