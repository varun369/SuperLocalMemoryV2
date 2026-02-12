# Quick Start Tutorial

**Your first memory in 2 minutes** - Get started with SuperLocalMemory V2's intelligent local memory system for AI coding assistants.

---

## Prerequisites

Before starting, ensure you have:
- Python 3.8 or higher installed (`python3 --version`)
- Git installed (for cloning repository)
- 5 minutes of time

**Already installed?** Skip to [Your First Memory](#your-first-memory).

---

## Installation (60 seconds)

### Mac/Linux

```bash
# Clone repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2

# Install
./install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2
.\install.ps1
```

**What happens during installation:**
1. Creates `~/.claude-memory/` directory
2. Initializes SQLite database
3. Auto-detects installed IDEs (Cursor, Windsurf, Claude Desktop, VS Code)
4. Configures MCP server for detected tools
5. Installs CLI wrapper (`slm` command)
6. Sets up shell completions (bash/zsh)

**Verify installation:**
```bash
slm status
```

**Expected output:**
```
✓ Database: OK (0 memories)
✓ Knowledge Graph: Ready
✓ Pattern Learning: Ready
✓ Current Profile: default
```

![CLI Status Output](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-status.png)
*Figure 1: The `slm status` command shows system health and database statistics*

For detailed installation troubleshooting, see the [Installation Guide](Installation).

---

## Your First Memory

### Step 1: Save Your First Memory

```bash
slm remember "We use FastAPI for REST APIs in this project"
```

**Output:**
```
Memory added with ID: 1

✅ Memory saved successfully

Next steps:
  • Use `slm recall <query>` to search this memory
  • Use `slm list` to see recent memories
```

![CLI Remember Command](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-remember.png)
*Figure 2: Saving your first memory with the `slm remember` command*

**What just happened:**
- Content saved to local SQLite database (`~/.claude-memory/memory.db`)
- TF-IDF vectors generated for semantic search
- Entities extracted ("FastAPI", "REST APIs")
- Pattern learning analyzed your preference for FastAPI
- Full-text search index updated

![CLI Demo](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/cli-demo.gif)
*Interactive demo: Watch how memories are saved and recalled in real-time*

### Step 2: Add More Context

```bash
slm remember "JWT tokens expire after 24 hours" --tags security,auth,jwt
```

**With tags** for better organization:
- Helps filtering
- Improves search relevance
- Enables tag-based queries

### Step 3: Add Project-Specific Memory

```bash
slm remember "Database uses PostgreSQL 15 with UUID primary keys" --project myapp --tags database,postgresql
```

**Project isolation** prevents context bleeding between different codebases.

### Step 4: Add Important Information

```bash
slm remember "CRITICAL: Production deploys require approval from @lead" --importance 10 --tags deployment,production
```

**Importance levels (1-10):**
- 1-3: Low priority (notes, ideas)
- 4-6: Normal (coding patterns, decisions)
- 7-9: High priority (critical info, warnings)
- 10: Critical (blockers, security issues)

---

## Search Your Memories

### Basic Search

```bash
slm recall "FastAPI"
```

**Output:**
```
🔍 Search Results (1 found)

[ID: 1] Score: 0.95
We use FastAPI for REST APIs in this project
Tags: -
Project: default
Created: 2026-02-07 14:23
```

![CLI Recall Results](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-recall.png)
*Figure 3: Search results showing relevance scores and memory metadata*

**Three search methods working simultaneously:**
1. **Semantic Search (TF-IDF)** - Finds conceptually similar content
2. **Knowledge Graph** - Discovers related memories via graph edges
3. **Full-Text Search (FTS5)** - Exact keyword matching

### Advanced Search

```bash
# Limit results
slm recall "authentication" --limit 3

# Filter by relevance score
slm recall "React hooks" --min-score 0.7

# Filter by tags
slm recall "database" --tags postgresql,performance

# Filter by project
slm recall "API design" --project myapp
```

See the [CLI Cheatsheet](CLI-Cheatsheet) for all search options.

---

## List Recent Memories

```bash
slm list --limit 10
```

**Output:**
```
📋 Recent Memories (3 total)

[ID: 3] CRITICAL: Production deploys require approval from @lead
Tags: deployment, production
Project: default
Created: 2026-02-07 14:25

[ID: 2] JWT tokens expire after 24 hours
Tags: security, auth, jwt
Project: default
Created: 2026-02-07 14:24

[ID: 1] We use FastAPI for REST APIs in this project
Tags: -
Project: default
Created: 2026-02-07 14:23
```

![CLI List Output](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-list.png)
*Figure 4: The `slm list` command displays recent memories with tags and metadata*

---

## Build Knowledge Graph

After adding several memories, build the knowledge graph to discover relationships:

```bash
slm build-graph
```

**Output:**
```
🔄 Building Knowledge Graph...

Phase 1: Entity Extraction
  Scanning 3 memories...
  Extracted 15 unique entities
  Created 15 graph nodes
  ✓ Complete (0.1s)

Phase 2: Relationship Discovery
  Computing similarity scores...
  Created 8 edges (relationships)
  Avg edges per node: 0.5
  ✓ Complete (0.2s)

✅ Knowledge graph built successfully!

Graph Statistics:
  Nodes: 15
  Edges: 8
  Density: 0.37%
```

![CLI Build Graph](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-build-graph.png)
*Figure 5: Building the knowledge graph discovers relationships between memories*

**Why build the graph:**
- Improves search quality
- Discovers hidden relationships
- Enables graph-enhanced recall
- Creates topic clusters

Learn more in the [Knowledge Graph Guide](Knowledge-Graph-Guide).

---

## Check System Status

```bash
slm status
```

**Output:**
```
📊 SuperLocalMemory V2 Status

Database:
  Total memories: 3
  Database size: 12 KB
  Location: /Users/username/.claude-memory/memory.db

Knowledge Graph:
  Nodes: 15
  Edges: 8
  Clusters: 0 (run with --clustering to enable)

Pattern Learning:
  Learned patterns: 2
  Confidence threshold: 0.5

Current Profile: default
```

---

## Use Across Different Tools

SuperLocalMemory works across 16+ IDEs and tools. All use the **same local database** - no data duplication.

### In Cursor (MCP Integration)

After installation, Cursor automatically detects SuperLocalMemory.

**Usage in Cursor:**
```
You: "Remember that we use FastAPI for REST APIs"
AI: [Automatically invokes memory tools]
✓ Memory saved

You: "What did we decide about APIs?"
AI: [Searches memories]
Found: "We use FastAPI for REST APIs in this project"
```

### In Claude Code (Skills)

```bash
# Use skills directly
/slm-remember "content"
/slm-recall "query"
/slm-list-recent
/slm-status
```

### In VS Code with Continue.dev

```bash
# Slash commands
/slm-remember "content"
/slm-recall "query"
```

### In Any Terminal

```bash
# Universal CLI works everywhere
slm remember "content"
slm recall "query"
slm list
slm status
```

See [Multi-Profile Workflows](Multi-Profile-Workflows) for advanced usage.

---

## Step 5: Explore Dashboard (NEW v2.2.0)

**NEW:** SuperLocalMemory V2.2.0 includes an interactive web dashboard for visual exploration.

### Launch Dashboard

```bash
# Start the visualization dashboard
python ~/.claude-memory/ui_server.py

# Opens at: http://localhost:8765
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════════╗
║  SuperLocalMemory V2.2.0 - Visualization Dashboard           ║
╚══════════════════════════════════════════════════════════════╝

✓ Database loaded: 3 memories
✓ Knowledge graph loaded: 1 cluster, 15 entities
✓ Pattern data loaded: 2 learned patterns

🌐 Dashboard running at: http://localhost:8765
```

![Dashboard Overview](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-overview.png)
*Figure 6: The web dashboard provides visual exploration of your memory system*

![Dashboard Navigation](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/dashboard-tabs.gif)
*Interactive navigation: Explore Timeline, Search, Graph, and Statistics views*

### Explore Four Views

**1. Timeline View**
```
Navigate to: Timeline tab
See: All 3 memories chronologically
Features:
  - Color-coded by importance
  - Cluster badges
  - Click to expand
  - Filter by date range
```

**2. Search Explorer**
```
Navigate to: Search tab
Type: "FastAPI"
See: Real-time results with score bars
Features:
  - Live search (updates as you type)
  - Visual relevance scores (0-100%)
  - Strategy toggle (semantic/exact/graph/hybrid)
  - Advanced filters
```

**3. Graph Visualization**
```
Navigate to: Graph tab
See: Interactive knowledge graph
Features:
  - Zoom and pan
  - Click clusters to explore
  - Hover for details
  - Drag nodes to rearrange
```

![Knowledge Graph Visualization](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-graph.png)
*Figure 7: Interactive graph view shows relationships between memories and entities*

![Graph Interaction](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/graph-interaction.gif)
*Click, drag, and explore the knowledge graph in real-time*

**4. Statistics Dashboard**
```
Navigate to: Statistics tab
See: Memory trends and analytics
Features:
  - Memory trends (line chart)
  - Tag cloud
  - Importance distribution
  - Pattern confidence scores
```

![Dashboard Timeline View](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-timeline.png)
*Figure 8: Timeline view displays memories chronologically with importance indicators*

### Dashboard Features

| Feature | Benefit |
|---------|---------|
| **Real-time updates** | Changes via CLI appear immediately |
| **Dark mode** | Toggle in top-right corner |
| **Keyboard shortcuts** | `Ctrl+1/2/3/4` for views, `Ctrl+F` for search |
| **Responsive design** | Works on desktop, tablet, mobile |
| **Export options** | Download results as JSON/CSV/PDF |

### Install Dashboard Dependencies (If Needed)

```bash
# If dashboard fails to start
pip install dash plotly pandas networkx

# Or from requirements
pip install -r ~/.claude-memory/requirements-dashboard.txt
```

### Use Cases with Dashboard

**Daily Context Refresh:**
```
1. Open dashboard (http://localhost:8765)
2. Timeline view → Filter: Last 7 days
3. Scan memories chronologically
4. Export as text for AI assistant
Time: 2 minutes
```

**Discover Patterns:**
```
1. Statistics tab
2. View tag cloud
3. See most frequent topics
4. Analyze pattern confidence
Time: 3 minutes
```

**Explore Relationships:**
```
1. Graph tab
2. Click "Authentication" cluster
3. See all related memories
4. Discover connections
Time: 5 minutes
```

**[[Complete Dashboard Guide →|Visualization-Dashboard]]**

---

## Next Steps

Congratulations! You've completed the quick start tutorial.

### Explore Advanced Features

1. **[Multi-Profile Workflows](Multi-Profile-Workflows)** - Separate work/personal contexts
2. **[Knowledge Graph Guide](Knowledge-Graph-Guide)** - Deep dive into graph features
3. **[Pattern Learning](Pattern-Learning-Explained)** - How SuperLocalMemory learns your style
4. **[CLI Cheatsheet](CLI-Cheatsheet)** - Complete command reference
5. **[Python API](Python-API)** - Programmatic access

### Common Use Cases

- **Daily Standups**: `slm recall "decided" --limit 5`
- **Code Reviews**: `slm remember "Code review feedback: Use async/await consistently" --tags codereview`
- **Bug Tracking**: `slm remember "Bug: JWT tokens expire too fast" --tags bug --importance 8`
- **Architecture Decisions**: `slm remember "ADR: Use microservices over monolith" --tags architecture --importance 9`

### Get Help

- **Issues**: [GitHub Issues](https://github.com/varun369/SuperLocalMemoryV2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/varun369/SuperLocalMemoryV2/discussions)
- **Wiki**: [Complete Documentation](https://github.com/varun369/SuperLocalMemoryV2/wiki)

---

## Visual Gallery

### Command Line Interface

<table>
<tr>
<td width="50%">

![Status Command](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-status.png)
*System status showing memory count and graph statistics*

</td>
<td width="50%">

![Remember Command](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-remember.png)
*Saving a new memory with automatic entity extraction*

</td>
</tr>
<tr>
<td width="50%">

![Recall Command](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-recall.png)
*Search results with relevance scores and metadata*

</td>
<td width="50%">

![List Command](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-list.png)
*Recent memories organized chronologically*

</td>
</tr>
<tr>
<td width="50%">

![Build Graph](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-build-graph.png)
*Knowledge graph construction with entity extraction*

</td>
<td width="50%">

![Profile Switch](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-profile-switch.png)
*Multi-profile support for context isolation*

</td>
</tr>
</table>

### Web Dashboard (v2.2.0+)

<table>
<tr>
<td width="50%">

![Dashboard Overview](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-overview.png)
*Main dashboard with memory statistics and quick actions*

</td>
<td width="50%">

![Memory Browser](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-memories.png)
*Browse and filter memories with advanced search*

</td>
</tr>
<tr>
<td width="50%">

![Knowledge Graph](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-graph.png)
*Interactive graph visualization with zoom and pan*

</td>
<td width="50%">

![Cluster View](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-clusters.png)
*Explore memory clusters and topic relationships*

</td>
</tr>
<tr>
<td width="50%">

![Pattern Learning](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-patterns.png)
*View learned patterns and confidence scores*

</td>
<td width="50%">

![Filtered Results](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/dashboard/dashboard-filtered.png)
*Advanced filtering by tags, projects, and importance*

</td>
</tr>
</table>

### NEW in v2.5: Live Events & Agent Tracking

<table>
<tr>
<td width="50%">

![Live Events Stream](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/v25/v25-live-events-working.png)
*Real-time event stream showing memory operations across all agents*

</td>
<td width="50%">

![Agents Tab](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/v25/v25-agents-tab.png)
*Track active AI agents and their memory access patterns*

</td>
</tr>
</table>

**v2.5 Features (Released Feb 2026):**
- **Event Bus**: Real-time memory operation broadcasting via WebSocket/SSE
- **Agent Registry**: Track which AI assistants are accessing your memories
- **Provenance Tracking**: Know which agent created each memory (CLI, Cursor, Claude, etc.)
- **Trust Scoring**: Silent collection of agent behavior patterns
- **Live Dashboard**: Watch memory operations happen in real-time

![Event Stream Demo](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/event-stream.gif)
*Watch memories flow through the system in real-time with the Event Bus*

### Interactive Demos

![CLI Demo](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/cli-demo.gif)
*Complete CLI workflow: remember → recall → list → build-graph*

![Dashboard Search](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/dashboard-search.gif)
*Real-time search with instant results and relevance scoring*

![Graph Interaction](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/graph-interaction.gif)
*Explore the knowledge graph: click, drag, and discover connections*

![Dashboard Tabs](https://varun369.github.io/SuperLocalMemoryV2/assets/gifs/dashboard-tabs.gif)
*Navigate between Timeline, Search, Graph, and Statistics views*

---

## Troubleshooting

### "slm: command not found"

**Solution:**
```bash
# Restart your shell
exec $SHELL

# Or manually add to PATH
echo 'export PATH="$HOME/.claude-memory/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### "Database not found"

**Solution:**
```bash
# Verify installation
ls -la ~/.claude-memory/memory.db

# If missing, reinstall
cd SuperLocalMemoryV2
./install.sh
```

### "No memories found" after saving

**Solution:**
```bash
# Check database
sqlite3 ~/.claude-memory/memory.db "SELECT COUNT(*) FROM memories;"

# If 0, check write permissions
chmod 755 ~/.claude-memory/
chmod 644 ~/.claude-memory/memory.db
```

For more troubleshooting, see the [Configuration](Configuration) guide.

---

## Summary

You've learned how to:
- ✅ Install SuperLocalMemory V2
- ✅ Save your first memory
- ✅ Search memories semantically
- ✅ List recent memories
- ✅ Build knowledge graph
- ✅ Check system status
- ✅ Use across different tools

**100% local. 100% private. 100% yours.**

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
