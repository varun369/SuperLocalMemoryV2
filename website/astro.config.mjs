import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://superlocalmemory.com',
  base: '/',

  integrations: [mdx(), sitemap({
    customPages: [
      'https://superlocalmemory.com/architecture',
      'https://superlocalmemory.com/learning',
    ],
    serialize(item) {
      item.lastmod = new Date('2026-02-16');
      if (item.url === 'https://superlocalmemory.com/') {
        item.priority = 1.0;
        item.changefreq = 'weekly';
      } else if (item.url.includes('architecture')) {
        item.priority = 0.9;
        item.changefreq = 'monthly';
      } else if (item.url.includes('learning')) {
        item.priority = 0.9;
        item.changefreq = 'monthly';
      } else {
        item.priority = 0.8;
        item.changefreq = 'monthly';
      }
      return item;
    },
  }), react()],

  markdown: {
    shikiConfig: {
      theme: 'github-dark',
      wrap: true
    }
  },

  vite: {
    plugins: [tailwindcss()]
  }
});