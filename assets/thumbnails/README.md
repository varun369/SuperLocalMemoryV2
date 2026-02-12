# Thumbnail Gallery — SuperLocalMemory V2

Auto-generated optimized thumbnail versions of all dashboard screenshots.

## Specifications

- **Size:** 320×180px (16:9 aspect ratio)
- **Formats:** PNG (for wiki/docs) + WebP (for website)
- **Quality:** High-fidelity resizing with LANCZOS resampling + unsharp masking
- **File Size:** < 50KB per thumbnail
- **Metadata:** `index.json` with full catalog

## Files

### Dashboard Screenshots (12 total)

| Thumbnail | Category | Description |
|-----------|----------|-------------|
| `dashboard-agents-thumb.{png,webp}` | Agents | Agent connections and activity tracking |
| `dashboard-clusters-thumb.{png,webp}` | Clusters | Knowledge graph clusters and relationships |
| `dashboard-filtered-thumb.{png,webp}` | Search | Advanced memory search and filtering interface |
| `dashboard-graph-thumb.{png,webp}` | Graph | Interactive knowledge graph visualization |
| `dashboard-live-events-thumb.{png,webp}` | Events | Real-time live event stream (light mode) |
| `dashboard-live-events-dark-thumb.{png,webp}` | Events | Real-time live event stream (dark mode) |
| `dashboard-memories-thumb.{png,webp}` | Memories | Detailed memory list with search and filtering |
| `dashboard-memories-dark-thumb.{png,webp}` | Memories | Detailed memory list (dark mode) |
| `dashboard-overview-thumb.{png,webp}` | Dashboard | Main dashboard with stats and graph overview |
| `dashboard-overview-dark-thumb.{png,webp}` | Dashboard | Main dashboard (dark mode) |
| `dashboard-patterns-thumb.{png,webp}` | Patterns | Learned coding patterns and user preferences |
| `dashboard-timeline-thumb.{png,webp}` | Timeline | Chronological timeline of memories and events |

## Usage

### Website (Astro/Next)

Use WebP format for modern browsers with PNG fallback:

```html
<picture>
  <source srcset="dashboard-overview-thumb.webp" type="image/webp">
  <img src="dashboard-overview-thumb.png" alt="Dashboard Overview" width="320" height="180">
</picture>
```

Or directly with modern browser support:

```html
<img src="dashboard-overview-thumb.webp" alt="Dashboard Overview" width="320" height="180">
```

### Documentation (GitHub Wiki / Markdown)

Use PNG format (better compatibility):

```markdown
![Dashboard Overview](../assets/thumbnails/dashboard-overview-thumb.png)
```

### Gallery / Screenshot Grid

Reference the metadata index for dynamic gallery generation:

```javascript
import thumbnails from './assets/thumbnails/index.json';

Object.entries(thumbnails).forEach(([key, meta]) => {
  console.log(`${meta.title}: ${meta.description}`);
  console.log(`  Full: ${meta.full_image}`);
  console.log(`  Thumbnail: ${meta.thumbnail_webp}`);
});
```

### Social Media Preview Cards

Use WebP format with 16:9 aspect ratio. The 320×180px size is perfect for:
- Twitter card images (auto-resized by platform)
- LinkedIn preview images
- GitHub social preview
- Discord embeds

## Index Metadata

The `index.json` file contains complete metadata for each thumbnail:

```json
{
  "dashboard-overview": {
    "title": "Dashboard Overview",
    "description": "Main dashboard with memory statistics and knowledge graph overview",
    "category": "dashboard",
    "full_image": "../screenshots/dashboard/dashboard-overview.png",
    "thumbnail_png": "dashboard-overview-thumb.png",
    "thumbnail_webp": "dashboard-overview-thumb.webp",
    "created": "2026-02-12T09:59:03.606594",
    "original_size": "3840×2160",
    "thumbnail_size": "320×180",
    "png_size_kb": 13.52,
    "webp_size_kb": 3.28
  }
}
```

Use this for:
- Dynamic gallery generation
- Alt text lookup
- File size tracking
- Category-based filtering
- SEO optimization

## File Sizes

Total size of all 24 thumbnails (12 images × 2 formats):

- **PNG total:** ~292.8 KB (avg 12.2 KB each)
- **WebP total:** ~113.6 KB (avg 4.7 KB each)
- **Savings:** 61% reduction using WebP

### Size Breakdown

| Format | Min | Avg | Max |
|--------|-----|-----|-----|
| PNG | 10.7 KB | 18.6 KB | 31.2 KB |
| WebP | 2.6 KB | 5.8 KB | 9.7 KB |

All thumbnails are well under the 50 KB limit.

## Regenerating Thumbnails

If you need to regenerate thumbnails (e.g., after updating source images):

```bash
# Ensure you're in the repository root
python3 scripts/generate-thumbnails.py
```

This script will:
1. Scan `assets/screenshots/` for all image files
2. Resize to 320×180 (maintain aspect ratio + crop)
3. Apply LANCZOS resampling for quality
4. Apply subtle unsharp masking for sharpness
5. Generate PNG and WebP versions
6. Create/update `index.json` metadata
7. Report file sizes and optimization stats

### Script Features

- **Aspect ratio preservation:** Crops intelligently to maintain 16:9
- **Quality optimization:** LANCZOS for resizing, unsharp mask for sharpening
- **Format coverage:** Both PNG and WebP with optimal compression
- **Metadata generation:** Auto-generates titles, descriptions, categories
- **Error handling:** Skips corrupted images, reports issues
- **Verification:** Checks file sizes against limits

## Categories

Thumbnails are automatically categorized:

- **dashboard** — Main dashboard overview
- **agents** — Agent monitoring and connections
- **timeline** — Chronological event/memory timeline
- **patterns** — Learned coding patterns
- **clusters** — Knowledge graph clusters
- **memories** — Detailed memory list
- **graph** — Interactive graph visualization
- **search** — Search and filtering
- **events** — Live event stream

## Browser Support

### WebP Format

- Chrome 23+ ✅
- Firefox 65+ ✅
- Safari 16+ ✅
- Edge 18+ ✅
- Internet Explorer ❌ (use PNG fallback)

### PNG Format

- All modern browsers ✅
- All devices ✅
- Perfect for documentation

## Performance Tips

1. **Lazy load thumbnails** in galleries to improve page load
2. **Use `<picture>` tags** with WebP + PNG fallback for optimal performance
3. **Set explicit dimensions** (320×180) to prevent layout shift
4. **Compress further** if needed: `pngquant` or `imagemagick`
5. **Cache aggressively** — thumbnails rarely change

## Related Documentation

- `../assets/README.md` — General asset guidelines
- `../assets/screenshots/` — Full-resolution source images
- `scripts/generate-thumbnails.py` — Thumbnail generation script

## Metadata Format Specification

Each entry in `index.json` contains:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Human-readable title (e.g., "Dashboard Overview") |
| `description` | string | Long description for alt text and captions |
| `category` | string | Category for filtering/organization |
| `full_image` | string | Path to full-resolution source image |
| `thumbnail_png` | string | PNG thumbnail filename |
| `thumbnail_webp` | string | WebP thumbnail filename |
| `created` | ISO 8601 | Timestamp of thumbnail generation |
| `original_size` | string | Original image dimensions (WIDTHxHEIGHT) |
| `thumbnail_size` | string | Thumbnail dimensions (always 320×180) |
| `png_size_kb` | number | PNG file size in kilobytes |
| `webp_size_kb` | number | WebP file size in kilobytes |

---

**Last Updated:** February 12, 2026
**Generator:** `scripts/generate-thumbnails.py`
**License:** MIT (inherited from SuperLocalMemory V2)
