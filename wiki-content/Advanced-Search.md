# Advanced Search

**SuperLocalMemory V2 finds what you mean, not just what you typed.** Search combines multiple signals simultaneously — the meaning behind your query, the exact words you used, and the web of connections between your memories — to surface the right result fast.

---

## Why Search Works Better Here

Most note apps match keywords. SuperLocalMemory does more: it runs three complementary search signals at the same time and merges the results.

- **Meaning-based search** — finds memories that are semantically related to your query, even if you use different words
- **Keyword search** — precise matching when you remember the exact term
- **Connection-based search** — follows links between related memories to surface context you did not directly ask for

The combination means you can search the way you actually think — imprecise, natural language — and still get the right result.

**And it gets smarter over time.** After you have used the system for a while, your personal preferences and project context actively influence result ranking. See the [Learning System](Learning-System) page for details.

---

## Basic Usage

```bash
# Natural language — describe what you're looking for
slm recall "how did we solve the database lock issue"

# Technical — exact term or component name
slm recall "FastAPI authentication middleware"

# Time-referenced — works with natural time phrases
slm recall "last month performance work"
slm recall "the Redis decision from last week"

# Context-first — include the project to narrow results
slm recall "authentication" --project ecommerce-api

# Tag filter — when you saved with tags
slm recall "deployment" --tags production,critical

# Limit results — when you want a tighter answer
slm recall "database patterns" --limit 3

# Minimum relevance — filter out weak matches
slm recall "JWT expiry" --min-score 0.7
```

---

## Search Syntax and Tips

### Natural language always works

Write your query the way you would ask a colleague:

```bash
slm recall "how did we fix the login bug"
slm recall "what was the decision on caching"
slm recall "our API rate limit policy"
```

You do not need to use the exact words that are in the memory. If you saved a memory about "rate limiting at 100 requests per minute", querying "API throttle policy" will still find it.

### Time references

The system understands relative time in queries:

```bash
slm recall "last week's architecture decisions"
slm recall "during the refactor"
slm recall "before the v2 launch"
```

For precise date filtering, use SQL directly:
```bash
sqlite3 ~/.claude-memory/memory.db \
  "SELECT id, content FROM memories WHERE created_at >= date('now', '-7 days') ORDER BY created_at DESC;"
```

### Project-scoping

If you work on multiple projects, include the project name to narrow results:

```bash
slm recall "database schema" --project ecommerce-api
slm recall "auth flow" --project mobile-app
```

Or combine with tags:
```bash
slm recall "error handling" --project myapi --tags backend
```

### Cross-tool search

SuperLocalMemory searches across everything — memories saved from Claude, Cursor, Windsurf, the CLI, or any other connected tool. You do not need to know which tool created a memory to find it. Search is universal.

---

## Dashboard Search

Open the dashboard (usually at `http://localhost:8765` — see your status bar or run `slm status`).

The **Memories tab** has a search bar at the top. Results appear in real-time as you type.

**Dashboard filters:**
- **Date range** — Filter memories by when they were saved
- **Profile** — Narrow to a specific profile (work, personal, etc.)
- **Source tool** — Show only memories from Claude, Cursor, CLI, etc.
- **Tags** — Click a tag to filter instantly
- **Importance** — Filter by importance score

Each result shows a relevance score, when it was saved, which tool created it, and which project it belongs to. Click any result to see the full memory.

---

## Understanding Your Results

### Result ranking

Results are ranked by a combination of:

1. **Relevance to your query** — how well the memory matches what you asked for
2. **Your personal preferences** — memories matching your tech stack and current project score higher
3. **Recency** — more recent memories get a mild boost
4. **Source quality** — memories from tools you have historically found most useful rank slightly higher

The learning system (Phase 2 and above) means the same search query can return different orderings for different people — your results are calibrated to how you work.

### Relevance scores

Each result includes a relevance score from 0.0 to 1.0. As a rough guide:

| Score | What it means |
|-------|--------------|
| 0.9 — 1.0 | Very strong match — likely what you wanted |
| 0.7 — 0.9 | Good match — worth reading |
| 0.5 — 0.7 | Partial match — related but may not be exact |
| Below 0.5 | Weak match — included for completeness |

Use `--min-score 0.7` to filter out weak matches when you want a tight result set.

### Related memories

When a memory matches your query, the system also checks whether any connected memories in the knowledge graph are relevant. These appear as "related" results beneath the primary match.

This is useful when a concept you saved is connected to other decisions you made at the same time — the system surfaces the cluster, not just the single memory.

---

## Knowledge Graph Connections

Every memory you save is automatically linked to related memories. The knowledge graph is built from the concepts that appear across your memories — when the same concept appears in multiple places, those memories are connected.

**Why this matters for search:**

```
You save:
  Memory A: "Use JWT for API authentication"
  Memory B: "Token expiry should be 24 hours"
  Memory C: "Refresh tokens needed for mobile clients"

Search "authentication" finds Memory A directly.
The graph shows Memory A connects to B and C.
All three surface together in your results.
```

You captured three separate decisions over time — the graph stitches them back together when you need them.

**To rebuild or update the graph** (run after bulk imports or if search quality degrades):
```bash
slm build-graph
slm build-graph --force    # Complete rebuild from scratch
```

**To view connections visually**, open the Graph tab in the dashboard. You can zoom, pan, and click any node to see its connected memories.

See [Knowledge Graph Guide](Knowledge-Graph-Guide) for full details on the graph and [Using Interactive Graph](Using-Interactive-Graph) for the dashboard visualization.

---

## Performance Expectations

Search is fast for typical personal use:

| Memory count | Typical search time |
|-------------|---------------------|
| Under 500 | Under 50ms |
| 500 — 2,000 | 50ms — 200ms |
| 2,000 — 5,000 | 200ms — 1,500ms |

*Measured on Apple M4 Pro, Python 3.12. Results vary by hardware.*

Search quality does not degrade as your library grows — the hybrid approach maintains precision across larger collections. Speed decreases slightly at very large sizes, but relevance stays high.

---

## Tips for Better Results

**Save memories with context.** A memory saved as just "use connection pooling" is harder to find than "In the ecommerce-api project, use connection pooling for the PostgreSQL layer — avoids overhead of reconnecting on every request." The extra context gives search more signals to work with.

```bash
# Good — searchable from multiple angles
slm remember "In project X, we decided to use Redis for session storage because we needed sub-10ms reads across multiple API servers" --project myapp --tags redis,sessions,architecture

# Poor — hard to find later
slm remember "Redis for sessions" --tags redis
```

**Use tags when saving.** Tags enable precise filtering when you recall later. Consistent tag use is worth the extra two seconds:
```bash
slm remember "Rate limit: 100 req/min per API key" --tags api,rate-limiting,policy --project ecommerce-api
```

**Include the decision reason.** "We chose X" is hard to distinguish from "We tried X but rejected it." Include the outcome:
```bash
slm remember "Chose PostgreSQL over MySQL for this project — needed JSON column support and Postgres is our team standard" --tags database,architecture
```

**Build your graph after bulk saves.** If you import many memories at once, run `slm build-graph` afterwards to update the connections:
```bash
slm build-graph
```

**The more you use it, the better it gets.** Every recall you make, and every time you mark a memory as useful, improves future search rankings for your profile. The system is designed to get out of your way as fast as possible — but it needs a little signal to learn what matters to you. See [Learning System](Learning-System) for details.

---

## Related Pages

- [Learning System](Learning-System) — How personalized ranking works
- [Knowledge Graph Guide](Knowledge-Graph-Guide) — How memory connections are built
- [Using Interactive Graph](Using-Interactive-Graph) — Graph visualization in the dashboard
- [CLI Cheatsheet](CLI-Cheatsheet) — Full search command reference
- [Pattern Learning Explained](Pattern-Learning-Explained) — Tech preference detection

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
