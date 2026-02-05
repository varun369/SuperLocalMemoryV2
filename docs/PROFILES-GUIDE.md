# SuperLocalMemory V2 - Profile Management Guide

## Overview

**Profiles** let you maintain completely separate memory systems for different contexts or personalities.

**Use cases:**
- **Work vs Personal**: Keep professional and personal memories separate
- **Client-specific**: Isolated memories for each client project
- **Experimentation**: Test profile for trying new features
- **Personality switching**: Different "AI Master" personas with unique learned patterns

---

## Quick Start

### List Profiles
```bash
python ~/.claude-memory/memory-profiles.py list
```

### Show Current Profile
```bash
python ~/.claude-memory/memory-profiles.py current
```

### Create New Profile
```bash
# Empty profile
python ~/.claude-memory/memory-profiles.py create work \
  --description "Work projects"

# Copy current memories to new profile
python ~/.claude-memory/memory-profiles.py create personal \
  --from-current
```

### Switch Profile
```bash
python ~/.claude-memory/memory-profiles.py switch work

# ⚠️ IMPORTANT: Restart Claude CLI after switching!
```

### Delete Profile
```bash
python ~/.claude-memory/memory-profiles.py delete old-profile
```

---

## Profile Isolation

Each profile has its own:
- ✅ **Database** (memory.db) - Completely separate memories
- ✅ **Graph data** - Independent knowledge graph
- ✅ **Learned patterns** - Different identity profiles
- ✅ **Compressed archives** - Separate storage
- ✅ **Configuration** - Profile-specific settings

**Profiles DO NOT share:**
- Memories
- Graphs
- Patterns
- Any data

---

## Use Cases

### 1. Work vs Personal

```bash
# Create work profile
python ~/.claude-memory/memory-profiles.py create work \
  --description "Professional coding projects"

# Create personal profile from current
python ~/.claude-memory/memory-profiles.py create personal \
  --from-current --description "Personal learning and experiments"

# Switch based on context
python ~/.claude-memory/memory-profiles.py switch work   # During work hours
python ~/.claude-memory/memory-profiles.py switch personal  # Personal time
```

**Result:**
- Work profile learns: Enterprise patterns, client tech stacks, professional terminology
- Personal profile learns: Hobby projects, experimental tech, casual coding style

---

### 2. Client-Specific Profiles

```bash
# Create profile per client
python ~/.claude-memory/memory-profiles.py create client-acme \
  --description "Acme Corp project"

python ~/.claude-memory/memory-profiles.py create client-contoso \
  --description "Contoso Inc project"

# Switch when working on different clients
python ~/.claude-memory/memory-profiles.py switch client-acme
```

**Benefits:**
- Client data never mixes
- Each client gets learned patterns specific to their codebase
- Easy to archive completed projects

---

### 3. Learning & Experimentation

```bash
# Create test profile
python ~/.claude-memory/memory-profiles.py create experimental \
  --description "Testing new features"

# Switch to test profile
python ~/.claude-memory/memory-profiles.py switch experimental

# Try new things without polluting main profile
# ...test features...

# Switch back when done
python ~/.claude-memory/memory-profiles.py switch default
```

---

### 4. Different AI Personalities

```bash
# Strict architect profile
python ~/.claude-memory/memory-profiles.py create architect \
  --description "Rigorous architecture-first approach"

# Rapid prototyper profile
python ~/.claude-memory/memory-profiles.py create prototyper \
  --description "Fast iteration, MVP-first approach"

# Use based on project phase
python ~/.claude-memory/memory-profiles.py switch architect  # Planning
python ~/.claude-memory/memory-profiles.py switch prototyper  # MVP development
```

**Result:** Each profile learns different patterns:
- Architect: Detailed docs, extensive planning, clean architecture
- Prototyper: Quick iterations, pragmatic choices, speed over perfection

---

## Profile Operations

### Create Empty Profile

Creates fresh V2 database with no memories:

```bash
python ~/.claude-memory/memory-profiles.py create new-profile
```

**When to use:**
- Starting completely fresh context
- Client work (no prior context)
- Experimentation (clean slate)

---

### Create from Current

Copies current memory system to new profile:

```bash
python ~/.claude-memory/memory-profiles.py create backup --from-current
```

**When to use:**
- Branching current memories
- Creating backup before major changes
- Testing with real data

---

### Switch Profile

Changes active profile (requires Claude CLI restart):

```bash
python ~/.claude-memory/memory-profiles.py switch work

# Output:
# Switching from 'default' to 'work'...
#   Saving current state to profile 'default'...
#     ✓ Saved to ~/.claude-memory/profiles/default
#   Loading profile 'work'...
#     ✓ Loaded from ~/.claude-memory/profiles/work
# ✅ Switched to profile: work
#
# ⚠️  IMPORTANT: Restart Claude CLI to use new profile!
```

**⚠️ Must restart Claude CLI after switching!**

---

### Delete Profile

Permanently removes a profile:

```bash
python ~/.claude-memory/memory-profiles.py delete old-profile

# Prompts: Type profile name 'old-profile' to confirm:
```

**Safety:**
- Cannot delete 'default' profile
- Cannot delete active profile
- Requires confirmation (type profile name)
- Use `--force` to skip confirmation

---

### Rename Profile

```bash
python ~/.claude-memory/memory-profiles.py rename old-name new-name
```

**Cannot rename:**
- 'default' profile
- Active profile (switch first)

---

## Profile Storage

Profiles stored in:
```
~/.claude-memory/profiles/
├── work/
│   ├── memory.db
│   ├── config.json
│   └── vectors/
├── personal/
│   ├── memory.db
│   ├── config.json
│   └── vectors/
└── client-acme/
    ├── memory.db
    ├── config.json
    └── vectors/
```

**Active profile** stored in main location:
```
~/.claude-memory/
├── memory.db          ← Currently active profile
├── config.json
└── vectors/
```

---

## Profile Configuration

Stored in `~/.claude-memory/profiles.json`:

```json
{
  "profiles": {
    "default": {
      "name": "default",
      "description": "Default memory profile",
      "created_at": "2026-02-05T10:00:00",
      "last_used": "2026-02-05T14:00:00",
      "created_from": "empty"
    },
    "work": {
      "name": "work",
      "description": "Work projects",
      "created_at": "2026-02-05T11:00:00",
      "last_used": "2026-02-05T13:00:00",
      "created_from": "empty"
    }
  },
  "active_profile": "work"
}
```

---

## Best Practices

### 1. Use Descriptive Names
```bash
# Good
python ~/.claude-memory/memory-profiles.py create client-acme-api
python ~/.claude-memory/memory-profiles.py create personal-learning

# Avoid
python ~/.claude-memory/memory-profiles.py create profile1
python ~/.claude-memory/memory-profiles.py create temp
```

### 2. Document Profile Purpose
```bash
python ~/.claude-memory/memory-profiles.py create project-x \
  --description "Confidential client X - Next.js + PostgreSQL"
```

### 3. Switch Profiles at Context Boundaries
```bash
# Start of work day
python ~/.claude-memory/memory-profiles.py switch work

# End of work day
python ~/.claude-memory/memory-profiles.py switch personal
```

### 4. Backup Before Major Changes
```bash
# Create backup profile
python ~/.claude-memory/memory-profiles.py create backup-$(date +%Y%m%d) \
  --from-current

# Make changes in main profile
# ...

# If needed, switch to backup
python ~/.claude-memory/memory-profiles.py switch backup-20260205
```

### 5. Archive Completed Projects
```bash
# Rename completed project
python ~/.claude-memory/memory-profiles.py rename client-acme \
  archived-client-acme-202602

# Create fresh profile for new project
python ~/.claude-memory/memory-profiles.py create client-newco
```

---

## Integration with Reset Commands

**Profiles + Reset = Powerful Combination**

### Reset Current Profile Only
```bash
# Soft reset active profile
python ~/.claude-memory/memory-reset.py soft

# Active profile cleared, others untouched
```

### Reset Specific Profile
```bash
# Switch to profile
python ~/.claude-memory/memory-profiles.py switch old-project

# Reset it
python ~/.claude-memory/memory-reset.py soft

# Switch back
python ~/.claude-memory/memory-profiles.py switch default
```

### Create Clean Profile
```bash
# Create empty profile
python ~/.claude-memory/memory-profiles.py create clean-slate

# Switch to it
python ~/.claude-memory/memory-profiles.py switch clean-slate

# Now work in completely clean environment
```

---

## Troubleshooting

### "Profile not found"
Check available profiles:
```bash
python ~/.claude-memory/memory-profiles.py list
```

### "Changes not reflecting"
Restart Claude CLI after switching profiles:
```bash
# Exit Claude CLI
# Restart Claude CLI
```

### "Cannot delete active profile"
Switch to different profile first:
```bash
python ~/.claude-memory/memory-profiles.py switch default
python ~/.claude-memory/memory-profiles.py delete unwanted
```

### "Profile directory not found"
Profile will be created on first switch:
```bash
python ~/.claude-memory/memory-profiles.py switch new-profile
# Creates directory automatically
```

---

## FAQ

**Q: Do profiles share learned patterns?**
A: No. Each profile learns independently.

**Q: Can I merge profiles?**
A: Not directly. You can manually copy memories between profiles.

**Q: What happens to cron jobs with multiple profiles?**
A: Cron jobs run on currently active profile. Switch profile to run jobs on it.

**Q: Can I have different compression settings per profile?**
A: Yes. Each profile has its own `config.json`.

**Q: How much space do profiles use?**
A: ~5MB per profile with 100 memories (before compression).

**Q: Can I backup all profiles at once?**
A: Yes, backup `~/.claude-memory/profiles/` directory.

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `list` | Show all profiles |
| `current` | Show active profile |
| `create <name>` | Create empty profile |
| `create <name> --from-current` | Copy current to new profile |
| `switch <name>` | Change active profile (requires restart) |
| `delete <name>` | Remove profile (requires confirmation) |
| `rename <old> <new>` | Rename profile |

---

**Remember:** Always restart Claude CLI after switching profiles!
