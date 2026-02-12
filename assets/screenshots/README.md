# SuperLocalMemory V2 - Screenshot Documentation

This directory contains official screenshots of the SuperLocalMemory V2 dashboard and features.

## Annotated Screenshots

Professional annotations highlighting key features (added for v2.5.0 release):

### 1. Dashboard Overview (`dashboard-overview-annotated.png`)
**Annotations:**
- **Real-time statistics** - Arrow pointing to the stats cards at the top showing Total Memories, Clusters, Graph Nodes, and Connections
- **NEW in v2.5** - Box highlighting the "Live Events" tab, which is a new feature in version 2.5

**Features shown:**
- Real-time memory statistics
- Knowledge graph visualization
- Force-directed layout with semantic clustering
- Tab navigation (Knowledge Graph, Memories, Clusters, Patterns, Timeline, Live Events, Agents, Settings)

### 2. Live Events Stream (`dashboard-live-events-annotated.png`)
**Annotations:**
- **Real-time memory operations** - Arrow pointing to the live event stream showing memory operations as they happen
- **Color-coded events** - Box highlighting the event type badges (memory_created, memory_deleted) with different colors

**Features shown:**
- Real-time event stream with timestamps
- Event type badges (create, delete, read operations)
- Event statistics (Total Events, Last 24h, Listeners, In Buffer)
- Connected/All Events filter
- Event details with memory content

### 3. Connected Agents (`dashboard-agents-annotated.png`)
**Annotations:**
- **Agent trust scoring** - Arrow pointing to the Trust column showing agent reliability scores (1.00 = perfect trust)
- **MCP/A2A support** - Box highlighting the protocol badges showing which communication protocol each agent uses

**Features shown:**
- Agent registry with connection status
- Protocol identification (MCP, Python, A2A)
- Trust scoring system (v2.5 silent collection, v2.6 enforcement)
- Agent activity metrics (Writes, Recalls, Last Seen)
- Signal breakdown showing agent behavior patterns
- Trust scoring status (Silent Collection in v2.5)

### 4. Knowledge Graph (`dashboard-graph-annotated.png`)
**Annotations:**
- **Semantic clusters** - Arrow pointing to a cluster of related memory nodes (color-coded by cluster)
- **Interactive graph visualization** - Label describing the force-directed graph layout

**Features shown:**
- Force-directed knowledge graph with D3.js
- Hierarchical Leiden clustering (Layer 3)
- Color-coded semantic clusters
- Interactive node exploration
- Relationship visualization (links show semantic similarity)
- Refresh and node count controls

### 5. Memory Browser (`dashboard-memories-annotated.png`)
**Annotations:**
- **Hybrid search (TF-IDF + FTS5 + Graph)** - Arrow pointing to the search box that combines three search methods
- **Advanced filters** - Box highlighting the filter panel with Category, Project, All Projects dropdowns

**Features shown:**
- Hybrid search combining TF-IDF, FTS5 full-text, and graph traversal
- Advanced filtering (Category, Project, Tags)
- Memory list with importance scores
- Content preview with truncation
- Memory metadata (cluster, created date)
- Bulk operations (Export, Filter buttons)

## Clean (Un-annotated) Screenshots

Original screenshots without annotations are also available:
- `dashboard-overview.png`
- `dashboard-live-events.png`
- `dashboard-agents.png`
- `dashboard-graph.png`
- `dashboard-memories.png`
- Additional variants: `dashboard-clusters.png`, `dashboard-patterns.png`, `dashboard-timeline.png`, `dashboard-filtered.png`

## Dark Mode Variants

Dark theme screenshots available:
- `dashboard-overview-dark.png`
- `dashboard-live-events-dark.png`
- `dashboard-memories-dark.png`

## Annotation Style Guide

All annotations follow these standards:
- **Arrows:** Red (#FF0000), 3px width, vector-style with arrow heads
- **Boxes:** Red border (#FF0000), 2px width, no fill
- **Labels:** White background (#FFFFFF), black text (#000000), 14px font, rounded corners (6px radius)
- **Purpose:** Minimal, professional annotations highlighting key features only

## Regenerating Annotations

To regenerate annotated screenshots:

```bash
# From repo root
python3 annotate_screenshots.py
```

The script will:
1. Load original screenshots from `assets/screenshots/dashboard/`
2. Add arrows, boxes, and labels programmatically
3. Save annotated versions with `-annotated` suffix
4. Preserve original clean versions

## Usage in Documentation

**For GitHub README, website, and marketing:**
- Use annotated versions to highlight features for new users
- Use clean versions for professional documentation and technical guides
- Use dark mode versions to show theme support

**Best practices:**
- Link to full-size images (these are high-resolution 4K screenshots)
- Provide context about what each screenshot demonstrates
- Keep annotations minimal - only highlight what's truly important
- Update annotations when UI changes significantly

## Technical Details

- **Resolution:** 3840x2160 (4K) for crisp display on high-DPI screens
- **Format:** PNG with RGB color mode (converted from original palette mode for annotation compatibility)
- **Tool:** PIL/Pillow for programmatic annotation
- **Source:** Screenshots captured from live dashboard running on localhost:8765

---

**Last Updated:** February 12, 2026 (v2.5.0 release)
**Annotations Added By:** Varun Pratap Bhardwaj (automated via annotate_screenshots.py)
