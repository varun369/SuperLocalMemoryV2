---
name: superlocalmemoryv2:profile
description: Manage multiple memory profiles for different contexts
arguments: command (list/current/create/switch/delete), name, options
---

# SuperLocalMemory V2: Profile

Manage multiple isolated memory profiles for different projects, contexts, or use cases.

## Usage

```bash
/superlocalmemoryv2:profile list
/superlocalmemoryv2:profile current
/superlocalmemoryv2:profile create work
/superlocalmemoryv2:profile switch work
/superlocalmemoryv2:profile delete old-project
```

## Commands

### `list`
Shows all available profiles with statistics.

**Usage:**
```bash
/superlocalmemoryv2:profile list
```

**Output:**
```
Available Profiles:

* default (active)
  Memories: 247 | Size: 45.2 MB | Created: 2026-01-15

  work
  Memories: 89 | Size: 12.3 MB | Created: 2026-01-20

  research
  Memories: 156 | Size: 28.7 MB | Created: 2026-01-25

Total: 3 profiles
```

---

### `current`
Shows currently active profile details.

**Usage:**
```bash
/superlocalmemoryv2:profile current
```

**Output:**
```
Active Profile: work
Location: ~/.claude-memory/profiles/work/
Memories: 89
Database Size: 12.3 MB
Created: 2026-01-20
Last Access: 2026-02-05 15:30:22
```

---

### `create <name>`
Creates new isolated memory profile.

**Usage:**
```bash
/superlocalmemoryv2:profile create ml-research
```

**Actions:**
- Creates new profile directory
- Initializes empty database with schema
- Sets up knowledge graph structure
- Creates pattern learning models
- Does NOT switch to new profile automatically

**Naming rules:**
- Alphanumeric, hyphens, underscores only
- No spaces or special characters
- Max 50 characters

---

### `switch <name>`
Switches to different profile (requires CLI restart).

**Usage:**
```bash
/superlocalmemoryv2:profile switch work
```

**⚠️ Important:**
After switching, you must restart Claude CLI for changes to take effect:
```bash
exit
claude
```

**What happens:**
- Updates active profile pointer
- Next Claude CLI session uses new profile
- All remember/recall operations use new profile's database

---

### `delete <name>`
Deletes profile after confirmation (destructive).

**Usage:**
```bash
/superlocalmemoryv2:profile delete old-project
```

**Safety features:**
- Cannot delete active profile (switch first)
- Requires interactive confirmation
- Creates automatic backup before deletion
- Backup retained for 30 days

**Confirmation prompt:**
```
Delete profile "old-project"?
Memories: 45 | Size: 8.2 MB
This action cannot be undone (backup will be created).
Type 'DELETE old-project' to confirm:
```

## Implementation

This skill executes: `~/.claude-memory/bin/superlocalmemoryv2:profile`

The command:
1. Parses profile command and arguments
2. Validates profile names and permissions
3. Executes requested profile operation
4. Updates profile configuration
5. Reports status and next steps

## Use Cases

**Separate work contexts:**
```bash
/superlocalmemoryv2:profile create work
/superlocalmemoryv2:profile create personal
```

**Project-specific memories:**
```bash
/superlocalmemoryv2:profile create ecommerce-app
/superlocalmemoryv2:profile switch ecommerce-app
/superlocalmemoryv2:remember "Stripe API key rotation: monthly"
```

**Research vs production:**
```bash
/superlocalmemoryv2:profile create ml-experiments
/superlocalmemoryv2:profile create production-code
```

**Client isolation:**
```bash
/superlocalmemoryv2:profile create client-acme
/superlocalmemoryv2:profile create client-globex
```

## Examples

**List all profiles:**
```bash
/superlocalmemoryv2:profile list
```

**Create new profile:**
```bash
/superlocalmemoryv2:profile create ai-research
```

**Switch to profile:**
```bash
/superlocalmemoryv2:profile switch ai-research
# Then restart CLI
exit
claude
```

**Check current profile:**
```bash
/superlocalmemoryv2:profile current
```

**Delete old profile:**
```bash
/superlocalmemoryv2:profile switch default
/superlocalmemoryv2:profile delete old-project
```

## Notes

- Profile isolation is complete (separate databases)
- Default profile created automatically on first use
- Profile data location: `~/.claude-memory/profiles/<name>/`
- Switch requires CLI restart to take effect
- Cannot delete active profile (safety measure)
- Deleted profiles backed up for 30 days
- Profile name shown in status command output
