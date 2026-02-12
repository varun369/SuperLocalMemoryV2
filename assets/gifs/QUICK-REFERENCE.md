# Quick Reference - GIF Usage

## Where to Use Each GIF

### cli-demo.gif (0.65 MB)
**Best for:** README, CLI docs, Twitter/LinkedIn
```markdown
![CLI Demo](assets/gifs/cli-demo.gif)
```

### dashboard-search.gif (0.68 MB)
**Best for:** Feature highlights, documentation
```markdown
![Search & Filter](assets/gifs/dashboard-search.gif)
```

### graph-interaction.gif (3.14 MB)
**Best for:** Visual features, presentations
```markdown
![Knowledge Graph](assets/gifs/graph-interaction.gif)
```

### event-stream.gif (1.30 MB)
**Best for:** v2.5 announcements, Event Bus docs
```markdown
![Real-Time Events](assets/gifs/event-stream.gif)
```

### dashboard-tabs.gif (2.12 MB)
**Best for:** Full walkthroughs, hero sections
```markdown
![Dashboard Overview](assets/gifs/dashboard-tabs.gif)
```

## One-Line Embeds

### GitHub README (relative path)
```markdown
![Demo](assets/gifs/cli-demo.gif)
```

### GitHub Wiki (raw URL)
```markdown
![Demo](https://raw.githubusercontent.com/varun369/SuperLocalMemoryV2/main/assets/gifs/cli-demo.gif)
```

### Website (Astro)
```html
<img src="/assets/gifs/dashboard-tabs.gif" alt="Dashboard" width="1400">
```

### Responsive
```html
<img src="assets/gifs/cli-demo.gif" alt="CLI" style="max-width: 100%; height: auto;">
```

## Regenerate

```bash
python3 tools/create_gifs.py
python3 tools/optimize_gifs.py
```

---

**Quick tip:** All GIFs loop seamlessly and are web-optimized.
