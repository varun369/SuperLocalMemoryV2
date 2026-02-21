# Upgrading to v2.7 — "Your AI Learns You"

**Step-by-step guide for upgrading from any previous version to SuperLocalMemory v2.7.0.** Your existing memories, graph, and settings are fully preserved.

---

## What's New in v2.7

SuperLocalMemory v2.7 adds a **personalized learning system** that makes recall smarter over time. Instead of returning results based on text matching alone, v2.7 learns your preferences and re-ranks results so the most relevant memories appear first.

### Key Additions

| Feature | What It Does |
|---------|-------------|
| **Intelligent Pattern Learning** | Learns your tech preferences (frameworks, languages, tools) across all projects |
| **Personalized Recall** | Search results re-ranked based on your patterns, current project, and workflow |
| **Multi-Channel Feedback** | Tell the AI which recalled memories were useful via `memory_used` MCP tool |
| **Source Quality Tracking** | System learns which tools produce your most useful memories |
| **Workflow Pattern Detection** | Detects your coding workflow patterns (docs, architecture, code, test) |
| **Three-Phase Adaptive Ranking** | Starts with rule-based boosting, graduates to ML ranking as feedback accumulates |
| **Local Engagement Metrics** | Track your memory system health locally (zero telemetry) |

### New MCP Tools

| Tool | Purpose |
|------|---------|
| `memory_used` | Report that a recalled memory was useful (primary feedback channel) |
| `get_learned_patterns` | View your learned technology preferences and their confidence scores |
| `correct_pattern` | Correct or suppress a pattern the system learned incorrectly |

### New CLI Commands

| Command | Purpose |
|---------|---------|
| `slm useful <id>` | Mark a recalled memory as useful (CLI feedback channel) |
| `slm patterns list` | View all learned patterns with confidence scores |
| `slm learning status` | Check learning system status, ranking phase, and feedback count |
| `slm engagement` | View local engagement metrics and memory system health |

### New Modules (11 files in `src/learning/`)

The learning system is implemented as a self-contained module with 11 files totaling 7,503 lines, backed by 229 passing unit tests.

---

## Upgrade Steps

### Option 1: npm (Recommended)

```bash
# Update to v2.7.0
npm update -g superlocalmemory

# Or install the exact version
npm install -g superlocalmemory@2.7.0
```

**What happens automatically:**
- Downloads v2.7.0 from npm
- Copies updated files to `~/.claude-memory/`
- Installs learning dependencies (`lightgbm`, `scipy`) if pip is available
- Creates `src/learning/` module directory
- Preserves all existing data (memories, graph, patterns, events, agents)
- No restart of running IDE sessions needed (changes take effect on next operation)

### Option 2: Git (Manual Install)

```bash
# Navigate to your clone
cd SuperLocalMemoryV2

# Pull latest
git pull origin main

# Re-run installer
./install.sh      # Mac/Linux
# or
.\install.ps1     # Windows
```

### Option 3: Fresh Install

If you do not have SuperLocalMemory installed yet, follow the [[Installation]] guide. v2.7 includes everything from previous versions.

---

## Learning Dependencies

v2.7 introduces two optional Python dependencies for the ML-based ranking phase:

| Package | Version | Purpose | Required? |
|---------|---------|---------|-----------|
| `lightgbm` | >= 4.0.0 | LambdaRank ML model for Phase 3 adaptive ranking | Optional |
| `scipy` | >= 1.9.0 | Statistical functions for feature extraction | Optional |

### Automatic Installation

Both the npm postinstall script and `install.sh` attempt to install these automatically via:

```bash
pip install -r requirements-learning.txt
```

### Manual Installation

If automatic installation fails (restricted environments, no pip, etc.):

```bash
pip install lightgbm>=4.0.0 scipy>=1.9.0
```

Or:

```bash
pip install -r ~/.claude-memory/requirements-learning.txt
```

### What If Dependencies Are Not Installed?

**The system works fine without them.** The learning system has three ranking phases:

| Phase | Dependencies Required | What You Get |
|-------|----------------------|-------------|
| Phase 1: Baseline | None | Initial ranking from existing memory patterns |
| Phase 2: Rule-Based | None | Tech preference boosting, project context, workflow patterns |
| Phase 3: ML Ranking | `lightgbm` + `scipy` | Full ML-powered personalized re-ranking |

Without `lightgbm` and `scipy`, the system caps at Phase 2 (rule-based boosting). This still provides personalized re-ranking — just without the ML model. There is **no degradation** of any feature that existed before v2.7.

---

## Backward Compatibility

### Guaranteed: No Breaking Changes

v2.7 maintains full backward compatibility with all previous versions.

| What | Guarantee |
|------|-----------|
| **Existing memories** | Untouched. No schema migration. No data modification. |
| **memory.db** | Same format. Same tables. Same columns. No changes. |
| **MCP tools** | All 9 existing tools (`remember`, `recall`, `search`, `fetch`, `list_recent`, `get_status`, `build_graph`, `switch_profile`, `backup_status`) work identically. 3 new learning tools added (12 total). |
| **CLI commands** | All existing commands unchanged. 4 new commands added. |
| **Skills** | All 6 existing skills work as before. 1 new skill added (`slm-show-patterns`). |
| **REST API** | All 28 endpoints unchanged. New learning endpoints added. |
| **Config** | Existing `config.json` works without changes. New `learning` section is optional. |
| **Python imports** | All existing imports work. New `src/learning/` module uses `try/except ImportError` for graceful fallback. |
| **Dashboard** | All 8 tabs work as before. |
| **Profiles** | Profile system unchanged. Learning adapts per-profile. |
| **Knowledge Graph** | Graph engine unchanged. Learning uses graph signals as features. |
| **Pattern Learning** | v2.0 pattern learner still works. v2.7 wraps and enhances it. |

### New Files Added

```
~/.claude-memory/
├── learning.db                              # NEW: Separate learning database
├── requirements-learning.txt                # NEW: Optional dependency list
└── src/
    └── learning/                            # NEW: Learning system module
        ├── __init__.py
        ├── learning_db.py                   # Separate SQLite database for behavioral data
        ├── cross_project_aggregator.py      # Layer 1: Tech preference tracking
        ├── project_context_manager.py       # Layer 2: Project detection
        ├── workflow_pattern_miner.py        # Layer 3: Workflow sequence mining
        ├── adaptive_ranker.py               # Three-phase adaptive ranking engine
        ├── feedback_collector.py            # Multi-channel feedback collection
        ├── feature_extractor.py             # Feature engineering for ML model
        ├── source_quality_scorer.py         # Per-source quality tracking
        ├── synthetic_bootstrap.py           # Day-1 synthetic model from existing data
        └── engagement_tracker.py            # Local engagement metrics
```

### Fallback Behavior

If any v2.7 component fails to load, the system falls back gracefully:

```python
# How v2.7 modules are imported (safe pattern)
try:
    from src.learning import adaptive_ranker
    USE_LEARNING = True
except ImportError:
    USE_LEARNING = False
    # System continues with v2.6 behavior
```

This means:
- If `src/learning/` is missing or corrupt: v2.6 behavior (pure text ranking)
- If `learning.db` is missing: created automatically on first use
- If `learning.db` is corrupt: deleted and recreated (memories unaffected)
- If `lightgbm` is not installed: Phase 2 (rule-based) only, no ML
- If `scipy` is not installed: Same as above

---

## Verify Your Upgrade

After upgrading, run these checks to confirm everything works.

### 1. Check Version

```bash
slm status
```

Expected: Shows `SuperLocalMemory V2.7.0` in the header.

### 2. Check Learning System

```bash
slm learning status
```

Expected output:
```
Learning System Status
======================

Ranking Phase:     Baseline (Phase 1)
Feedback Signals:  0 / 50 needed for rule-based phase
Model Status:      Synthetic bootstrap ready

Layer 1 (Tech Preferences):  Active - 0 patterns learned
Layer 2 (Project Context):   Active - No project detected
Layer 3 (Workflow Patterns):  Active - 0 sequences detected

Learning DB Size:  12 KB
Last Updated:      just now
```

### 3. Check Dependencies (Optional)

```bash
python3 -c "import lightgbm; print('LightGBM:', lightgbm.__version__)"
python3 -c "import scipy; print('SciPy:', scipy.__version__)"
```

If these fail, Phase 3 ML ranking will not be available, but everything else works.

### 4. Test Core Functionality

```bash
# Save a memory (should work identically to before)
slm remember "Testing v2.7 upgrade" --tags test,upgrade

# Recall (should work, with learning features active in background)
slm recall "v2.7 upgrade"

# Mark as useful (new v2.7 feature)
slm useful <memory_id_from_recall>

# View patterns (new v2.7 feature)
slm patterns list
```

### 5. Test MCP Integration

In Claude Desktop, Cursor, or Windsurf:

1. Start a new conversation
2. Ask: "What tools do you have access to?"
3. Verify you see `memory_used`, `get_learned_patterns`, and `correct_pattern` alongside existing tools
4. Test: "Remember that I prefer FastAPI for REST APIs"
5. Test: "What do I use for APIs?" (should recall and potentially trigger `memory_used`)

---

## Rollback Instructions

If you need to revert to a previous version for any reason:

### npm Rollback

```bash
# Install the specific previous version
npm install -g superlocalmemory@2.6.5

# Verify rollback
slm status
```

### Git Rollback

```bash
cd SuperLocalMemoryV2

# Check out the v2.6.5 tag
git checkout v2.6.5

# Re-run installer
./install.sh
```

### What Happens on Rollback

- **Memories:** Completely unaffected (memory.db is unchanged by v2.7)
- **Learning data:** `learning.db` remains on disk but is ignored by older versions
- **New CLI commands:** `slm useful`, `slm patterns`, `slm learning`, `slm engagement` will no longer be available
- **New MCP tools:** `memory_used`, `get_learned_patterns`, `correct_pattern` will no longer appear
- **Recall behavior:** Returns to pure text-relevance ranking (no personalization)

### Cleaning Up After Rollback

If you want to fully remove v2.7 artifacts after rolling back:

```bash
# Remove learning database (optional, does not affect memories)
rm ~/.claude-memory/learning.db

# Remove learning module (optional)
rm -rf ~/.claude-memory/src/learning/

# Remove learning requirements (optional)
rm ~/.claude-memory/requirements-learning.txt
```

None of these deletions affect your memories, graph, patterns, events, or any other existing data.

---

## Upgrading from Specific Versions

### From v2.6.x

Direct upgrade. No special steps needed. Follow the standard upgrade procedure above.

### From v2.5.x

Direct upgrade. The Event Bus, Agent Registry, and Trust Scoring features from v2.5 are fully preserved and enhanced by v2.7's learning system.

### From v2.4.x or earlier

Direct upgrade. The installer handles all intermediate changes. Your memories, graph, and MACLA-based patterns are preserved.

### From v1.x

Follow the [[Installation]] guide for a fresh install. Then use the migration tool:

```bash
python3 ~/.claude-memory/migrate_v1_to_v2.py
```

---

## FAQ

### Does v2.7 modify my existing memories?

No. v2.7 does not alter `memory.db` in any way. It creates a separate `learning.db` file for all behavioral data.

### Will my search results change immediately?

Slightly. Phase 1 (baseline) creates a synthetic model from your existing memory patterns, so there may be minor re-ranking differences from day one. The changes are designed to be improvements — surfacing more relevant results. If results seem worse, you can disable learning (see [[Pattern-Learning-Explained#disabling-learning]]).

### Do I need to provide feedback for the system to work?

Not strictly. Phase 1 works without any feedback. But the system gets significantly better with feedback. In MCP-connected IDEs, feedback happens automatically — no action needed on your part.

### Is `lightgbm` safe to install?

Yes. LightGBM is an open-source gradient boosting framework by Microsoft, widely used in production ML systems. It runs entirely locally and makes no network calls. v2.7 uses it for local model training only.

### How much disk space does the learning database use?

Typically under 5 MB after a year of use. See the [[Pattern-Learning-Explained#troubleshooting]] section for details.

### Can I use v2.7 without the learning features?

Yes. Set `"learning": { "enabled": false }` in `config.json`. Everything works exactly as v2.6.

---

## Related Pages

- [[Pattern-Learning-Explained]] - Complete guide to the learning system
- [[Pattern-Learning-Explained]] - How v2.0 pattern detection works (enhanced by v2.7)
- [[Installation]] - Fresh installation guide
- [[CLI-Cheatsheet]] - Full command reference
- [[Performance-Benchmarks]] - Measured performance data

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect - SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) | [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) | [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
