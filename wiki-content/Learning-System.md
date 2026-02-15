# Learning System — "Your AI Learns You"

**How SuperLocalMemory v2.7 learns your preferences and personalizes recall** - Three-layer learning architecture with adaptive ranking, all processed locally with zero telemetry.

---

## What is the Learning System?

Starting with v2.7, SuperLocalMemory goes beyond storing and retrieving memories. It **learns how you work** and uses that knowledge to surface the right memories at the right time.

**The problem it solves:** After months of use, you might have hundreds or thousands of memories. A simple search returns many results, but you have to scroll through them to find what you actually need. The learning system fixes this by understanding your patterns and ranking results accordingly.

**What it learns:**
- Your technology preferences (frameworks, languages, tools) across all projects
- Which project you are currently working on
- Your typical workflow sequences (documentation first, then architecture, then code)
- Which sources produce memories you actually use
- Which recalled memories you find useful

**What it does with that knowledge:**
- Re-ranks search results so the most relevant memories appear first
- Boosts memories matching your current project context
- Prioritizes memories from tools and sources you trust most
- Adapts over time as your preferences evolve

**Example:**
```
Before v2.7:
  You search "authentication" → 47 results, sorted by text relevance alone
  The memory you need is at position 12

After v2.7:
  You search "authentication" → Same 47 results, but re-ranked
  The system knows you are in a FastAPI project, prefer JWT, and your
  Cursor-created memories are your most-used → Result you need is at position 1
```

---

## How It Works: Three Learning Layers

The learning system has three independent layers. Each one captures a different kind of pattern. They combine during recall to produce personalized rankings.

### Layer 1: Cross-Project Tech Preferences

**What it does:** Tracks which technologies, frameworks, and tools you use across all your projects. These preferences are portable — if you prefer React in one project, that signal carries over when you start a new one.

**What it tracks:**
- Frameworks (React, FastAPI, Django, Vue, Next.js, etc.)
- Languages (Python, TypeScript, Go, Rust, etc.)
- Tools and libraries (Docker, Redis, PostgreSQL, etc.)
- Architecture patterns (microservices, serverless, REST, GraphQL)

**How it works:**
```
Every time you save or recall a memory, the system extracts
technology mentions and updates a running preference profile.

Month 1: React (73%), Vue (15%), Angular (12%)
Month 2: React (68%), Vue (22%), Angular (10%)  ← Vue usage growing
Month 3: React (55%), Vue (35%), Angular (10%)  ← Trend detected

When you search for "component architecture", memories about
React and Vue are boosted based on your actual usage patterns.
```

**Preferences decay naturally.** A framework you used heavily six months ago but haven't touched since will gradually lose its boost. Current usage always takes priority.

### Layer 2: Project Context Detection

**What it does:** Automatically detects which project you are working in and boosts memories relevant to that project.

**How it detects your project (4 signals):**

| Signal | How It Works |
|--------|-------------|
| **Working directory** | Reads the directory name and path from your environment |
| **Recent tags** | Looks at tags from your last few memories (e.g., `--tags myapp,backend`) |
| **File context** | Detects project type from files mentioned in memories (package.json = Node, pyproject.toml = Python) |
| **Active profile** | Uses your current SuperLocalMemory profile name |

**Example:**
```
You switch to ~/projects/ecommerce-api/
The system detects: "ecommerce-api" project, Python/FastAPI stack

Search for "database" now boosts:
  - Memories tagged with "ecommerce-api" or "ecommerce"
  - Memories about PostgreSQL (used in this project)
  - Memories from the same profile

Over memories about MongoDB (used in a different project)
```

### Layer 3: Workflow Pattern Mining

**What it does:** Detects your repeating workflow sequences and uses them to predict what you will need next.

**What it learns:**
- Typical activity sequences (e.g., docs, then architecture, then implementation, then testing)
- Time-of-day patterns (morning = planning, afternoon = coding)
- Session patterns (what you tend to do at the start vs. end of a session)

**Example:**
```
The system observes your pattern over weeks:
  1. You recall architecture docs
  2. Then you save implementation decisions
  3. Then you recall testing patterns
  4. Then you save test results

When you start recalling architecture docs for a new feature,
the system predicts you will soon need testing patterns and
subtly boosts their ranking in upcoming searches.
```

**How sequences are detected:** The system uses a sliding window over your recent memory operations (saves and recalls). When it sees the same sequence of topics repeat across multiple sessions, it records it as a learned workflow pattern.

---

## Adaptive Ranking: Three Phases

The ranking system gets smarter over time. It starts simple and graduates to machine learning as it collects more data about what you find useful.

### Phase 1: Baseline (Day 1)

**Active from:** First use, no feedback needed

**What it does:** Uses synthetic signals generated from your existing memories to create a starting model. Even before you give any explicit feedback, the system looks at patterns in your memory database (what you saved, how often, which tags, which projects) to make educated guesses about relevance.

**How it ranks:** Standard text relevance (FTS5 + TF-IDF) enhanced with:
- Recency boost (newer memories rank higher)
- Importance boost (high-importance memories rank higher)
- Tag overlap boost (memories sharing tags with recent activity rank higher)

### Phase 2: Rule-Based Boosting (After ~50 feedback signals)

**Active from:** After you start using the `memory_used` feedback tool

**What it adds on top of Phase 1:**
- Cross-project tech preference boosting (Layer 1)
- Project context boosting (Layer 2)
- Workflow prediction boosting (Layer 3)
- Source quality weighting (memories from your preferred tools rank higher)

**How it works:**
```
Base score from text search: 0.85
+ Tech preference match:     +0.05 (you prefer FastAPI, this memory is about FastAPI)
+ Project context match:     +0.08 (this memory is tagged with your current project)
+ Source quality bonus:       +0.03 (this memory came from Cursor, your most-used tool)
= Final score:                1.01 → Re-ranked to position 1
```

### Phase 3: ML Ranking (After ~200 feedback signals)

**Active from:** After sufficient feedback data accumulates

**What it does:** A local LightGBM model learns your personal relevance function. It considers dozens of features simultaneously and discovers patterns that simple rules would miss.

**Features the model learns from:**
- Text relevance scores
- Recency and importance
- Tag similarity between query and memory
- Your tech preference alignment
- Project context signals
- Source quality history
- Workflow position (where you are in your typical sequence)
- Time-of-day patterns
- Historical feedback on similar queries

**The transition is automatic.** You do not need to configure anything. The system checks if it has enough feedback data and switches to ML ranking when ready. If the ML model performs worse than rule-based (measured by internal validation), it falls back to Phase 2 automatically.

**Dependencies:** Phase 3 requires `lightgbm` and `scipy` (installed automatically). If these are not available, the system stays on Phase 2 permanently — no degradation of existing functionality.

---

## Feedback System

The learning system needs to know which recalled memories were useful to you. There are three feedback channels.

### 1. MCP Tool: `memory_used` (Primary)

**How it works:** After your AI assistant recalls memories and uses one, it calls `memory_used` to tell the system which memory was helpful.

**This happens automatically** in MCP-connected tools (Claude Desktop, Cursor, Windsurf, etc.). The AI assistant calls `memory_used` as part of its natural workflow — you do not need to do anything.

**MCP tool signature:**
```json
{
  "name": "memory_used",
  "description": "Report that a recalled memory was useful in the current context",
  "inputSchema": {
    "type": "object",
    "properties": {
      "memory_id": {
        "type": "integer",
        "description": "ID of the memory that was useful"
      },
      "context": {
        "type": "string",
        "description": "Brief description of how it was used (optional)"
      }
    },
    "required": ["memory_id"]
  }
}
```

### 2. CLI: `slm useful` (Manual)

**For terminal workflows:** After recalling memories via CLI, mark the useful ones.

```bash
# Recall memories
slm recall "authentication patterns"

# Mark memory #42 as useful
slm useful 42

# Mark with context
slm useful 42 --context "Used for JWT refresh token implementation"
```

### 3. Passive Decay (Automatic)

**Memories that are never used gradually lose their ranking boost.** This is not a punishment — it is a natural signal that those memories may be less relevant to your current work.

- Memories recalled but never marked as useful: slow decay over 30 days
- Memories never recalled at all: no boost, but no penalty either
- Memories marked as useful: boosted for 14 days, then gradual normalization

---

## New MCP Tools (v2.7)

Three new tools are available in all MCP-connected IDEs.

### `memory_used`

Report that a recalled memory was useful. This is the primary feedback channel for the learning system.

```json
{
  "name": "memory_used",
  "input": { "memory_id": 42, "context": "Used for API design" }
}
```

### `get_learned_patterns`

Retrieve your current learned preferences. Useful for inspecting what the system has learned about you.

```json
{
  "name": "get_learned_patterns",
  "input": { "category": "frameworks", "min_confidence": 0.5 }
}
```

**Response example:**
```json
{
  "patterns": [
    { "pattern": "React", "confidence": 0.73, "frequency": 47, "last_seen": "2026-05-15" },
    { "pattern": "FastAPI", "confidence": 0.68, "frequency": 31, "last_seen": "2026-05-14" },
    { "pattern": "Next.js", "confidence": 0.52, "frequency": 18, "last_seen": "2026-05-12" }
  ],
  "total_memories_analyzed": 523,
  "ranking_phase": "rule_based"
}
```

**Categories:** `frameworks`, `languages`, `tools`, `architecture`, `workflow`, `all`

### `correct_pattern`

Tell the system that a learned pattern is wrong or outdated.

```json
{
  "name": "correct_pattern",
  "input": { "pattern": "Angular", "action": "suppress", "reason": "Switched to React last month" }
}
```

**Actions:**
- `suppress` — Stop boosting this pattern in rankings
- `boost` — Manually increase this pattern's weight
- `reset` — Clear all learned data for this pattern and let it re-learn

---

## New CLI Commands (v2.7)

### `slm useful`

Mark a memory as useful after recall.

```bash
# Basic usage
slm useful <memory_id>

# With context
slm useful 42 --context "Used for JWT implementation"

# Mark multiple
slm useful 42 43 44
```

### `slm patterns`

View and manage learned patterns.

```bash
# List all learned patterns
slm patterns list

# List by category
slm patterns list --category frameworks

# List with minimum confidence
slm patterns list --min-confidence 0.6

# Reset a specific pattern
slm patterns reset "Angular"

# Reset all patterns (confirmation required)
slm patterns reset --all
```

**Example output:**
```
Learned Patterns (from 523 memories)
=====================================

Frameworks:
  React          73% confidence  (47 observations, last: 2 days ago)
  FastAPI        68% confidence  (31 observations, last: 1 day ago)
  Next.js        52% confidence  (18 observations, last: 4 days ago)

Languages:
  Python         71% confidence  (52 observations, last: today)
  TypeScript     63% confidence  (38 observations, last: 2 days ago)

Workflow Sequences:
  docs -> architecture -> code -> test  (seen 12 times)
  recall auth -> save implementation    (seen 8 times)
```

### `slm learning`

Check the status of the adaptive ranking system.

```bash
# View learning status
slm learning status
```

**Example output:**
```
Learning System Status
======================

Ranking Phase:     Rule-Based (Phase 2)
Feedback Signals:  127 / 200 needed for ML phase
Model Status:      Not yet trained (need 73 more signals)

Layer 1 (Tech Preferences):  Active - 15 patterns learned
Layer 2 (Project Context):   Active - Current project: ecommerce-api
Layer 3 (Workflow Patterns):  Active - 4 sequences detected

Source Quality:
  cursor-mcp:     0.82 quality score (most useful memories)
  claude-desktop:  0.78 quality score
  cli:             0.65 quality score

Learning DB Size:  2.1 MB
Last Updated:      2 minutes ago
```

### `slm engagement`

View local engagement metrics for your memory system health.

```bash
# View engagement summary
slm engagement

# View for specific time period
slm engagement --days 30
```

**Example output:**
```
Memory System Health (Last 30 Days)
====================================

Activity:
  Memories saved:    47
  Memories recalled:  183
  Feedback given:    31 useful / 183 recalls (17% feedback rate)

Trends:
  Save frequency:    Stable (1.5/day average)
  Recall frequency:  Increasing (+12% vs previous 30 days)
  Feedback rate:     Improving (+5% vs previous 30 days)

Top Categories:
  1. Backend API patterns     (34 recalls)
  2. Authentication           (28 recalls)
  3. Database design          (21 recalls)
```

**Zero telemetry.** All metrics are computed locally from your `learning.db` file. Nothing leaves your machine.

---

## Source Quality Tracking

The learning system tracks which tools and sources produce memories you actually use.

**How it works:**
1. Every memory records which tool created it (Cursor, Claude Desktop, CLI, etc.)
2. When you mark a memory as useful via `memory_used` or `slm useful`, the source gets a quality boost
3. Over time, memories from high-quality sources get a ranking bonus

**Example:**
```
After 3 months of use:

Source Quality Scores:
  cursor-mcp:       0.82  (You use 34% of memories from Cursor)
  claude-desktop:    0.78  (You use 28% of memories from Claude Desktop)
  cli:               0.65  (You use 15% of memories from CLI)
  continue-dev:      0.71  (You use 22% of memories from Continue.dev)

When you search, memories from Cursor get a slight ranking boost
over memories from CLI, because historically you find Cursor
memories more useful.
```

**Source quality decays and adapts.** If you switch to a new IDE and start finding its memories more useful, the scores adjust within a few weeks.

---

## Configuration & Privacy

### Separate Learning Database

Learning data is stored in a separate file: `~/.claude-memory/learning.db`

This is intentionally separate from your memories (`memory.db`) for two reasons:

1. **GDPR-friendly erasure:** Delete `learning.db` to erase all behavioral data without touching your memories
2. **Isolation:** A corrupted learning database cannot affect your memory storage

### Data Stored in learning.db

| Data | Purpose | Contains Personal Content? |
|------|---------|---------------------------|
| Tech preferences | Framework/language counts | No (just technology names and counts) |
| Project contexts | Project detection signals | Directory names only |
| Workflow sequences | Activity type sequences | No (just pattern labels like "recall", "save") |
| Feedback signals | Which memories were useful | Memory IDs and timestamps only |
| Source quality | Per-tool quality scores | Tool names and scores only |
| Engagement metrics | Activity counts | Aggregate counts only |

### Privacy Guarantees

- **100% local processing.** No data leaves your machine. No API calls. No cloud sync.
- **Zero telemetry.** No usage data, analytics, or tracking of any kind.
- **No memory content in learning.db.** The learning database stores counts, scores, and IDs — never the content of your memories.
- **One-command delete.** Remove all learned data instantly:

```bash
rm ~/.claude-memory/learning.db
```

Your memories are completely unaffected. The learning system simply starts fresh on the next operation.

### Disabling the Learning System

If you prefer not to use personalized ranking:

```bash
# In your config.json
{
  "learning": {
    "enabled": false
  }
}
```

With learning disabled, recall works exactly as it did in v2.6 — pure text relevance ranking with no personalization. You can re-enable it at any time without data loss.

---

## Research Foundations

Every component of the v2.7 learning system is grounded in peer-reviewed research, adapted for local-first operation without any cloud or LLM dependency.

### Core Architecture

| Component | Research Paper | How We Use It |
|-----------|---------------|---------------|
| **Two-stage retrieve-then-rerank** | ColBERT-Based User Profiles (eKNOW 2025) | BM25/FTS5/TF-IDF retrieves candidates; LightGBM re-ranks with personalized features |
| **LightGBM LambdaRank** | LambdaMART (Burges, 2010); MO-LightGBM (SIGIR 2025) | Pairwise learning-to-rank with gradient boosting. Local inference in <10ms |
| **Three-phase cold-start** | Few-Shot Learning for Cold-Start (LREC 2024) | Baseline → rule-based → ML, adapting as feedback data accumulates |
| **Temporal confidence decay** | MACLA (arXiv:2512.18950) | Bayesian Beta-Binomial confidence with exponential temporal decay |
| **Sequence pattern mining** | TSW-PrefixSpan (IEEE 2020) | Time-weighted sliding-window n-gram detection for workflow patterns |
| **Synthetic bootstrap** | Semi-supervised L2R with pseudo-labels (WWW 2015); GPL (NAACL 2022) | Generates training data from existing memory patterns for day-1 ML model |

### Privacy Architecture

| Concern | Research Basis | Our Approach |
|---------|---------------|--------------|
| **Privacy-preserving feedback** | ADPMF — Adaptive Differentially Private Matrix Factorization (IPM, 2024) | We go further: zero communication by design. No differential privacy noise needed because data never leaves the device |
| **Data minimization** | GDPR Article 5(1)(c) | Query hashes (SHA256[:16]) stored instead of raw queries. No memory content in learning.db |
| **Behavioral data isolation** | SQLCipher (Zetetic) — 256-bit AES for SQLite | Separate learning.db file. Optional encryption via SQLCipher with <15% overhead |

### Key Differentiator

Most personalized retrieval systems in the literature require cloud infrastructure, GPU compute, or neural models. SuperLocalMemory's v2.7 learning system achieves personalization using only:

- **Gradient boosting** (LightGBM) — CPU-only, <10ms inference, 30MB install
- **Statistical features** — TF-IDF, frequency analysis, Beta-Binomial scoring
- **Local SQLite** — All data in two files on your machine

No prior work in the academic literature combines local-only gradient boosting re-ranking with multi-channel implicit feedback for personal memory retrieval. This appears to be a novel contribution.

---

## GDPR Compliance — Data Sovereignty

SuperLocalMemory v2.7 is designed for full GDPR compliance by architecture, not by policy.

| GDPR Right | How SuperLocalMemory Implements It |
|------------|-----------------------------------|
| **Art. 6 — Lawful Basis** | No processing of personal data by third parties. All processing is local. |
| **Art. 17 — Right to Erasure** | `slm learning reset` or `rm ~/.claude-memory/learning.db` — instant, complete |
| **Art. 20 — Data Portability** | Copy `learning.db` and `memory.db` — standard SQLite files, readable by any tool |
| **Art. 25 — Data Protection by Design** | Separate databases, query hashing, no memory content in behavioral data |
| **Art. 35 — DPIA** | Not required — no high-risk processing, no profiling for automated decisions affecting individuals |

**Compare with cloud alternatives:**
- Cloud memory services process your data on their servers under their terms
- Deleting your data requires submitting a formal request and waiting
- You have no way to verify deletion actually occurred
- Your behavioral patterns are their business asset

**With SuperLocalMemory:**
- Your data is files on your machine
- You delete them yourself, instantly
- There is no server to request deletion from
- Your behavioral patterns are your private knowledge

---

## How Learning Enhances Existing Features

### Relationship to Pattern Learning (v2.0+)

The v2.0 Pattern Learning system (see [[Pattern-Learning-Explained]]) extracts your coding identity (frameworks, languages, architecture preferences) using MACLA Beta-Binomial confidence scoring. That system is **not replaced** by v2.7.

Instead, v2.7 **wraps and enhances** it:

| Feature | v2.0 Pattern Learning | v2.7 Learning System |
|---------|----------------------|---------------------|
| Detects tech preferences | Yes (6 categories) | Yes (expanded, cross-project) |
| Confidence scoring | MACLA Beta-Binomial | Same, plus feedback signals |
| Affects recall ranking | No (identity context only) | **Yes (active re-ranking)** |
| Learns from feedback | No | **Yes (memory_used)** |
| Project-aware | No (global only) | **Yes (per-project context)** |
| Workflow detection | No | **Yes (sequence mining)** |
| Source quality | No | **Yes (per-tool scoring)** |
| ML model | No | **Yes (LightGBM, Phase 3)** |

If the v2.7 learning modules fail to load (missing dependencies, corrupted `learning.db`), the system falls back to v2.6 behavior automatically.

### Relationship to Knowledge Graph (v2.0+)

The knowledge graph (see [[Knowledge-Graph-Guide]]) organizes memories into clusters and discovers relationships. The learning system does not modify the graph. Instead, it uses graph cluster membership as one of many features for re-ranking.

### Relationship to Trust Scoring (v2.5+)

The trust scorer (see [[Architecture-V2.5]]) tracks agent trustworthiness. The learning system's source quality scoring is complementary — trust scoring catches malicious behavior, while source quality tracks usefulness. A trusted but low-quality source simply means "this tool is not malicious, but its memories are not very useful to you."

---

## Troubleshooting

### "Learning system not active"

**Check if learning is enabled:**
```bash
slm learning status
```

If it shows "disabled", check your `config.json`:
```bash
cat ~/.claude-memory/config.json | grep learning
```

**Enable it:**
```json
{
  "learning": {
    "enabled": true
  }
}
```

### "Phase 3 ML ranking not activating"

**Check feedback count:**
```bash
slm learning status
```

Phase 3 requires approximately 200 feedback signals. If you see "127 / 200 needed", keep using `memory_used` or `slm useful` to provide feedback.

**Check dependencies:**
```bash
python3 -c "import lightgbm; print(lightgbm.__version__)"
python3 -c "import scipy; print(scipy.__version__)"
```

If either import fails, install the learning dependencies:
```bash
pip install lightgbm>=4.0.0 scipy>=1.9.0
```

Or use the bundled requirements file:
```bash
pip install -r ~/.claude-memory/requirements-learning.txt
```

Phase 3 is optional. The system works well on Phase 2 (rule-based) without these dependencies.

### "Patterns seem wrong or outdated"

**Correct a specific pattern:**
```bash
slm patterns reset "Angular"
```

**Reset all learned patterns:**
```bash
slm patterns reset --all
```

**Or delete the entire learning database:**
```bash
rm ~/.claude-memory/learning.db
```

The system will rebuild its understanding from scratch on the next operation.

### "Learning database is large"

The learning database grows slowly over time. Typical sizes:

| Usage Period | Approximate Size |
|-------------|-----------------|
| 1 month | ~500 KB |
| 6 months | ~2 MB |
| 1 year | ~5 MB |

If size is a concern:
```bash
# Check current size
ls -lh ~/.claude-memory/learning.db

# Delete and start fresh (memories unaffected)
rm ~/.claude-memory/learning.db
```

### "Search results worse after v2.7"

If personalized ranking is producing worse results than before:

1. **Disable learning temporarily** to confirm it is the cause:
   ```json
   { "learning": { "enabled": false } }
   ```

2. **Reset learning data** if results improve without it:
   ```bash
   rm ~/.claude-memory/learning.db
   ```

3. **Provide more feedback.** The system needs feedback signals to calibrate. Use `slm useful` or the `memory_used` MCP tool after recalls.

4. **File an issue** at [GitHub Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) with details about your use case.

---

## Performance Impact

The learning system adds minimal overhead to core operations.

| Operation | Without Learning | With Learning | Overhead |
|-----------|-----------------|---------------|----------|
| `remember` | ~5ms | ~7ms | +2ms (preference extraction) |
| `recall` | ~65ms (500 memories) | ~72ms (500 memories) | +7ms (re-ranking) |
| `recall` with ML (Phase 3) | ~65ms | ~80ms | +15ms (model inference) |
| Learning DB update | N/A | ~3ms | Background, non-blocking |

All existing benchmarks (BM1-BM6) show no regression beyond the 10% tolerance threshold.

---

## Best Practices

### 1. Give Feedback Regularly

The more feedback you provide, the better the re-ranking becomes. In MCP-connected tools, this happens automatically. For CLI usage, make it a habit:

```bash
slm recall "database patterns"
# Read results, find useful one
slm useful 42
```

### 2. Use Tags Consistently

Tags help the project context detector understand your projects. Use consistent project tags:

```bash
slm remember "Use connection pooling" --tags ecommerce-api,database
slm remember "Rate limit at 100/min" --tags ecommerce-api,api
```

### 3. Use Profiles for Different Contexts

If you work on very different types of projects (e.g., Python backends and React frontends), profiles keep the learning signals clean:

```bash
slm switch-profile backend-work
# ... backend memories and learning ...

slm switch-profile frontend-work
# ... frontend memories and learning ...
```

### 4. Review Learned Patterns Periodically

Check what the system has learned every few weeks:

```bash
slm patterns list
slm learning status
```

Correct anything that looks off:
```bash
slm patterns reset "Angular"  # I don't use Angular anymore
```

---

## Related Pages

- [[Pattern-Learning-Explained]] - How v2.0 pattern detection works (enhanced by v2.7)
- [[Upgrading-to-v2.7]] - Step-by-step upgrade guide
- [[Architecture-V2.5]] - Event Bus, Trust Scoring, Agent Registry
- [[Performance-Benchmarks]] - Measured performance data
- [[CLI-Cheatsheet]] - Full command reference including new v2.7 commands
- [[MCP-Integration]] - IDE integration for automatic feedback
- [[Multi-Profile-Workflows]] - Using profiles with the learning system

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect - SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) | [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) | [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
