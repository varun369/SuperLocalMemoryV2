# CLI Terminal Screenshots

Professional terminal mockups showcasing SuperLocalMemory V2 CLI commands.

## Generated Screenshots

| File | Description | Command |
|------|-------------|---------|
| `cli-status.png` | System status check | `slm status` |
| `cli-remember.png` | Adding a new memory | `slm remember "Use FastAPI for REST APIs" --tags api --importance 7` |
| `cli-recall.png` | Searching memories | `slm recall "FastAPI"` |
| `cli-list.png` | Listing recent memories | `slm list --limit 5` |
| `cli-build-graph.png` | Building knowledge graph | `slm build-graph` |
| `cli-profile-switch.png` | Switching profiles | `slm switch-profile work` |
| `cli-help.png` | Help command | `slm --help` |

## Technical Details

- **Dimensions:** 1200x800 pixels
- **Style:** Modern light terminal (#f5f5f5 background, #2c3e50 text)
- **Font:** Menlo, Monaco, Courier New (monospace)
- **Generated via:** Playwright + HTML/CSS mockup

## Regenerating Screenshots

If you need to update the screenshots:

```bash
# Install Playwright (if not already installed)
pip install playwright
playwright install chromium

# Generate screenshots
python3 generate-screenshots.py
```

## Files

- `terminal-mockup.html` - HTML/CSS terminal emulator with all scenarios
- `generate-screenshots.py` - Playwright script to render and screenshot each scenario
- `*.png` - Generated screenshot files

## Usage in Documentation

These screenshots are used in:
- GitHub Wiki (CLI documentation)
- README.md (quick start examples)
- CONTRIBUTING.md (developer guide)
- Website marketing materials

## Style Guide

The terminal mockups follow these design principles:
- **Clean and modern**: Light background for better readability in docs
- **Professional**: macOS-style window chrome with traffic lights
- **Accessible**: High contrast text, clear hierarchy
- **Realistic**: Authentic terminal experience without requiring real shell access

---

**Generated:** 2026-02-12
**Version:** 2.5.0
