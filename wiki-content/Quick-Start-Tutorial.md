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

**What just happened:**
- Content saved to local SQLite database (`~/.claude-memory/memory.db`)
- TF-IDF vectors generated for semantic search
- Entities extracted ("FastAPI", "REST APIs")
- Pattern learning analyzed your preference for FastAPI
- Full-text search index updated

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

SuperLocalMemory works across 11+ IDEs and tools. All use the **same local database** - no data duplication.

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

## Screenshots (Coming Soon)

- Installation process
- First memory saved
- Search results with scores
- Knowledge graph visualization
- IDE integrations (Cursor, Windsurf, Claude Desktop)

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
