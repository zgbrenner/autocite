import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const guides = defineCollection({
  loader: glob({ pattern: "**/*.{md,mdx}", base: "./src/content/guides" }),
  schema: z.object({
    title: z.string().min(20).max(90),
    description: z.string().min(80).max(180),
    publishedAt: z.coerce.date(),
    updatedAt: z.coerce.date().optional(),
    audience: z.enum(["students", "journals", "lawyers", "all"]),
    keywords: z.array(z.string()).min(2).max(8),
  }),
});

export const collections = { guides };
