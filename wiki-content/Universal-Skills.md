# Universal Skills

SuperLocalMemory V2.1.0 includes **6 universal agent-skills** that work as slash-commands in Claude Code, Continue.dev, and Cody. These ai-skills provide a consistent interface across different AI assistants while accessing the same local memory database.

**Keywords:** agent-skills, slash-commands, ai-skills, claude-code, continue-dev, cody

---

## 🎯 What Are Skills?

**Skills** are command-based interfaces for AI assistants that don't support MCP (Model Context Protocol) natively. They provide the same functionality as MCP tools but through a slash-command interface.

### Key Benefits

- **Consistent Interface** - Same commands work across multiple IDEs
- **No MCP Required** - Works with any tool that supports commands
- **Local Execution** - Everything runs on your machine
- **Single Database** - Uses the same SQLite database as MCP and CLI

---

## 📦 The 6 Universal Skills

All skills use the `slm-*` prefix for consistency:

| Skill | Purpose | Usage |
|-------|---------|-------|
| **slm-remember** | Save content to memory | `/slm-remember "content" --tags work,api` |
| **slm-recall** | Search memories | `/slm-recall "authentication"` |
| **slm-list-recent** | Display recent memories | `/slm-list-recent 10` |
| **slm-status** | System health and stats | `/slm-status` |
| **slm-build-graph** | Rebuild knowledge graph | `/slm-build-graph` |
| **slm-switch-profile** | Change active profile | `/slm-switch-profile work` |

---

## 🚀 Installation

### Automatic Installation

The `install-skills.sh` script automatically detects and configures skills for supported IDEs:

```bash
cd SuperLocalMemoryV2
./install-skills.sh
```

**Auto-detects:**
- Claude Code (native skills)
- Continue.dev (VS Code)
- Cody (VS Code/JetBrains)

**What it does:**
1. Detects installed IDEs
2. Backs up existing configurations
3. Merges skill definitions
4. Creates necessary directories
5. Sets correct permissions

### Manual Installation

If you need to manually install skills:

**Claude Code:**
```bash
cp -r skills/* ~/.claude/skills/
```

**Continue.dev:**
```bash
# Edit .continue/config.yaml and add skills
```

**Cody:**
```bash
# Edit VS Code settings.json or JetBrains Cody config
```

---

## 📖 Skill Documentation

### 1. slm-remember

**Save content to memory with automatic indexing.**

#### Usage

```bash
# Basic
/slm-remember "We use FastAPI for all REST APIs"

# With tags
/slm-remember "JWT tokens expire after 24 hours" --tags security,auth,jwt

# With project
/slm-remember "Database uses PostgreSQL 15" --project myapp --tags database

# With importance (1-10)
/slm-remember "CRITICAL: Production deploy requires approval" --importance 10
```

#### Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<content>` | string | Yes | - | Text to remember |
| `--tags` | string | No | None | Comma-separated tags |
| `--project` | string | No | "default" | Project name |
| `--importance` | integer | No | 5 | Priority level (1-10) |

#### What Happens

1. **Content Saved** - Stored in SQLite database
2. **Entities Extracted** - TF-IDF identifies key terms
3. **Graph Updated** - Entities added to knowledge graph
4. **Patterns Learned** - Analyzes for coding preferences
5. **ID Returned** - Memory ID for future reference

#### Example Output

```
✓ Memory added with ID: 42
  Tags: security, auth, jwt
  Project: myapp
  Importance: 7
  Entities extracted: 3 (JWT, tokens, authentication)
```

---

### 2. slm-recall

**Search memories using semantic search and full-text search.**

#### Usage

```bash
# Basic search
/slm-recall "authentication"

# Search with limit
/slm-recall "database query" --limit 5

# Search by tag
/slm-recall "performance" --tags optimization

# Search by project
/slm-recall "api" --project myapp
```

#### Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<query>` | string | Yes | - | Search query |
| `--limit` | integer | No | 10 | Max results |
| `--tags` | string | No | None | Filter by tags |
| `--project` | string | No | Current | Filter by project |

#### Search Methods

1. **Semantic Search** - TF-IDF vector similarity
2. **Full-Text Search** - SQLite FTS5 for exact matches
3. **Knowledge Graph** - Related memories via clustering
4. **Pattern Context** - Considers learned preferences

#### Example Output

```
Found 3 memories:

[1] ID: 42 (Score: 0.87)
    "Implemented JWT authentication with 24-hour expiry"
    Tags: security, auth, jwt
    Created: 2026-02-01
    Cluster: "Authentication & Security"

[2] ID: 15 (Score: 0.65)
    "OAuth2 integration for Google login"
    Tags: auth, oauth, security
    Created: 2026-01-28
    Cluster: "Authentication & Security"

[3] ID: 8 (Score: 0.52)
    "Added CSRF protection middleware"
    Tags: security, middleware
    Created: 2026-01-25
    Cluster: "Security Patterns"
```

---

### 3. slm-list-recent

**Display recent memories with metadata.**

#### Usage

```bash
# Show 10 most recent
/slm-list-recent

# Show 20 most recent
/slm-list-recent 20

# Filter by project
/slm-list-recent 10 --project work
```

#### Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<limit>` | integer | No | 10 | Number of memories |
| `--project` | string | No | Current | Filter by project |

#### Example Output

```
Recent Memories (10):

[1] ID: 47 - 2 hours ago
    "Added Redis caching for API responses"
    Tags: performance, caching, redis

[2] ID: 46 - 5 hours ago
    "Fixed authentication bug in login flow"
    Tags: bugfix, auth

[3] ID: 45 - 1 day ago
    "Implemented rate limiting middleware"
    Tags: security, api
```

---

### 4. slm-status

**System health, statistics, and diagnostics.**

#### Usage

```bash
# Show all stats
/slm-status

# Brief status
/slm-status --brief
```

#### Example Output

```
╔══════════════════════════════════════════════════════════════╗
║  SuperLocalMemory V2.1.0 - System Status                     ║
╚══════════════════════════════════════════════════════════════╝

✓ Database: OK
  - Total memories: 47
  - Database size: 2.3 MB
  - Current profile: default
  - Profiles: 3 (default, work, personal)

✓ Knowledge Graph:
  - Clusters: 8
  - Total entities: 156
  - Average cluster size: 5.8 memories
  - Last build: 2 hours ago

✓ Pattern Learning:
  - Learned patterns: 12
  - High-confidence patterns: 5
  - Framework preferences: React (73%), FastAPI (68%)
  - Last update: 30 minutes ago

✓ Storage:
  - Tier 1 (full): 45 memories
  - Tier 2 (compressed): 2 memories
  - Tier 3 (archived): 0 memories
  - Space savings: 5%

System: Healthy
```

---

### 5. slm-build-graph

**Rebuild knowledge graph with Leiden clustering.**

#### Usage

```bash
# Build/rebuild graph
/slm-build-graph

# Build with custom resolution
/slm-build-graph --resolution 1.5
```

#### What It Does

1. **Entity Extraction** - TF-IDF identifies important terms
2. **Similarity Calculation** - Cosine similarity between memories
3. **Graph Construction** - Create edges for similar memories
4. **Clustering** - Leiden algorithm finds communities
5. **Auto-Naming** - Generate descriptive cluster names

#### Example Output

```
Building knowledge graph...

✓ Processed 47 memories
✓ Extracted 156 entities
✓ Created 89 edges (similarity > 0.3)
✓ Detected 8 clusters:

Cluster 1: "Authentication & Security" (12 memories)
  - Top entities: JWT (8), OAuth (5), tokens (7), session (6)

Cluster 2: "Performance Optimization" (8 memories)
  - Top entities: caching (6), Redis (5), performance (8), speed (4)

Cluster 3: "React Components" (11 memories)
  - Top entities: React (11), components (9), hooks (7), state (6)

...

Graph build completed in 2.3 seconds.
```

---

### 6. slm-switch-profile

**Change active memory profile for context isolation.**

#### Usage

```bash
# Switch to work profile
/slm-switch-profile work

# Switch to personal profile
/slm-switch-profile personal

# Create and switch to new profile
/slm-switch-profile client-acme --create
```

#### Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<profile>` | string | Yes | - | Profile name |
| `--create` | flag | No | False | Create if doesn't exist |

#### Profile Benefits

- **Isolated Contexts** - Separate memories per profile
- **No Context Bleeding** - Work/personal/client memories separate
- **Independent Graphs** - Each profile has its own knowledge graph
- **Separate Patterns** - Different learned preferences per profile

#### Example Output

```
Switching to profile: work

✓ Profile loaded: work
  - Total memories: 142
  - Knowledge clusters: 15
  - Learned patterns: 8
  - Last used: 3 hours ago

Profile 'work' is now active.
```

---

## 🔧 IDE-Specific Usage

### Claude Code

**Native skills support** - Skills appear in command palette.

```bash
# Type / to see all skills
/slm-remember "content"
/slm-recall "query"
```

**Features:**
- Auto-completion
- Inline help
- Syntax highlighting

---

### Continue.dev (VS Code)

**Slash commands** - Skills work as custom commands.

**Setup:**
```bash
./install-skills.sh  # Auto-configures Continue
```

**Usage:**
```bash
# In Continue chat panel
/slm-remember "We use TypeScript for all frontend code"
/slm-recall "typescript configuration"
```

**Features:**
- Tab completion
- Command history
- Integration with VS Code tasks

---

### Cody (VS Code/JetBrains)

**Custom commands** - Skills as Cody commands.

**Setup:**
```bash
./install-skills.sh  # Auto-configures Cody
```

**Usage:**
```bash
# In Cody chat
/slm-remember "Added logging middleware"
/slm-status
```

**Features:**
- Command suggestions
- Context menu integration
- JetBrains and VS Code support

---

## 🏗️ Skills Architecture

### Metadata-First Design

Each skill includes a `SKILL.md` file with complete metadata:

```yaml
---
name: slm-remember
description: Save content to SuperLocalMemory
version: "2.1.0"
license: MIT
compatibility: "Requires SuperLocalMemory V2 installed"
attribution:
  creator: Varun Pratap Bhardwaj
  role: Solution Architect & Original Creator
  project: SuperLocalMemory V2
---
```

### Directory Structure

```
skills/
├── slm-remember/
│   ├── SKILL.md          # Metadata and documentation
│   ├── main.py           # Skill implementation
│   └── examples/         # Usage examples
├── slm-recall/
│   ├── SKILL.md
│   ├── main.py
│   └── examples/
└── ...
```

### Benefits

- **Version Tracking** - Each skill has semantic versioning
- **Attribution Preserved** - Creator info in every skill
- **Self-Documenting** - Complete docs in SKILL.md
- **IDE Agnostic** - Same structure works everywhere

---

## 🔄 Skills vs MCP vs CLI

All three access methods use the **same SQLite database**:

| Feature | Skills | MCP | CLI |
|---------|--------|-----|-----|
| **Interface** | Slash commands | AI tools | Terminal commands |
| **Best For** | Claude/Continue/Cody | Modern IDEs | Scripts/Terminals |
| **Requires** | IDE with commands | MCP support | Any shell |
| **Setup** | `install-skills.sh` | Auto in `install.sh` | Auto in `install.sh` |
| **Database** | `~/.claude-memory/memory.db` | Same | Same |

**Example - Same Operation, Three Ways:**

```bash
# Skills (Claude Code)
/slm-remember "We use FastAPI"

# MCP (Cursor)
"Remember that we use FastAPI"

# CLI (Terminal)
slm remember "We use FastAPI"
```

All three save to the **same memory**, queryable by all methods.

---

## 🐛 Troubleshooting

### Skills Not Showing Up

**Claude Code:**
1. Check `~/.claude/skills/` directory exists
2. Verify skill directories are present
3. Restart Claude Code
4. Type `/` to see command list

**Continue.dev:**
1. Check `.continue/config.yaml` has skills defined
2. Reload VS Code window (Cmd+Shift+P → "Reload Window")
3. Open Continue panel
4. Type `/` to see commands

**Cody:**
1. Check VS Code settings.json has `cody.customCommands`
2. Reload VS Code
3. Open Cody chat
4. Type `/` for commands

### "Skill Not Found" Error

**Solution:** Reinstall skills:
```bash
cd SuperLocalMemoryV2
./install-skills.sh --force
```

### "Permission Denied"

**Solution:** Fix permissions:
```bash
chmod +x ~/.claude-memory/skills/*/main.py
```

### Skills Return No Data

**Solution:** Check database:
```bash
slm status  # Should show memory count
```

If empty, add some memories first:
```bash
slm remember "Test memory"
```

---

## 📚 Full Skill Reference

For complete documentation of each skill, see:
- `skills/slm-remember/SKILL.md`
- `skills/slm-recall/SKILL.md`
- `skills/slm-list-recent/SKILL.md`
- `skills/slm-status/SKILL.md`
- `skills/slm-build-graph/SKILL.md`
- `skills/slm-switch-profile/SKILL.md`

Or visit the [GitHub repository](https://github.com/varun369/SuperLocalMemoryV2/tree/main/skills).

---

## 🔗 Related Pages

- [[MCP-Integration]] - Learn about MCP-based access
- [[Universal-Architecture]] - Understand the 7-layer architecture
- [[Installation]] - Setup guide
- [[CLI-Command-Reference]] - CLI commands reference
- [[Home]] - Back to wiki home

---

**Created by Varun Pratap Bhardwaj**
