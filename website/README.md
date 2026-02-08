# SuperLocalMemory V2 Website

Official static website for SuperLocalMemory V2, built with Astro and deployed to GitHub Pages.

## 🌐 Live Site

**Production:** https://varun369.github.io/SuperLocalMemoryV2

**Future Domain:** superlocalmemory.is-a.dev (planned)

---

## 📁 Structure

```
website/
├── src/
│   ├── pages/          # Routes (index, docs, features, comparison)
│   ├── layouts/        # Layout components (BaseLayout)
│   ├── styles/         # Global CSS
│   └── components/     # Reusable components (future)
├── public/             # Static assets (favicon)
├── dist/               # Built output (gitignored)
├── astro.config.mjs    # Astro configuration
├── package.json        # Dependencies
└── tsconfig.json       # TypeScript config
```

---

## 🚀 Development

### Prerequisites

- Node.js 20+
- npm

### Local Development

```bash
# Install dependencies
cd website
npm install

# Start dev server (http://localhost:4321)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server at http://localhost:4321 |
| `npm run build` | Build production site to `dist/` |
| `npm run preview` | Preview production build locally |
| `npm run astro` | Run Astro CLI commands |

---

## 📦 Deployment

### Automatic Deployment (GitHub Actions)

The website automatically deploys to GitHub Pages when:
- Changes are pushed to `main` branch in the `website/` directory
- Or manually triggered via GitHub Actions UI

**Workflow:** `.github/workflows/deploy-website.yml`

### Manual Deployment

#### Step 1: Enable GitHub Pages

1. Go to repository **Settings** → **Pages**
2. Under **Build and deployment**:
   - Source: **GitHub Actions** (NOT Deploy from branch)
3. Save

#### Step 2: Build Locally (Optional - Test First)

```bash
cd website
npm install
npm run build
```

Verify build succeeds before pushing.

#### Step 3: Commit and Push

```bash
# From repository root
git add website/
git commit -m "Docs: Update website"
git push origin main
```

#### Step 4: Monitor Deployment

1. Go to **Actions** tab on GitHub
2. Watch "Deploy Website to GitHub Pages" workflow
3. Should complete in 2-3 minutes
4. Visit: https://varun369.github.io/SuperLocalMemoryV2

---

## 🎨 Design System

### Colors

```css
--color-bg: #0d1117              /* Main background */
--color-bg-secondary: #161b22    /* Cards, sections */
--color-bg-tertiary: #1c2128     /* Code blocks */
--color-border: #30363d          /* Borders */
--color-text: #e6edf3            /* Primary text */
--color-text-secondary: #8b949e  /* Secondary text */
--color-accent: #7c3aed          /* Primary brand color */
--color-link: #58a6ff            /* Links */
--color-success: #3fb950         /* Success states */
```

### Typography

- **Font Family:** System fonts (-apple-system, BlinkMacSystemFont, Segoe UI)
- **Code Font:** SF Mono, Monaco, Cascadia Code, Roboto Mono

### Components

- **Buttons:** `.btn`, `.btn-secondary`
- **Cards:** `.card` (with hover effects)
- **Badges:** `.badge`, `.badge-success`, `.badge-accent`
- **Grid:** `.grid`, `.grid-2`, `.grid-3`

---

## 📄 Pages

| Route | File | Description |
|-------|------|-------------|
| `/` | `src/pages/index.astro` | Home page with hero, features, comparison |
| `/docs` | `src/pages/docs.astro` | Documentation hub with links to wiki |
| `/features` | `src/pages/features.astro` | Detailed feature descriptions |
| `/comparison` | `src/pages/comparison.astro` | vs Mem0, Zep, Personal.AI |

---

## 🔍 SEO Optimization

### Current SEO Features

✅ Semantic HTML structure
✅ Meta descriptions on all pages
✅ Open Graph tags
✅ Twitter Card tags
✅ Sitemap generation (`sitemap-index.xml`)
✅ Canonical URLs
✅ Mobile responsive
✅ Fast loading (<1s)

### Target Keywords

- local AI memory
- claude memory extension
- AI memory system free
- alternative to Mem0
- alternative to Zep
- MCP integration
- Model Context Protocol

---

## 🧪 Testing

### Pre-deployment Checklist

```bash
# 1. Test build
cd website
npm run build

# 2. Check for errors
# Should show: "4 page(s) built in Xms"

# 3. Preview locally
npm run preview

# 4. Manual checks:
# - Navigate to all pages
# - Test mobile responsiveness (Chrome DevTools)
# - Verify links work
# - Check GitHub stars badge updates
# - Test navigation menu
```

### Build Performance

| Metric | Target | Actual |
|--------|--------|--------|
| Build time | < 5s | ~500ms |
| Page count | 4 pages | 4 pages |
| Bundle size | < 500KB | ~300KB |

---

## 🚨 Troubleshooting

### Build Fails

**Error:** `npm run build` fails with TypeScript errors

**Solution:**
```bash
npm run astro check
# Fix any reported errors
```

### GitHub Pages Shows 404

**Possible causes:**

1. **Wrong Pages settings**
   - Go to Settings → Pages
   - Ensure Source is **GitHub Actions** (not Deploy from branch)

2. **Base path mismatch**
   - Check `astro.config.mjs`: `base: '/SuperLocalMemoryV2'`
   - All links should use `/SuperLocalMemoryV2/` prefix

3. **Workflow didn't run**
   - Check Actions tab
   - Re-run workflow manually if needed

### Styles Not Loading

**Issue:** Site appears unstyled

**Check:**
- `src/styles/global.css` exists
- Imported in `src/layouts/BaseLayout.astro`
- Build completed successfully

---

## 🔮 Future Enhancements

### Planned Features

- [ ] Blog section (Astro Content Collections)
- [ ] Interactive demo (embed terminal)
- [ ] Video tutorials
- [ ] Testimonials section
- [ ] Live installation counter
- [ ] Search functionality
- [ ] Dark/light theme toggle (currently dark-only)

### Domain Migration (Planned)

When `superlocalmemory.is-a.dev` is approved:

1. Update `astro.config.mjs`:
   ```js
   site: 'https://superlocalmemory.is-a.dev'
   base: '/'  // Remove base path
   ```

2. Add CNAME file:
   ```bash
   echo "superlocalmemory.is-a.dev" > website/public/CNAME
   ```

3. Rebuild and deploy

---

## 📝 Content Updates

### Updating Existing Pages

1. Edit files in `src/pages/`
2. Test locally: `npm run dev`
3. Commit and push to trigger auto-deployment

### Adding New Pages

1. Create new `.astro` file in `src/pages/`
2. Use `BaseLayout` component
3. Add navigation link in `BaseLayout.astro`
4. Update this README

### Updating Documentation Links

Most documentation lives in the GitHub Wiki. To update:

1. Edit wiki content in `/wiki-content/` (main repo)
2. Run `./sync-wiki.sh` to deploy to GitHub Wiki
3. Wiki links in website will automatically work

---

## 🤝 Contributing

### Design Guidelines

- Maintain dark-theme aesthetic (GitHub Dark inspired)
- Use semantic HTML (h1-h6 hierarchy)
- Mobile-first responsive design
- Accessibility: proper ARIA labels, alt text
- Performance: lazy-load images, minimize JS

### Code Style

- Use Astro components for reusability
- Keep styles in `global.css` (avoid inline styles where possible)
- Comment complex sections
- Follow existing naming conventions

---

## 📊 Analytics (Future)

Currently NO analytics or tracking (privacy-first).

If added in future:
- Use privacy-respecting service (Plausible, Fathom)
- Opt-in only
- No cookies
- No personal data collection

---

## 📧 Support

Issues with the website:
- **Report bugs:** https://github.com/varun369/SuperLocalMemoryV2/issues
- **Suggestions:** Open a discussion

---

## 📜 License

MIT License - Same as SuperLocalMemory V2 main project

Created by **Varun Pratap Bhardwaj** - Solution Architect & Original Creator

---

**Last Updated:** February 7, 2026
**Website Version:** 1.0.0
**SuperLocalMemory Version:** v2.3.0-universal
