# GIF Usage Examples

## In Documentation (Markdown)

### README.md
```markdown
## Quick Demo

![SuperLocalMemory CLI in Action](assets/gifs/cli-demo.gif)

### Web Dashboard
![Dashboard Search](assets/gifs/dashboard-search.gif)

### Knowledge Graph
![Interactive Graph Explorer](assets/gifs/graph-interaction.gif)
```

### Feature Documentation
```markdown
## v2.5: Real-Time Event Stream

The new Event Bus broadcasts every memory operation in real-time:

![Live Event Stream](assets/gifs/event-stream.gif)

Subscribe to events via WebSocket, SSE, or HTTP webhooks.
```

## In Website (HTML/Astro)

### Hero Section
```html
<section class="hero">
  <h1>Your AI Memory, Persistent & Local</h1>
  <img src="/assets/gifs/dashboard-tabs.gif"
       alt="SuperLocalMemory Dashboard"
       width="1400"
       loading="lazy">
</section>
```

### Features Section
```html
<div class="feature">
  <h3>Command Line Interface</h3>
  <p>Simple, powerful commands for all memory operations.</p>
  <img src="/assets/gifs/cli-demo.gif"
       alt="CLI Demo"
       width="800"
       style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
</div>
```

### Comparison Section
```html
<div class="comparison">
  <h2>Knowledge Graph vs Traditional Search</h2>
  <div class="side-by-side">
    <div>
      <h4>Hierarchical Search</h4>
      <img src="/assets/gifs/dashboard-search.gif" alt="Search Demo">
    </div>
    <div>
      <h4>Graph Navigation</h4>
      <img src="/assets/gifs/graph-interaction.gif" alt="Graph Demo">
    </div>
  </div>
</div>
```

## In GitHub Wiki

```markdown
# Dashboard Overview

Navigate through all dashboard features:

![Dashboard Navigation](https://raw.githubusercontent.com/varun369/SuperLocalMemoryV2/main/assets/gifs/dashboard-tabs.gif)

## Real-Time Events (v2.5+)

![Event Stream](https://raw.githubusercontent.com/varun369/SuperLocalMemoryV2/main/assets/gifs/event-stream.gif)
```

## In Presentations

For PowerPoint/Keynote, export GIFs as video:
```bash
# Convert GIF to MP4 (higher quality for presentations)
ffmpeg -i assets/gifs/dashboard-tabs.gif \
       -movflags faststart \
       -pix_fmt yuv420p \
       -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
       dashboard-tabs.mp4
```

## Optimization Tips

### Lazy Loading
```html
<img src="assets/gifs/large-demo.gif" loading="lazy" decoding="async">
```

### Responsive Sizing
```html
<img src="assets/gifs/dashboard-tabs.gif"
     alt="Dashboard"
     style="max-width: 100%; height: auto;">
```

### With Fallback Image
```html
<picture>
  <source srcset="assets/gifs/cli-demo.gif" type="image/gif">
  <img src="assets/screenshots/cli/cli-status.png"
       alt="CLI Demo"
       width="800">
</picture>
```

## File Size Reference

| GIF | Size | Best For |
|-----|------|----------|
| cli-demo.gif | 0.65 MB | README, docs, quick demos |
| dashboard-search.gif | 0.68 MB | Feature highlights |
| event-stream.gif | 1.30 MB | v2.5 announcements |
| dashboard-tabs.gif | 2.12 MB | Full walkthroughs |
| graph-interaction.gif | 3.14 MB | Visual features |

All GIFs are optimized for web use and loop seamlessly.

---

**Generated:** February 12, 2026
**Copyright © 2026 Varun Pratap Bhardwaj**
