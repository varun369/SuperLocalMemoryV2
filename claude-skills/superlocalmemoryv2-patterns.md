# SuperLocalMemory V2: Patterns

Learn and display coding patterns, preferences, and style from your memories.

## Usage

```
/superlocalmemoryv2:patterns [update|list|context] [confidence_threshold]
```

## What This Skill Does

Analyzes your memories to learn your coding patterns:
- Extracts framework preferences
- Identifies coding style preferences
- Learns terminology patterns
- Builds identity profile with confidence scoring

## Examples

```bash
# Update patterns from current memories
/superlocalmemoryv2:patterns update

# List all patterns (10%+ confidence)
/superlocalmemoryv2:patterns list 0.1

# Get high-confidence patterns for context (50%+ confidence)
/superlocalmemoryv2:patterns context 0.5

# View pattern statistics
/superlocalmemoryv2:patterns stats
```

## Implementation

This skill runs:
```bash
cd ~/.claude-memory && python3 pattern_learner.py $1 ${2:-0.1}
```

## Pattern Categories

**1. Framework Preferences**
- Frontend: React, Vue, Angular
- Backend: FastAPI, Django, Flask
- Confidence based on frequency

**2. Coding Style**
- "Performance over readability"
- "Type safety important"
- "Test-driven development"

**3. Terminology**
- Preferred technical terms
- Domain-specific language
- Naming conventions

**4. Technology Stack**
- Languages: Python, JavaScript, TypeScript
- Tools: Docker, Kubernetes, Git
- Platforms: AWS, Azure, GCP

## Output Format

### Update Output
```
Updating patterns from memories...
Analyzed 20 memories
Extracted 15 patterns
Updated confidence scores
Pattern learning complete!
```

### List Output
```
Learned Patterns (confidence >= 10%):

Framework Preferences:
- React: 60% (appears in 12/20 memories)
- FastAPI: 35% (appears in 7/20 memories)

Coding Style:
- Performance optimization: 45% (appears in 9/20 memories)
- Type safety: 30% (appears in 6/20 memories)

Technology Stack:
- Docker: 55% (appears in 11/20 memories)
- Python: 75% (appears in 15/20 memories)
```

### Context Output
```
# Identity Profile (High Confidence Patterns)

**Framework Preferences:**
- Frontend: React (60% confidence)
- Backend: Python + FastAPI (75% / 35%)

**Coding Philosophy:**
- Prioritizes performance and optimization
- Values type safety and testing

**Technology Stack:**
- Containers: Docker (55% confidence)
- Languages: Python-first approach (75%)
```

## When to Update Patterns

Update patterns:
- After adding 20+ new memories
- Weekly or bi-weekly
- When coding style changes
- Before context generation for AI assistants

## Prerequisites

- SuperLocalMemory V2 installed
- At least 5 memories for meaningful patterns
- Python 3.8+ available

## Use Cases

**AI Context:**
- Provide patterns to AI for personalized responses
- Share coding preferences automatically
- Maintain consistent style across sessions

**Self-Reflection:**
- Understand your coding evolution
- Identify dominant technologies
- Track preference changes over time

**Documentation:**
- Auto-generate personal coding guidelines
- Create team onboarding materials
- Document technology stack choices

## Integration with Other Skills

Patterns complement:
- `/superlocalmemoryv2:graph-stats` - Thematic organization
- `/superlocalmemoryv2:search` - Find supporting memories
- Profile switching - Different patterns per context

## Pro Tips

- Higher confidence thresholds (0.5-0.7) for critical decisions
- Lower thresholds (0.1-0.3) for exploration and discovery
- Update patterns regularly to track evolution
- Use context output for `.claude-memory/context.md`

---

**Part of SuperLocalMemory V2 - Standalone intelligent memory system**
