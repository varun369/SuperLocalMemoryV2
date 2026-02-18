import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://superlocalmemory.com',
  base: '/',
  trailingSlash: 'never',

  integrations: [mdx(), sitemap({
    customPages: [
      'https://superlocalmemory.com/architecture',
      'https://superlocalmemory.com/learning',
      'https://superlocalmemory.com/integrations/claude-code',
      'https://superlocalmemory.com/integrations/cursor',
      'https://superlocalmemory.com/integrations/chatgpt',
    ],
    serialize(item) {
      item.lastmod = new Date('2026-02-18');
      if (item.url === 'https://superlocalmemory.com/') {
        item.priority = 1.0;
        item.changefreq = 'weekly';
      } else if (item.url.includes('/integrations/')) {
        item.priority = 0.9;
        item.changefreq = 'monthly';
      } else if (item.url.includes('architecture')) {
        item.priority = 0.9;
        item.changefreq = 'monthly';
      } else if (item.url.includes('learning')) {
        item.priority = 0.9;
        item.changefreq = 'monthly';
      } else if (item.url.includes('comparison') || item.url.includes('pricing')) {
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

  build: {
    // Inline all CSS into <style> tags — eliminates render-blocking CSS network requests
    inlineStylesheets: 'always',
  },

  vite: {
    plugins: [tailwindcss()]
  }
});