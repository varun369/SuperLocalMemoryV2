# Pattern Learning Explained

**How pattern learning works in SuperLocalMemory V2** - Multi-dimensional identity extraction with confidence scoring, all processed locally for privacy.

---

## What is Pattern Learning?

Pattern learning is SuperLocalMemory's ability to **automatically detect your coding preferences and style** by analyzing the memories you save. It learns what frameworks you prefer, how you write code, what testing approaches you use, and more.

**Based on xMemory (Stanford Research):** Identity pattern learning from interactions with adaptive confidence scoring.

**Example:**
```
After saving 50 memories, SuperLocalMemory learns:

Your Coding Identity:
- Framework preference: React (73% confidence)
- Style: Performance over readability (58% confidence)
- Testing: Jest + React Testing Library (65% confidence)
- API style: REST over GraphQL (81% confidence)
- Language: Python for backends (65% confidence)
```

**Why this matters:** Your AI assistant can automatically match your preferences without you re-explaining them every session.

---

## How It Works

### Multi-Dimensional Analysis

Pattern learning analyzes **six categories** of patterns:

#### 1. Framework Preferences

**What it detects:**
- Frontend: React, Vue, Angular, Svelte, Next.js, Nuxt, etc.
- Backend: FastAPI, Flask, Django, Express, NestJS, etc.
- Mobile: React Native, Flutter, SwiftUI, etc.

**How it works:**
```
Scans memories for framework mentions
Counts frequency of each framework
Calculates confidence = (mentions of X / total framework mentions)

Example:
- React: 15 mentions
- Vue: 3 mentions
- Angular: 2 mentions
Total: 20 mentions

React confidence: 15/20 = 75%
```

**Output:**
```
Framework preference: React (75% confidence)
```

#### 2. Language Preferences

**What it detects:**
- Python, JavaScript, TypeScript, Go, Rust, Java, C#, etc.
- Context-aware (API vs frontend vs backend)

**Example:**
```
Memories analyzed:
- "Use Python for REST APIs" → Python + backend context
- "TypeScript for React components" → TypeScript + frontend context
- "Python data processing pipeline" → Python + data context

Result:
- Language: Python for backends (73% confidence)
- Language: TypeScript for frontend (65% confidence)
```

#### 3. Architecture Patterns

**What it detects:**
- Microservices vs monolith
- Serverless vs traditional servers
- Event-driven architecture
- REST vs GraphQL
- SQL vs NoSQL

**Example:**
```
Memories:
- "Split user service into microservice"
- "Avoid monolith, use microservices"
- "Microservices for scalability"

Result:
Architecture preference: Microservices (58% confidence)
```

#### 4. Security Approaches

**What it detects:**
- JWT vs sessions vs OAuth
- API keys vs certificates
- Authentication patterns
- Authorization strategies

**Example:**
```
Memories:
- "JWT tokens expire after 24h"
- "Use JWT for API authentication"
- "JWT refresh token strategy"

Result:
Security: JWT tokens (81% confidence)
```

#### 5. Coding Style Priorities

**What it detects:**
- Performance vs readability
- TDD vs pragmatic testing
- Functional vs OOP
- Strict typing vs dynamic

**Example:**
```
Memories:
- "Optimize for performance"
- "Cache aggressively for speed"
- "Performance is critical here"
- "Readable code is important"

Result:
Style: Performance over readability (60% confidence)
```

#### 6. Domain Terminology

**What it detects:**
- Project-specific terms
- Industry vocabulary (fintech, healthcare, e-commerce)
- Team conventions
- Internal acronyms

**Example:**
```
Memories in fintech project:
- "KYC verification flow"
- "AML compliance check"
- "Transaction reconciliation"

Result:
Domain: Fintech (KYC, AML, reconciliation)
```

---

## Confidence Scoring Algorithm

### How Confidence is Calculated

**Frequency-based scoring:**
```python
confidence = (pattern_mentions / category_total_mentions)
```

**With recency weighting:**
```python
recent_boost = 1.2 if last_seen < 7_days else 1.0
confidence = (pattern_mentions / category_total_mentions) × recent_boost
```

**With statistical significance:**
```python
if pattern_mentions < 3:
    confidence *= 0.5  # Low confidence if too few samples
```

### Confidence Levels

| Confidence | Meaning | Threshold |
|------------|---------|-----------|
| **>80%** | Very strong preference | Always report |
| **60-80%** | Strong preference | Always report |
| **40-60%** | Moderate preference | Report if >50% |
| **30-40%** | Weak preference | Report only if significant |
| **<30%** | Too weak to report | Filtered out |

**Default reporting threshold: 50%**

### Example Calculation

```
Scenario: Framework preferences

Memories:
- React: 15 mentions (last: 2 days ago)
- Vue: 3 mentions (last: 45 days ago)
- Angular: 2 mentions (last: 90 days ago)

Calculations:
React confidence:
  Base: 15 / 20 = 75%
  Recency boost: 1.2 (last seen < 7 days)
  Final: 75% × 1.2 = 90% (capped at 100%)

Vue confidence:
  Base: 3 / 20 = 15%
  Recency: 1.0 (last seen > 7 days)
  Final: 15% (below threshold, not reported)

Output:
Framework preference: React (90% confidence)
```

---

## Learning Process

### Automatic Learning

**Triggered on every `remember` operation:**
```bash
slm remember "We use FastAPI for REST APIs" --tags python,backend
```

**What happens:**
1. Content saved to database
2. Pattern learner extracts entities
3. Updates pattern frequency counts
4. Recalculates confidence scores
5. Updates learned_patterns table

**No manual action required.**

### Manual Update

```bash
# Force pattern update
python3 ~/.claude-memory/pattern_learner.py update
```

**When to use:**
- After bulk imports
- After database restore
- When patterns seem stale

### Get Identity Context

```bash
# Get identity context (confidence threshold: 0.5)
python3 ~/.claude-memory/pattern_learner.py context 0.5
```

**Output:**
```
Your Coding Identity:

Framework Preferences:
- React (73% confidence)
- FastAPI (68% confidence)

Language Preferences:
- Python for backends (65% confidence)
- TypeScript for frontend (58% confidence)

Architecture Patterns:
- Microservices (58% confidence)
- REST over GraphQL (81% confidence)

Security Approaches:
- JWT tokens (81% confidence)

Coding Style:
- Performance over readability (58% confidence)
- Async/await preferred (72% confidence)

Testing Preferences:
- Jest + React Testing Library (65% confidence)
- Pytest for Python (71% confidence)
```

---

## Identity Context Generation

### What is Identity Context?

**Identity context** is a formatted text summary of your learned patterns that can be injected into AI assistant prompts.

### Format

```
Your Coding Identity (learned from 247 memories):

- Framework preference: React (73% confidence)
- Backend: FastAPI (68% confidence)
- Style: Performance-focused (58% confidence)
- Testing: Jest + Pytest (65% confidence)
- API style: REST over GraphQL (81% confidence)
- Security: JWT tokens (81% confidence)

Based on this, when writing code:
1. Use React for frontend
2. Use FastAPI for APIs
3. Optimize for performance
4. Write tests with Jest/Pytest
5. Design REST APIs
6. Use JWT for auth
```

### Using with AI Assistants

**Manual injection:**
```bash
# Get context
context=$(python3 ~/.claude-memory/pattern_learner.py context 0.5)

# Use with Claude
echo "$context\n\nNow help me build a new API endpoint."
```

**Automatic injection (Cursor/Claude Desktop):**
- MCP server automatically includes identity context
- No manual action needed

**Aider integration:**
```bash
# aider-smart wrapper includes context automatically
aider-smart
```

---

## Adaptive Learning

### Patterns Evolve Over Time

**Scenario 1: New preference emerges**
```
Month 1: React (90% confidence)
Month 2: React (85%), Vue (15%)
Month 3: React (75%), Vue (25%)
Month 4: React (55%), Vue (45%)

Pattern learning adapts: "Shifting from React to Vue"
```

**Scenario 2: Temporary spike**
```
Week 1-4: Python (90%)
Week 5: JavaScript spike (10 mentions in 1 week)
Week 6: Back to Python

Pattern learning recognizes: "JavaScript was temporary, Python is core"
```

### Recency Weighting

**Recent patterns weighted more heavily:**
```python
if last_seen < 7_days:
    weight = 1.2  # 20% boost
elif last_seen < 30_days:
    weight = 1.0
else:
    weight = 0.8  # 20% penalty
```

**Prevents stale patterns from dominating.**

### Context Decay

**Old patterns gradually fade:**
```python
if last_seen > 180_days:
    confidence *= 0.5  # Reduce confidence by half
```

**Ensures current preferences dominate.**

---

## Privacy & Security

### 100% Local Processing

**No data leaves your machine:**
- All pattern learning happens locally
- No external API calls
- No telemetry
- No cloud sync

### Data Storage

**Stored in SQLite database:**
```sql
CREATE TABLE learned_patterns (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    pattern TEXT NOT NULL,
    confidence REAL NOT NULL,
    frequency INTEGER NOT NULL,
    last_seen TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

**Location:** `~/.claude-memory/memory.db`

**Access control:** Standard filesystem permissions

---

## Use Cases

### 1. Onboarding New AI Sessions

**Without pattern learning:**
```
You: "Help me build an API"
AI: "Sure! Which framework? Which language? REST or GraphQL?"
You: *explains preferences again*
```

**With pattern learning:**
```
You: "Help me build an API"
AI: [Reads identity context: FastAPI, Python, REST, JWT]
AI: "I'll create a FastAPI REST endpoint with JWT auth"
```

### 2. Team Consistency

**Scenario:** Multiple team members using SuperLocalMemory

```bash
# Share learned patterns
slm remember "Team uses React + TypeScript" --tags team-standard
slm remember "Team prefers REST over GraphQL" --tags team-standard
slm remember "Team uses Jest for testing" --tags team-standard

# Pattern learning ensures consistent recommendations
```

### 3. Project-Specific Patterns

**Use profiles for different projects:**
```bash
# Work project (React + FastAPI)
slm switch-profile work
slm remember "Work project uses React + FastAPI"

# Personal project (Vue + Flask)
slm switch-profile personal
slm remember "Personal project uses Vue + Flask"

# Each profile learns separate patterns
```

### 4. Debugging Assistance

**Pattern learning knows your typical patterns:**
```
AI: "You typically use JWT auth, but this endpoint uses sessions.
     Was this intentional or should I fix it?"
```

---

## Advanced Features

### Custom Confidence Threshold

```bash
# High confidence only (80%+)
python3 ~/.claude-memory/pattern_learner.py context 0.8

# Low confidence included (30%+)
python3 ~/.claude-memory/pattern_learner.py context 0.3
```

### List All Patterns

```bash
# View all learned patterns (raw)
python3 ~/.claude-memory/pattern_learner.py list
```

**Output:**
```
Category: frameworks
  React: 73% (15 mentions, last: 2 days ago)
  Vue: 15% (3 mentions, last: 45 days ago)

Category: languages
  Python: 65% (22 mentions, last: 1 day ago)
  TypeScript: 58% (18 mentions, last: 3 days ago)

Category: architecture
  microservices: 58% (12 mentions, last: 5 days ago)
  REST: 81% (27 mentions, last: 1 day ago)
```

### Reset Patterns

```bash
# Clear all learned patterns
python3 ~/.claude-memory/pattern_learner.py reset

# Confirmation required
Are you sure? This will delete all learned patterns. [y/N]: y

✓ Patterns reset successfully
```

---

## Troubleshooting

### "No patterns learned"

**Cause:** Not enough memories with relevant content

**Solution:**
```bash
# Check memory count
slm status

# Need at least 20-30 memories for meaningful patterns
# Add more memories about your preferences
slm remember "I prefer React for frontend"
slm remember "I use Python for backend APIs"
slm remember "I prefer performance over readability"
```

### "Patterns seem wrong"

**Cause:** Conflicting or outdated memories

**Solution:**
```bash
# Review learned patterns
python3 ~/.claude-memory/pattern_learner.py list

# Delete outdated memories
sqlite3 ~/.claude-memory/memory.db \
  "DELETE FROM memories WHERE created_at < date('now', '-180 days');"

# Force pattern update
python3 ~/.claude-memory/pattern_learner.py update
```

### "Confidence too low"

**Cause:** Not enough samples or conflicting signals

**Solution:**
```bash
# Add more memories about your preferences
slm remember "I always use React for frontend" --tags preference
slm remember "React is my go-to framework" --tags preference

# Or lower confidence threshold
python3 ~/.claude-memory/pattern_learner.py context 0.3
```

---

## Best Practices

### 1. Be Explicit About Preferences

**Good:**
```bash
slm remember "I prefer React over Vue for this project" --tags preference
```

**Poor:**
```bash
slm remember "Used React" --tags todo
```

### 2. Tag Preferences

```bash
slm remember "Team standard: Use TypeScript" --tags team-standard,preference
```

**Benefits:**
- Easier to find later
- Higher confidence (tagged = intentional)

### 3. Update Patterns After Major Changes

```bash
# Switched from React to Vue
slm remember "Migrated from React to Vue" --tags migration
slm remember "Now using Vue for all frontend" --tags preference

# Force pattern update
python3 ~/.claude-memory/pattern_learner.py update
```

### 4. Use Profiles for Different Contexts

```bash
# Work profile learns work patterns
slm switch-profile work

# Personal profile learns personal patterns
slm switch-profile personal
```

---

## Performance

### Learning Time

| Memories | Update Time |
|----------|-------------|
| 100 | ~0.5s |
| 1,000 | ~2s |
| 5,000 | ~10s |
| 10,000 | ~20s |

### Memory Overhead

**Pattern storage:**
- ~100 bytes per pattern
- Typical: 50-200 patterns
- Total: 5-20 KB (negligible)

---

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [Knowledge Graph Guide](Knowledge-Graph-Guide) - Graph features
- [Multi-Profile Workflows](Multi-Profile-Workflows) - Profile management
- [Why Local Matters](Why-Local-Matters) - Privacy benefits
- [CLI Cheatsheet](CLI-Cheatsheet) - Command reference

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
