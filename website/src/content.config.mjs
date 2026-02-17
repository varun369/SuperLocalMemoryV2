import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    author: z.string().default('Varun Pratap Bhardwaj'),
    tags: z.array(z.string()).default([]),
    category: z.enum(['tutorials', 'comparisons', 'guides', 'updates', 'education']).default('tutorials'),
    image: z.string().optional(),
    draft: z.boolean().default(false),
    keywords: z.string().optional(),
    slug: z.string().optional(),
  }),
});

export const collections = { blog };
