# Pattern Learning Explained

**How pattern learning works in SuperLocalMemory V2** - Automatic detection of your coding preferences and style, all processed locally for privacy.

---

## What is Pattern Learning?

Pattern learning is SuperLocalMemory's ability to **automatically detect your coding preferences and style** by analyzing the memories you save. It learns what frameworks you prefer, how you write code, what testing approaches you use, and more — without any manual configuration.

**Example:**
```
After saving memories, SuperLocalMemory learns:

Your Coding Identity:
- Framework preference: React (high confidence)
- Style: Performance over readability
- Testing: Jest + React Testing Library
- API style: REST over GraphQL
- Language: Python for backends
```

**Why this matters:** Your AI assistant can automatically match your preferences without you re-explaining them every session.

> For technical details on the learning algorithms, see our published research: https://zenodo.org/records/18709670

---

## How It Works

Pattern learning analyzes your saved memories across multiple dimensions:

- **Technology preferences** — What frameworks, languages, and tools you use most
- **Architecture choices** — Your preferred patterns (e.g., REST vs GraphQL, microservices vs monolith)
- **Security approaches** — Your go-to authentication and authorization patterns
- **Coding style** — Performance vs readability, testing depth, code organization
- **Domain terminology** — Project-specific terms and industry vocabulary

Each detected preference gets a confidence score based on the evidence in your memories. Low confidence with small datasets is correct behavior — the system is conservative by design.

---

## Learning Process

### Automatic Learning

**Triggered on every `remember` operation:**
```bash
slm remember "We use FastAPI for REST APIs" --tags python,backend
```

No manual action required. Patterns update as you add memories.

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
# Get identity context
python3 ~/.claude-memory/pattern_learner.py context 0.5
```

**Output:**
```
Your Coding Identity:

Framework Preferences:
- React (strong confidence)
- FastAPI (strong confidence)

Language Preferences:
- Python for backends
- TypeScript for frontend

Architecture Patterns:
- REST over GraphQL

Security Approaches:
- JWT tokens

Coding Style:
- Performance over readability
```

---

## Identity Context Generation

**Identity context** is a formatted text summary of your learned patterns that gets injected into AI assistant prompts automatically.

### Using with AI Assistants

**Automatic injection (Cursor/Claude Desktop):**
- MCP server automatically includes identity context
- No manual action needed

**Manual injection:**
```bash
# Get context
context=$(python3 ~/.claude-memory/pattern_learner.py context 0.5)

# Use with any AI assistant
echo "$context\n\nNow help me build a new API endpoint."
```

---

## Adaptive Learning

### Patterns Evolve Over Time

**Scenario 1: New preference emerges**
```
Month 1: React (dominant)
Month 3: React and Vue emerging equally
Month 4: Pattern learning adapts: "Shifting from React to Vue"
```

**Scenario 2: Temporary spike**
```
Week 1-4: Python dominant
Week 5: JavaScript spike (project context)
Week 6: Python resumes dominance — recognized as temporary
```

### Recency and Decay

Recent patterns are weighted more heavily. Old patterns gradually fade when not reinforced. This ensures your current preferences dominate, not stale ones from months ago.

---

## Privacy & Security

### 100% Local Processing

**No data leaves your machine:**
- All pattern learning happens locally
- No external API calls
- No telemetry
- No cloud sync

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

### 2. Project-Specific Patterns

**Use profiles for different projects:**
```bash
# Work project
slm switch-profile work
slm remember "Work project uses React + FastAPI"

# Personal project
slm switch-profile personal
slm remember "Personal project uses Vue + Flask"

# Each profile learns separate patterns
```

### 3. Debugging Assistance

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

# More patterns included (30%+)
python3 ~/.claude-memory/pattern_learner.py context 0.3
```

### List All Patterns

```bash
# View all learned patterns
python3 ~/.claude-memory/pattern_learner.py list
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

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [Multi-Profile Workflows](Multi-Profile-Workflows) - Profile management
- [Why Local Matters](Why-Local-Matters) - Privacy benefits
- [CLI Cheatsheet](CLI-Cheatsheet) - Command reference

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
