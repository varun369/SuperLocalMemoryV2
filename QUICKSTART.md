# Quick Start Guide

## SuperLocalMemory V2 - Get Started in 5 Minutes

This guide gets you from installation to your first intelligent memory operations in under 5 minutes.

**SuperLocalMemory V2.1.0-universal** is a universal memory system that works across 8+ IDEs and CLI tools with automatic configuration. No external dependencies required.

## Three Ways to Use SuperLocalMemory V2

**Version 2.1.0-universal** offers multiple access methods - all using the same local database:

1. **MCP (Model Context Protocol)** - Auto-configured for Cursor, Windsurf, Claude Desktop
   - AI assistants get natural memory access
   - Just talk: "Remember that we use FastAPI"
   - No manual commands needed

2. **Skills & Commands** - For Claude Code, Continue.dev, Cody
   - Claude Code: `/superlocalmemoryv2:remember "text"`
   - Continue.dev: `/slm-remember text`
   - Cody: `/slm-remember` (with selection)

3. **Universal CLI** - Works in any terminal or script
   - Simple syntax: `slm remember "text"`
   - Original commands still work: `superlocalmemoryv2:remember "text"`
   - No additional setup needed

**All three methods work identically and use the same database.** Choose what fits your workflow.

---

## Prerequisites

Before starting, ensure you've completed the installation:
- [Installation Guide](INSTALL.md) completed
- CLI commands available in PATH
- Python 3.8+ installed

Verify installation:
```bash
slm status
# OR
superlocalmemoryv2:status
```

**Auto-Configuration:** The installer automatically detected and configured your installed IDEs (Cursor, Windsurf, VS Code, etc.). See [Universal Integration Guide](docs/UNIVERSAL-INTEGRATION.md) for details.

---

## Your First 5 Minutes

### Minute 1: Add Your First Memories

SuperLocalMemory V2 learns from your memories. Let's add some.

**Choose your preferred method:**

#### Option A: Universal CLI (Simple - Works Anywhere)

```bash
slm remember "Built React authentication using JWT tokens" --tags auth,react,security
slm remember "Optimized database queries using indexes" --tags performance,database
slm remember "Created user profile management with React hooks" --tags react,frontend,user-management
slm remember "Implemented token refresh mechanism for security" --tags auth,security,tokens
slm remember "Fixed N+1 query problem in API endpoints" --tags performance,api,database
```

#### Option B: Claude Code Skills

```bash
/superlocalmemoryv2:remember "Built React authentication using JWT tokens" --tags auth,react,security
/superlocalmemoryv2:remember "Optimized database queries using indexes" --tags performance,database
/superlocalmemoryv2:remember "Created user profile management with React hooks" --tags react,frontend,user-management
/superlocalmemoryv2:remember "Implemented token refresh mechanism for security" --tags auth,security,tokens
/superlocalmemoryv2:remember "Fixed N+1 query problem in API endpoints" --tags performance,api,database
```

#### Option C: Cursor/Windsurf/Claude Desktop (MCP - Just Talk)

If you're using Cursor, Windsurf, or Claude Desktop, you can simply tell the AI:

```
You: "Remember that we built React authentication using JWT tokens, focusing on auth, react, and security"
AI: [Automatically calls remember() tool and saves memory]
✓ Memory saved
```

**What just happened?**
- 5 memories stored in local SQLite database
- Full-text search indexes created automatically
- Tags assigned for organization
- All methods work identically and use the same database

---

### Minute 2: Search Your Memories

Test basic search functionality.

**Claude CLI:**
```bash
/superlocalmemoryv2:search "authentication"
/superlocalmemoryv2:search "performance"
/superlocalmemoryv2:search "react"
```

**Terminal/Standalone:**
```bash
python3 memory_store_v2.py search "authentication"
python3 memory_store_v2.py search "performance"
python3 memory_store_v2.py search "react"
```

**Expected output:**
```
Found 2 memories matching "authentication":
1. Built React authentication using JWT tokens
2. Implemented token refresh mechanism for security
```

---

### Minute 3: Build Knowledge Graph

Now the magic happens - let SuperLocalMemory discover relationships.

**Claude CLI:**
```bash
/superlocalmemoryv2:graph-build
/superlocalmemoryv2:graph-stats
```

**Terminal/Standalone:**
```bash
python3 graph_engine.py build
python3 graph_engine.py stats
```

**Expected output:**
```
Knowledge Graph Statistics:
Total Clusters: 3
Total Entities: 12
Average Cluster Size: 2-3 memories

Discovered Clusters:
- Cluster 1: "Authentication & Security" (3 memories)
- Cluster 2: "Performance & Optimization" (2 memories)
- Cluster 3: "React & Frontend" (2 memories)
```

**What just happened?**
- TF-IDF extracted important terms from memories
- Leiden algorithm clustered related memories
- Clusters auto-named based on common themes

---

### Minute 4: Discover Patterns

Let the system learn your coding style and preferences.

**Claude CLI:**
```bash
/superlocalmemoryv2:patterns update
/superlocalmemoryv2:patterns list 0.1
/superlocalmemoryv2:patterns context 0.5
```

**Terminal/Standalone:**
```bash
python3 pattern_learner.py update
python3 pattern_learner.py list 0.1
python3 pattern_learner.py context 0.5
```

**Expected output:**
```
Learned Patterns:

Preferences (Framework):
- React: 60% confidence (appears in 3/5 memories)

Preferences (Security):
- JWT tokens: 40% confidence (appears in 2/5 memories)

Preferences (Performance):
- Database optimization: 40% confidence (appears in 2/5 memories)
```

**What just happened?**
- System analyzed frequency of topics in memories
- Extracted your coding preferences with confidence scores
- Built identity profile for future context retrieval

---

### Minute 5: Explore Relationships

Find related memories using the knowledge graph:

```bash
# Get memory ID from search
python3 memory_store_v2.py search "JWT"
# Note the ID (e.g., memory_id: 1)

# Find related memories
python3 graph_engine.py related --memory-id 1
```

**Expected output:**
```
Memories related to "Built React authentication using JWT tokens":

Same Cluster (Authentication & Security):
- Implemented token refresh mechanism for security
- [Future auth-related memories will appear here]

Shared Entities:
- Both mention: authentication, tokens, security
```

---

## Core Workflows

### Workflow 1: Daily Memory Capture

Add memories as you work:

```bash
# Add memory with context
python3 memory_store_v2.py add "Fixed CORS issue in API gateway" --tags api,bug-fix,security

# Add memory with multiple tags
python3 memory_store_v2.py add "Deployed microservice using Docker and Kubernetes" --tags devops,docker,kubernetes,deployment
```

**Pro tip:** Add memories right after completing a task while details are fresh.

---

### Workflow 2: Knowledge Discovery

Find related information:

```bash
# 1. Search for a topic
python3 memory_store_v2.py search "docker"

# 2. Get memory ID from results
# Example: memory_id: 7

# 3. Find related memories
python3 graph_engine.py related --memory-id 7

# 4. View entire cluster
python3 graph_engine.py cluster --cluster-id 4
```

**Use case:** "What else did I learn about Docker?" - Get the full cluster.

---

### Workflow 3: Pattern Recognition

Understand your coding style:

```bash
# Get patterns for Claude context
python3 pattern_learner.py context 0.5

# Output format ready for .claude-memory/context.md
```

**Use case:** Provide patterns to AI assistant for personalized responses.

---

### Workflow 4: Profile Management

Separate memories by project or client:

```bash
# Create profile for a specific project
memory-profile create project-alpha --description "Alpha project memories"

# Switch to profile
memory-profile switch project-alpha

# All future memories go to this profile
python3 memory_store_v2.py add "Implemented Alpha dashboard" --tags alpha,dashboard

# Switch back to default
memory-profile switch default
```

**Use case:** Keep work and personal memories separate, or manage multiple clients.

---

## Common Tasks

### Task: View System Status

```bash
memory-status
```

Shows:
- Database location and size
- Total memories count
- Active profile
- Graph statistics
- Pattern counts

---

### Task: Rebuild Knowledge Graph

After adding many memories:

```bash
# Rebuild entire graph
python3 graph_engine.py build

# View updated statistics
python3 graph_engine.py stats
```

**When to rebuild:**
- After adding 10+ new memories
- Weekly maintenance
- Before important searches

---

### Task: Update Patterns

After significant new memories:

```bash
# Update pattern learning
python3 pattern_learner.py update

# View updated patterns
python3 pattern_learner.py list 0.1
```

**When to update:**
- After adding 20+ new memories
- Weekly or bi-weekly
- When coding style changes

---

### Task: Backup Database

Before major operations:

```bash
# Create manual backup
cp ~/.claude-memory/memory.db ~/.claude-memory/backups/memory-backup-$(date +%Y%m%d).db

# Verify backup
ls -lh ~/.claude-memory/backups/
```

**Pro tip:** Backups are created automatically during reset operations.

---

## Pro Tips

### Tip 1: Use Descriptive Memory Text

**Good:**
```bash
python3 memory_store_v2.py add "Implemented JWT refresh token rotation with 7-day expiry for enhanced security" --tags auth,security
```

**Bad:**
```bash
python3 memory_store_v2.py add "Did auth stuff" --tags auth
```

**Why:** More descriptive text = better graph clustering and pattern learning.

---

### Tip 2: Tag Consistently

Create a tagging system:

**Categories:**
- **Domain:** `auth`, `frontend`, `backend`, `devops`
- **Technology:** `react`, `python`, `docker`, `aws`
- **Type:** `bug-fix`, `feature`, `optimization`, `learning`

**Example:**
```bash
python3 memory_store_v2.py add "Fixed memory leak in React component" --tags frontend,react,bug-fix,performance
```

---

### Tip 3: Regular Graph Rebuilds

Add to weekly routine:

```bash
# Sunday evening maintenance
python3 graph_engine.py build
python3 pattern_learner.py update
python3 pattern_learner.py stats
```

**Why:** Keeps relationships fresh and patterns accurate.

---

### Tip 4: Use Profiles for Context Switching

```bash
# Work context
memory-profile create work
memory-profile switch work

# Personal projects
memory-profile create personal
memory-profile switch personal

# Learning/experimentation
memory-profile create learning
memory-profile switch learning
```

**Why:** Clean separation prevents context pollution.

---

## What's Next?

Now that you're familiar with the basics:

### Learn Advanced Features

1. **Compression System:** [docs/COMPRESSION-README.md](docs/COMPRESSION-README.md)
   - Progressive summarization
   - Cold storage archival
   - Space savings strategies

2. **Graph Engine Deep Dive:** [docs/GRAPH_ENGINE_README.md](docs/GRAPH_ENGINE_README.md)
   - Clustering algorithms
   - Entity extraction
   - Relationship types

3. **Pattern Learning:** [docs/PATTERN_LEARNER_README.md](docs/PATTERN_LEARNER_README.md)
   - Confidence scoring
   - Context extraction
   - Identity profiles

4. **Profile Management:** [docs/PROFILES-GUIDE.md](docs/PROFILES-GUIDE.md)
   - Multi-profile workflows
   - Migration strategies
   - Backup management

### Explore Full CLI

Complete command reference: [docs/CLI-COMMANDS-REFERENCE.md](docs/CLI-COMMANDS-REFERENCE.md)

### Understand Architecture

Technical deep dive: [ARCHITECTURE.md](ARCHITECTURE.md)

### Contribute

Help improve the system: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Troubleshooting Quick Start

### Issue: Commands Not Working

```bash
# Verify installation
which memory-status

# If not found, check PATH
echo $PATH | grep ".claude-memory"

# Re-add if missing
echo 'export PATH="${HOME}/.claude-memory/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc
```

### Issue: Database Not Created

```bash
# Manually create database
cd ~/.claude-memory
python3 memory_store_v2.py add "Test memory" --tags test

# Verify
ls -lh memory.db
```

### Issue: Graph Build Fails

```bash
# Check if you have enough memories (minimum 2)
python3 memory_store_v2.py search ""

# If < 2 memories, add more first
```

---

## Summary

**You've learned:**
1. Add memories with tags
2. Search memories using full-text search
3. Build knowledge graphs with auto-clustering
4. Discover patterns in your coding style
5. Find related memories through graph relationships

**Core commands to remember:**
```bash
# Add memory
python3 memory_store_v2.py add "text" --tags tag1,tag2

# Search
python3 memory_store_v2.py search "query"

# Build graph
python3 graph_engine.py build

# Update patterns
python3 pattern_learner.py update

# System status
memory-status
```

---

## Author

**Varun Pratap Bhardwaj**
*Solution Architect*

SuperLocalMemory V2 - Standalone intelligent memory system that works with any AI assistant or terminal workflow.

---

**Ready to build intelligent memory?**

Start capturing your coding journey. The system learns and adapts as you grow.

**100% local. 100% private. 100% yours.**
