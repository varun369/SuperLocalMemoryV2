# Pattern Learner - Identity Profile Extraction

## Overview

The Pattern Learner is Layer 4 of the SuperLocalMemory system. It automatically learns user preferences, coding style, and terminology from stored memories using local TF-IDF and heuristic analysis.

**No external APIs. All processing is local.**

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ PatternLearner                                          │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ Frequency        │  │ Context          │           │
│  │ Analyzer         │  │ Analyzer         │           │
│  └──────────────────┘  └──────────────────┘           │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ Terminology      │  │ Confidence       │           │
│  │ Learner          │  │ Scorer           │           │
│  └──────────────────┘  └──────────────────┘           │
│                                                         │
│  ┌──────────────────┐                                  │
│  │ Pattern Store    │                                  │
│  └──────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. FrequencyAnalyzer
**Purpose:** Detect technology preferences via frequency counting

**Categories tracked:**
- Frontend frameworks (React, Next.js, Vue, Angular, Svelte)
- Backend frameworks (Express, FastAPI, Django, Flask)
- Databases (PostgreSQL, MySQL, MongoDB, Redis)
- State management (Redux, Context, Zustand)
- Styling (Tailwind, CSS Modules, Styled Components)
- Languages (Python, JavaScript, TypeScript, Go, Rust)
- Deployment (Docker, Kubernetes, Vercel, AWS)
- Testing (Jest, Pytest, Vitest, Cypress)

**Algorithm:**
1. Count keyword mentions across all memories
2. Calculate relative frequency (top choice vs others)
3. Create pattern if confidence > 60% and count >= 3

**Example output:**
```
Pattern: frontend_framework
Value: "Next.js over React"
Confidence: 85%
Evidence: 12 memories
```

### 2. ContextAnalyzer
**Purpose:** Detect coding style patterns from context

**Patterns tracked:**
- **Optimization priority:** Performance vs Readability
- **Error handling:** Explicit vs Permissive
- **Testing approach:** Comprehensive vs Minimal
- **Code organization:** Modular vs Monolithic

**Algorithm:**
1. Define indicator keywords for each style dimension
2. Count mentions in memory contexts
3. Determine dominant style if confidence > 65%

**Example output:**
```
Pattern: optimization_priority
Value: "Performance over readability"
Confidence: 90%
Evidence: 15 memories
```

### 3. TerminologyLearner
**Purpose:** Learn user-specific definitions of ambiguous terms

**Terms tracked:**
- optimize, refactor, clean, simple
- mvp, prototype, scale, production-ready
- fix, improve, update, enhance

**Algorithm:**
1. Extract 100-char context window around each term mention
2. Analyze co-occurring words across contexts
3. Apply heuristic rules to determine meaning
4. Require 3+ examples for confidence

**Example output:**
```
Pattern: optimize
Value: "Performance optimization (speed/latency)"
Confidence: 90%
Evidence: 15 memories
```

### 4. ConfidenceScorer
**Purpose:** Calculate reliability scores for patterns

**Formula:**
```python
confidence = (evidence_count / total_memories) * recency_bonus * distribution_factor

Where:
- evidence_count: Number of memories supporting pattern
- total_memories: Total memories in database
- recency_bonus: 1.2 if >50% evidence is from last 30 days, else 1.0
- distribution_factor: 1.1 if memories span >7 days, 0.8 if <3 memories
```

**Conservative by design:** Low confidence with small datasets is correct behavior.

### 5. PatternStore
**Purpose:** Persist patterns to database

**Tables:**
- `identity_patterns`: Pattern definitions with confidence scores
- `pattern_examples`: Representative excerpts showing patterns

## Usage

### Command Line Interface

```bash
# Full pattern update (run weekly)
python pattern_learner.py update

# List learned patterns
python pattern_learner.py list [min_confidence]
# Example: python pattern_learner.py list 0.7  # Show patterns with >70% confidence

# Get context for Claude injection
python pattern_learner.py context [min_confidence]
# Example: python pattern_learner.py context 0.6

# Show statistics
python pattern_learner.py stats
```

### Python API

```python
from pattern_learner import PatternLearner

learner = PatternLearner()

# Full pattern analysis
counts = learner.weekly_pattern_update()
# Returns: {'preferences': 5, 'styles': 3, 'terminology': 4}

# Incremental update for new memory
learner.on_new_memory(memory_id=42)

# Query patterns
patterns = learner.get_patterns(min_confidence=0.7)

# Get formatted context for Claude
context = learner.get_identity_context(min_confidence=0.7)
```

## Example Output

### Pattern List
```
Type            Category     Pattern                        Confidence   Evidence
-----------------------------------------------------------------------------------------------
style           general      Optimization Priority: Perfo...    90%        15
preference      frontend     Frontend Framework: Next.js...    85%        12
preference      backend      Database: PostgreSQL              72%        8
terminology     general      Optimize: Performance optimi...    90%        15
style           general      Error Handling: Explicit err...    78%        9
```

### Claude Context Injection
```markdown
## Working with User - Learned Patterns

**Technology Preferences:**
- **Frontend Framework:** Next.js over React (confidence: 85%, 12 examples)
- **Database:** PostgreSQL (confidence: 72%, 8 examples)
- **State Management:** Redux for complex, Context for simple (confidence: 68%, 7 examples)

**Coding Style:**
- **Optimization Priority:** Performance over readability (confidence: 90%, 15 examples)
- **Error Handling:** Explicit error boundaries (confidence: 78%, 9 examples)
- **Code Organization:** Modular organization (confidence: 75%, 11 examples)

**Terminology:**
- **Optimize:** Performance optimization (speed/latency) (confidence: 90%, 15 examples)
- **Refactor:** Architecture change, not just renaming (confidence: 82%, 10 examples)
- **MVP:** Core features only, no polish (confidence: 85%, 8 examples)
```

## Confidence Calibration

### Small Datasets (<20 memories)
- **Expected confidence:** 10-40%
- **Reason:** Limited evidence means low certainty
- **Recommendation:** Use min_confidence=0.1 for exploration

### Medium Datasets (20-100 memories)
- **Expected confidence:** 40-70%
- **Reason:** Patterns emerging but still developing
- **Recommendation:** Use min_confidence=0.5 for reliable patterns

### Large Datasets (>100 memories)
- **Expected confidence:** 70-95%
- **Reason:** Strong evidence across time
- **Recommendation:** Use min_confidence=0.7 for high-confidence patterns

**Note:** The system is designed to be conservative. Low confidence with small datasets is correct behavior, not a bug.

## Pattern Update Schedule

### Incremental (on `/remember`)
- Quick check for pattern updates
- For datasets >50 memories, defers to weekly update
- For small datasets, triggers full update

### Weekly Consolidation
- Full re-analysis of all memories
- Recommended cron job:
  ```bash
  # Every Sunday at 2 AM
  0 2 * * 0 cd ~/.claude-memory && python3 pattern_learner.py update >> pattern_updates.log 2>&1
  ```

## Integration with AI Assistants

### Context Injection
The `get_identity_context()` method formats patterns for any AI assistant's context window:

```python
# In your AI assistant integration:
learner = PatternLearner()
identity_context = learner.get_identity_context(min_confidence=0.7)

# Inject into system prompt or context (works with Claude, GPT, or any assistant)
prompt = f"""
{identity_context}

[Rest of your prompt...]
"""
```

### Benefits
1. **Personalized responses:** AI understands your technology preferences
2. **Consistent terminology:** AI uses terms the way you define them
3. **Style matching:** AI respects your coding style priorities
4. **Efficient communication:** No need to repeat preferences

**Works with:** Claude CLI, GPT, local LLMs, or any AI assistant that accepts context.

## Implementation Details

### Technology Stack
- **Language:** Python 3.8+
- **Database:** SQLite3 (local)
- **NLP:** sklearn TfidfVectorizer (optional, local)
- **No external APIs**

### Files
- `pattern_learner.py` - Main implementation (850 lines)
- `memory.db` - SQLite database (includes pattern tables)
- Schema tables:
  - `identity_patterns` - Pattern definitions
  - `pattern_examples` - Representative excerpts

### Performance
- **Full analysis (100 memories):** ~2-3 seconds
- **Query patterns:** <10ms
- **Database size:** ~1KB per pattern

## Security & Privacy

✅ **No external API calls**
✅ **All data stays local** (~/.claude-memory/)
✅ **SQL injection protected** (parameterized queries)
✅ **No credentials stored**
✅ **No network access required**

## Limitations

1. **English-only:** Pattern detection optimized for English text
2. **Technical domains:** Works best with technical/coding memories
3. **Minimum memories:** Requires 3+ mentions for pattern detection
4. **Confidence calibration:** Conservative scoring (by design)

## Troubleshooting

### "No patterns learned yet"
- **Cause:** Not enough memories or technical content
- **Solution:** Add 10-20 memories with technical details

### Low confidence scores
- **Cause:** Small dataset or mixed evidence
- **Solution:** Normal behavior. Use lower threshold (0.1-0.3) or add more memories

### Wrong preference detected
- **Cause:** More mentions of alternative technology
- **Solution:** Add more memories showing correct preference

### Pattern not updating
- **Cause:** Weekly update not run
- **Solution:** Run `python pattern_learner.py update` manually

## Testing

Sample memories for testing pattern detection:

```bash
# Add sample memories
python memory_store.py add "Built with Next.js for better performance" --tags nextjs
python memory_store.py add "Using Next.js on all new projects" --tags nextjs
python memory_store.py add "Optimized API from 200ms to 50ms" --tags performance
python memory_store.py add "Performance is critical for UX" --tags performance
python memory_store.py add "When I say optimize, I mean make it faster" --tags terminology

# Run pattern learning
python pattern_learner.py update

# Check results
python pattern_learner.py list 0.1
python pattern_learner.py context 0.1
```

## Future Enhancements

Potential improvements (not yet implemented):

1. **True incremental updates:** Update only affected patterns
2. **Pattern decay:** Reduce confidence over time if not reinforced
3. **Conflict detection:** Identify contradicting patterns
4. **Cross-project patterns:** Detect project-specific vs global preferences
5. **Multi-language support:** Extend beyond English
6. **Pattern visualization:** Web UI for pattern exploration

## References

Architecture documentation:
- `docs/architecture/05-pattern-learner.md` - Detailed algorithm specification
- `docs/architecture/01-database-schema.md` - Pattern table schemas
- `docs/COMPREHENSIVE-ARCHITECTURE.md` - System overview

Research inspiration:
- xMemory (arxiv.org/abs/2602.02007) - Semantic memory components
- A-RAG - Agentic multi-level retrieval

## License

Part of SuperLocalMemory system. See main project LICENSE.

---

**Implementation Status:** ✅ Complete and tested

**Last Updated:** 2026-02-05
