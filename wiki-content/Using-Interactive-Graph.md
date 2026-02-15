# Using the Interactive Knowledge Graph

**Added in:** v2.6.5 (February 16, 2026)

SuperLocalMemory's **Interactive Knowledge Graph** visualizes relationships between your memories using [Cytoscape.js](https://js.cytoscape.org/), the same library powering Obsidian's advanced graph plugins.

---

## Quick Start

1. **Open Dashboard**: Run `python3 ~/.claude-memory/ui_server.py` and visit http://localhost:8765
2. **Click Graph Tab**: The graph loads automatically (100 nodes by default)
3. **Explore**: Zoom (mouse wheel), pan (click-drag background), hover nodes for previews

---

## Core Interactions

| Action | How | Result |
|--------|-----|--------|
| **Zoom In/Out** | Mouse wheel or pinch (mobile) | Zoom into/out of graph |
| **Pan Canvas** | Click and drag background | Move the entire graph |
| **Hover Node** | Move mouse over a node | Shows tooltip with memory preview |
| **Click Node** | Click any node | Opens modal with full memory details + 3 actions |
| **Double-Click Node** | Double-click a node | Navigates to Memories tab and scrolls to that memory |
| **Drag Node** | Click-drag a node | Repositions node (saved to browser storage) |

---

## Modal Actions (Click Node)

When you click a node, a modal opens with 3 action buttons:

1. **View Full Memory** — Navigate to Memories tab and scroll to this memory
2. **Expand Neighbors** — Show only this node + connected nodes (local zoom)
3. **Filter to Cluster** — Show only memories in this cluster

---

## Layout Algorithms

Choose from 6 layouts using the dropdown in the Graph tab:

| Layout | Description | Best For |
|--------|-------------|----------|
| **Force-Directed (Fast)** | Nodes repel, links attract (fcose algorithm) | Default — balanced speed + quality |
| **Force-Directed (Classic)** | Traditional physics simulation (cose) | Smaller graphs (<500 nodes) |
| **Circular** | Nodes arranged in a circle by importance | Seeing importance hierarchy |
| **Grid** | Nodes in rectangular grid | Structured view, easy scanning |
| **Hierarchical** | Top-down tree layout | Parent-child relationships |
| **Concentric** | Rings by importance score | Visualizing importance levels |

**How to change:** Select from **Layout Algorithm** dropdown → graph re-renders automatically.

---

## Filtering by Cluster

**Method 1: From Clusters Tab**
1. Go to **Clusters** tab
2. Click any cluster card → Graph tab opens with that cluster filtered

**Method 2: From Graph Modal**
1. Click any node in graph → modal opens
2. Click **"Filter to Cluster X"** button → graph filters to that cluster

**Method 3: From URL**
- Add `?cluster_id=2` to URL → graph auto-filters on page load
- Example: `http://localhost:8765?cluster_id=2`

**Clear Filters:** Click **Clear** button in Graph tab (top-right).

---

## Filtering by Entity

**From Clusters Tab:**
1. Go to **Clusters** tab
2. Click any entity badge (e.g., "code (6)") → Graph shows memories with that entity

---

## Performance Tiers (Automatic)

SuperLocalMemory automatically optimizes graph rendering based on node count:

| Nodes | Strategy | Details |
|-------|----------|---------|
| **0-500** | Full graph | All features enabled, smooth interactions |
| **501-2000** | Cluster aggregation | Shows 1 node per cluster, click to expand |
| **2001+** | Focus mode | Shows 1 cluster at a time, use "Jump to Cluster" dropdown |

**Why?** Rendering 10,000+ nodes at once would lag. The 3-tier strategy keeps interactions smooth.

---

## Visual Styling

**Nodes:**
- **Color** = Cluster (same colors as Clusters tab)
- **Size** = Importance score (1-10 → larger nodes = more important)
- **Border** = Trust score (v2.5 feature)

**Edges (Links):**
- **Thickness** = Relationship strength (TF-IDF similarity)
- **Solid line** = Strong relationship (>0.3 similarity)
- **Dashed line** = Weak relationship (<0.3 similarity)

**Highlight on Hover:**
- Hovered node + connected nodes → **highlighted**
- Unconnected nodes → **dimmed** (focus mode)

---

## Keyboard Shortcuts

_(Planned for v2.6.6)_
- Arrow keys: Pan graph
- `+` / `-`: Zoom in/out
- `F`: Fit graph to viewport
- `Esc`: Clear filters

---

## Tips & Tricks

1. **Save Custom Layouts**: Drag nodes to preferred positions → layout auto-saves to browser storage
2. **Find Hidden Connections**: Hover nodes to highlight relationships you didn't know existed
3. **Cluster Exploration**: Start with Clusters tab to understand graph structure, then dive into Graph
4. **URL Bookmarks**: Bookmark `?cluster_id=X` URLs for quick access to important clusters
5. **Performance**: If graph feels slow, reduce node count (dropdown) or clear filters

---

## Troubleshooting

**Graph not loading?**
- Check browser console (F12) for errors
- Ensure `ui_server.py` is running
- Try refreshing (click Refresh button in Graph tab)

**Graph looks cluttered?**
- Reduce node count (use dropdown: 50/100/200 nodes)
- Apply cluster filter (click a cluster card)
- Try different layout (Circular or Grid for structure)

**Nodes won't drag?**
- Ensure you're dragging the node, not the background
- Check browser console for JavaScript errors

**Filters not working?**
- Click **Clear** button first, then re-apply filter
- Check if URL parameter `?cluster_id=X` is set (remove if not wanted)

---

## Technical Details

**Library:** [Cytoscape.js](https://js.cytoscape.org/) v3.30.4
**Renderer:** Canvas (WebGL for 1000+ nodes)
**File:** `ui/js/graph-cytoscape.js` (650 lines — scheduled for refactor in v2.6.6)
**Performance:** < 3s load time for 10K nodes, > 30 FPS interaction

---

## Coming in v2.6.6

- **Modular Refactor**: Split monolithic graph file into 4 clean modules
- **Keyboard Navigation**: Arrow keys, zoom shortcuts, ESC to clear
- **Sidebar Memory List**: Click "X memories" badge → view list without leaving graph
- **Search in Graph**: Filter nodes by text search
- **Minimap**: Bird's-eye view of large graphs

---

## Feedback

Found a bug? Have a feature request? Open an issue:
https://github.com/varun369/SuperLocalMemoryV2/issues

---

**Related Pages:**
- [Clusters](Clusters.md) — Understanding graph clusters
- [Performance Benchmarks](Performance-Benchmarks.md) — Graph rendering speeds
- [Architecture](Architecture.md) — How the knowledge graph works

---

*Page created: February 16, 2026*
*SuperLocalMemory v2.6.5*
