# Learning System

**SuperLocalMemory V2 gets smarter the more you use it** — automatically, with no configuration required. It observes your patterns, adapts to your workflow, and surfaces the memories you need before you have to dig for them.

---

## What the Learning System Does

After a few weeks of use, you might have hundreds of memories. A basic search returns many results — but the one you actually need can be buried on page two. The learning system fixes this by understanding how *you* work and re-ranking results accordingly.

**The difference in practice:**

```
Without learning:
  You search "authentication" → 47 results, sorted by text match
  The memory you need is at position 12

With learning:
  You search "authentication" → Same 47 results, re-ranked
  The system knows your current project, your preferred approach,
  and which tool created your most-used memories
  → The memory you need is at position 1
```

**What it learns silently, with zero effort from you:**
- Your technology preferences — what frameworks, languages, and tools you actually reach for
- Your current project context — which project you are working in right now
- Your workflow sequences — the order you typically move through design, implementation, and testing
- Which sources produce memories you actually use (and which ones you ignore)

**What it does with that knowledge:**
- Re-ranks search results so the most relevant memories rise to the top
- Boosts memories that match your current project
- Deprioritizes memories from sources that have historically been less useful to you
- Adapts over time as your preferences shift

---

## What It Learns: Three Layers

### Your Technology Preferences

The system tracks which technologies appear in your memories and builds a running preference profile. This is cross-project — preferences you establish in one project carry over to new ones.

**Example:**
```
After two months of use:

Frameworks:
  React          73% confidence  (47 observations, last: 2 days ago)
  FastAPI        68% confidence  (31 observations, last: 1 day ago)
  Next.js        52% confidence  (18 observations, last: 4 days ago)

Languages:
  Python         71% confidence  (52 observations, last: today)
  TypeScript     63% confidence  (38 observations, last: 2 days ago)
```

Preferences decay naturally. A technology you used six months ago but have not touched since will gradually lose its boost. Current usage always wins.

### Your Project Context

The system detects which project you are in right now and boosts memories relevant to it. It picks this up from your working directory, your recent tags, and your active profile — no manual input needed.

**Example:**
```
You are in ~/projects/ecommerce-api/

Search for "database" boosts:
  - Memories tagged with "ecommerce-api" or "ecommerce"
  - Memories about your PostgreSQL setup (used in this project)
  - Memories from the same profile

Over memories about MongoDB (used in a different project)
```

### Your Workflow Patterns

The system notices the sequences you repeat across sessions and uses them to predict what you will need next.

**Example:**
```
Pattern detected over several weeks:
  1. You recall architecture docs
  2. Then you save implementation decisions
  3. Then you recall testing patterns
  4. Then you save test results

When you start step 1 on a new feature,
testing-related memories get a subtle ranking boost
for the upcoming searches — before you even ask for them.
```

---

## Three Phases of Personalization

The learning system starts useful on day one and gets progressively smarter as it gathers more data about what you find helpful.

### Phase 1 — Intelligent Baseline (0 to 19 feedback signals)

Active from your very first use. No feedback required.

The system applies intelligent defaults: recent memories rank higher, high-importance memories rank higher, and memories that share tags with your recent activity get a boost. It works well out of the box, even before it knows anything about you personally.

### Phase 2 — Preference-Aware Ranking (20 to 199 signals)

Once you have provided around 20 feedback signals — either by marking memories as useful or simply by using the system regularly — rule-based personalization kicks in.

At this stage, your tech preferences, project context, and workflow patterns actively influence every search result. Memories from your preferred tools and projects move up. Stale ones from unrelated contexts move down.

### Phase 3 — Full Personalization (200+ signals)

With enough data, a local model trains on your personal feedback history and takes over ranking. It discovers patterns that simple rules would miss — correlations between time of day, query type, project phase, and what you have historically found useful.

**The transition is automatic.** You will not notice it happening — results simply keep improving. If the local model ever performs worse than the rule-based phase, the system falls back automatically. No configuration, no breakage.

---

## How to Interact With the Learning System

### CLI Commands

```bash
# After recalling memories, mark the ones that were actually useful
slm useful 42
slm useful 42 87 103          # Mark multiple at once

# See what preferences have been learned
slm patterns list

# Filter to a specific profile
slm patterns list --profile work

# Filter by category
slm patterns list --category frameworks

# Check which phase you are in and how many signals collected
slm learning status

# Wipe all learned data (your memories are not affected)
slm learning reset

# View memory system health and usage trends
slm engagement
slm engagement --days 30
```

**Example: `slm learning status` output:**
```
Learning System Status
======================

Ranking Phase:     Rule-Based (Phase 2)
Feedback Signals:  127 / 200 needed for full personalization

Layer 1 (Tech Preferences):  Active — 15 patterns learned
Layer 2 (Project Context):   Active — Current project: ecommerce-api
Layer 3 (Workflow Patterns):  Active — 4 sequences detected

Source Quality:
  cursor-mcp:      0.82  (your most-used source)
  claude-desktop:   0.78
  cli:              0.65

Last Updated:  2 minutes ago
```

**Example: `slm patterns list` output:**
```
Learned Patterns (from 523 memories)
=====================================

Frameworks:
  React          73% confidence  (47 observations, last: 2 days ago)
  FastAPI        68% confidence  (31 observations, last: 1 day ago)

Languages:
  Python         71% confidence  (52 observations, last: today)
  TypeScript     63% confidence  (38 observations, last: 2 days ago)

Workflow Sequences:
  docs → architecture → code → test  (seen 12 times)
  recall auth → save implementation   (seen 8 times)
```

### MCP Tools (Claude, Cursor, Windsurf Users)

If you use SuperLocalMemory through an MCP-connected IDE, feedback collection is automatic — your AI assistant handles it as part of its normal workflow.

Three tools are available:

**`memory_used`** — Report that a recalled memory was actually useful. In MCP-connected tools, this happens automatically. For manual use:
```
Tell your AI: "That memory about JWT auth was useful — mark it with memory_used"
```

**`get_learned_patterns`** — Ask your AI assistant what the system has learned about your preferences:
```
"Show me my learned patterns from SuperLocalMemory"
```

Example response:
```json
{
  "patterns": [
    { "pattern": "FastAPI", "confidence": 0.68, "frequency": 31 },
    { "pattern": "React",   "confidence": 0.73, "frequency": 47 }
  ],
  "ranking_phase": "rule_based"
}
```

**`correct_pattern`** — Fix a wrong or outdated preference with a direct override:
```
"Use correct_pattern to suppress Angular — I stopped using it last month"
```

Actions available: `suppress` (stop boosting), `boost` (manually increase weight), `reset` (clear and re-learn).

---

## Privacy

All learning data lives in `~/.claude-memory/learning.db` — on your machine, nowhere else.

**What is stored in `learning.db`:**
- Technology name counts and confidence scores (no memory content)
- Project directory names for context detection
- Memory IDs and timestamps from feedback (not the memory text)
- Aggregate usage counts for engagement metrics

**What is never stored:** The actual text of your memories never enters the learning database. Learning works entirely from metadata, IDs, and counts.

**`learning.db` and `memory.db` are completely independent.** Deleting one has zero effect on the other. Your memories are always safe even if you wipe all learned data.

**To erase all behavioral data instantly:**
```bash
rm ~/.claude-memory/learning.db
```

The system starts fresh on the next operation. No data leaves your machine. No request to submit. No waiting.

**Zero telemetry.** There is no analytics, no usage tracking, and no cloud component of any kind.

---

## FAQ

**Does the learning system slow down search?**

No. The personalization step runs in the background after results are retrieved. In typical use, you will not notice any difference in response time.

**What if it learns the wrong preference?**

Fix it with a single command:
```bash
slm patterns reset "Angular"      # Reset one pattern
slm patterns reset --all          # Reset all patterns
```

Or from your AI assistant using the `correct_pattern` MCP tool.

**Can I see everything it has learned about me?**

Yes:
```bash
slm patterns list
slm learning status
```

**Does switching profiles reset learning?**

No — each profile learns independently. Switching to a different profile starts from that profile's accumulated signals, not zero. If you have never used a profile before, it begins at Phase 1.

**Can I opt out entirely?**

Yes. Set `"learning": { "enabled": false }` in your `~/.claude-memory/config.json`. Recall returns to pure text relevance ranking, the same as before v2.7. Re-enable at any time without data loss.

---

## Tips for Better Personalization

**Give feedback after recalls.** The more signals the system has, the faster it reaches better personalization phases. In MCP tools this is automatic. For CLI use:
```bash
slm recall "database patterns"
slm useful 42                   # Takes 2 seconds, meaningfully improves future results
```

**Use consistent tags.** Project context detection works better when you use consistent project tags:
```bash
slm remember "Use connection pooling" --tags ecommerce-api,database
slm remember "Rate limit at 100/min" --tags ecommerce-api,api
```

**Use profiles for distinct work contexts.** If you work on very different types of projects, separate profiles keep learning signals clean and relevant:
```bash
slm switch-profile backend-work
slm switch-profile frontend-work
```

**Review what it has learned occasionally.** Every few weeks, run `slm patterns list` to see what the system thinks your preferences are. Correct anything outdated before it affects too many searches.

---

## Related Pages

- [Pattern Learning Explained](Pattern-Learning-Explained) — Identity context and framework detection
- [Multi-Profile Workflows](Multi-Profile-Workflows) — Using profiles to separate learning contexts
- [MCP Integration](MCP-Integration) — Automatic feedback in Claude, Cursor, and Windsurf
- [CLI Cheatsheet](CLI-Cheatsheet) — Full command reference
- [Upgrading to v2.7](Upgrading-to-v2.7) — Upgrade guide with learning system setup

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
