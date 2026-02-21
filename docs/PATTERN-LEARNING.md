# Pattern Learning

## Overview

The Pattern Learner is Layer 4 of the SuperLocalMemory system. It automatically learns user preferences, coding style, and terminology from stored memories — all processed locally with no external API calls.

**No external APIs. All processing is local.**

> For technical details on the learning algorithms, see our published research: https://zenodo.org/records/18709670

---

## What It Learns

Pattern learning analyzes your saved memories and builds a profile of your preferences across multiple dimensions:

- **Technology preferences** — Which frameworks, languages, and tools appear most often in your memories
- **Architecture choices** — Your preferred patterns (e.g., REST vs GraphQL, microservices vs monolith)
- **Security approaches** — Your go-to authentication and authorization patterns
- **Coding style** — Performance vs readability, testing approach, code organization
- **Domain terminology** — How you define common terms in your project context

Each detected preference gets a confidence score based on the supporting evidence. The system is conservative by design — low confidence with small datasets is correct behavior, not a bug.

---

## Usage

### Command Line Interface

```bash
# Full pattern update (run weekly or after bulk imports)
python pattern_learner.py update

# List learned patterns
python pattern_learner.py list [min_confidence]
# Example: python pattern_learner.py list 0.7

# Get context formatted for AI assistant injection
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

# Get formatted context for AI injection
context = learner.get_identity_context(min_confidence=0.7)
```

---

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

### AI Context Injection

```markdown
## Working with User - Learned Patterns

**Technology Preferences:**
- **Frontend Framework:** Next.js over React (confidence: 85%, 12 examples)
- **Database:** PostgreSQL (confidence: 72%, 8 examples)

**Coding Style:**
- **Optimization Priority:** Performance over readability (confidence: 90%, 15 examples)
- **Error Handling:** Explicit error boundaries (confidence: 78%, 9 examples)

**Terminology:**
- **Optimize:** Performance optimization (speed/latency) (confidence: 90%, 15 examples)
```

---

## Confidence Calibration

| Dataset Size | Expected Confidence | Recommended Threshold |
|-------------|--------------------|-----------------------|
| Under 20 memories | 10-40% | Use 0.1 for exploration |
| 20-100 memories | 40-70% | Use 0.5 for reliable patterns |
| Over 100 memories | 70-95% | Use 0.7 for high-confidence patterns |

The system is designed to be conservative. Low confidence with small datasets is correct behavior.

---

## Pattern Update Schedule

### Incremental (on `/remember`)
- Quick check for pattern updates on every new memory
- For large datasets, defers to weekly consolidation

### Weekly Consolidation
- Full re-analysis of all memories
- Recommended cron job:
  ```bash
  # Every Sunday at 2 AM
  0 2 * * 0 cd ~/.claude-memory && python3 pattern_learner.py update >> pattern_updates.log 2>&1
  ```

---

## Integration with AI Assistants

### Automatic Context Injection

The `get_identity_context()` method formats patterns for any AI assistant's context window:

```python
learner = PatternLearner()
identity_context = learner.get_identity_context(min_confidence=0.7)

# Inject into system prompt or context (works with Claude, GPT, or any assistant)
prompt = f"""
{identity_context}

[Rest of your prompt...]
"""
```

**Works with:** Claude CLI, GPT, local LLMs, or any AI assistant that accepts context.

### Benefits
1. **Personalized responses:** AI understands your technology preferences
2. **Consistent terminology:** AI uses terms the way you define them
3. **Style matching:** AI respects your coding style priorities
4. **Efficient communication:** No need to repeat preferences every session

---

## Privacy & Security

- **No external API calls** — all processing is local
- **All data stays local** — stored in `~/.claude-memory/`
- **SQL injection protected** — parameterized queries throughout
- **No credentials stored**
- **No network access required**

---

## Limitations

1. **English-optimized:** Pattern detection works best with English text
2. **Technical domains:** Works best with technical and coding memories
3. **Minimum samples:** Requires a few mentions before a pattern is detected
4. **Conservative scoring:** Low confidence with small datasets is by design

---

## Troubleshooting

### "No patterns learned yet"
- **Cause:** Not enough memories or technical content
- **Solution:** Add 10-20 memories with technical details about your preferences

### Low confidence scores
- **Cause:** Small dataset or mixed evidence
- **Solution:** Normal behavior. Lower the threshold (0.1-0.3) or add more memories

### Wrong preference detected
- **Cause:** More mentions of alternative technology than your true preference
- **Solution:** Add more memories explicitly stating your correct preference

### Pattern not updating
- **Cause:** Weekly update not run
- **Solution:** Run `python pattern_learner.py update` manually

---

## Testing

Sample memories for verifying pattern detection:

```bash
# Add sample memories
python memory_store.py add "Built with Next.js for better performance" --tags nextjs
python memory_store.py add "Using Next.js on all new projects" --tags nextjs
python memory_store.py add "Optimized API from slow to fast" --tags performance
python memory_store.py add "Performance is critical for UX" --tags performance
python memory_store.py add "When I say optimize, I mean make it faster" --tags terminology

# Run pattern learning
python pattern_learner.py update

# Check results
python pattern_learner.py list 0.1
python pattern_learner.py context 0.1
```

---

## License

Part of SuperLocalMemory system. See main project LICENSE.

---

**Implementation Status:** Complete and tested

**Last Updated:** 2026-02-05
