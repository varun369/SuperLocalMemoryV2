# Multi-Profile Workflows

**What are profiles, use cases, and best practices** - Separate work/personal contexts, multi-client management, and experimentation with complete isolation guarantees.

---

## What Are Profiles?

**Profiles** are isolated memory contexts in SuperLocalMemory V2. Each profile has its own:
- SQLite database
- Knowledge graph
- Learned patterns
- Configuration settings

**Think of profiles as completely separate workspaces.** Memories in one profile never affect another profile.

**Example:**
```
Profile: work
  - 500 memories about work projects
  - Graph: FastAPI, PostgreSQL, microservices
  - Patterns: Python backend, REST APIs

Profile: personal
  - 200 memories about personal projects
  - Graph: React, Firebase, Next.js
  - Patterns: TypeScript frontend, serverless

No context bleeding between them!
```

---

## Why Use Profiles?

### 1. Work/Personal Separation

**Problem:**
```
Without profiles:
- Work memories mixed with personal projects
- AI gets confused about which project you mean
- Privacy concerns (work info in personal context)
```

**Solution:**
```bash
# Work context
slm switch-profile work
slm remember "Company API uses OAuth2" --tags work,security

# Personal context
slm switch-profile personal
slm remember "My side project uses simple JWT" --tags personal
```

### 2. Multi-Client Management

**Scenario:** Freelancer working with 5 clients

```bash
# Client A
slm switch-profile client-acme
slm remember "Acme uses AWS, PostgreSQL, React"

# Client B
slm switch-profile client-techcorp
slm remember "TechCorp uses GCP, MySQL, Vue"

# Each client's context completely isolated
```

**Benefits:**
- No accidental data leaks between clients
- Clear context switching
- Easy to archive old clients

### 3. Experimentation

**Scenario:** Testing new patterns without polluting main database

```bash
# Create experiment profile
slm switch-profile experiment

# Try new patterns
slm remember "Testing new architecture pattern"
slm build-graph --clustering

# If experiment fails, delete profile
slm switch-profile delete experiment --confirm
```

### 4. Team Collaboration

**Scenario:** Team sharing common knowledge base

```bash
# Team profile (shared via git)
slm switch-profile team
slm remember "Team standard: Use TypeScript" --tags team
slm remember "Team uses Jest for testing" --tags team

# Each member switches to team profile for shared context
```

---

## Profile Operations

### List Profiles

```bash
slm switch-profile list
```

**Output:**
```
Available Profiles:

* default (active)
  Location: ~/.claude-memory/profiles/default/
  Memories: 247
  Last used: 2026-02-07 14:23

  work
  Location: ~/.claude-memory/profiles/work/
  Memories: 538
  Last used: 2026-02-06 09:15

  personal
  Location: ~/.claude-memory/profiles/personal/
  Memories: 123
  Last used: 2026-02-05 18:42

  client-acme
  Location: ~/.claude-memory/profiles/client-acme/
  Memories: 89
  Last used: 2026-01-28 11:30
```

### Create Profile

```bash
# Basic creation
slm switch-profile create work

# With description
slm switch-profile create work --description "Work projects and decisions"

# With custom location (advanced)
slm switch-profile create work --path /custom/path/work
```

**What happens:**
1. Creates new directory: `~/.claude-memory/profiles/work/`
2. Initializes fresh SQLite database
3. Creates empty graph and pattern tables
4. Sets up profile metadata

### Switch Profile

```bash
# Switch to profile
slm switch-profile work

# Verify switch
slm status
```

**Output:**
```
✓ Switched to profile: work

Current Profile: work
Total memories: 538
Knowledge graph: 342 nodes, 789 edges
```

**What changes:**
- All subsequent commands use work profile
- Database path: `~/.claude-memory/profiles/work/memory.db`
- Graph and patterns specific to work

### Delete Profile

```bash
# Delete profile (requires confirmation)
slm switch-profile delete experiment

# Force delete without confirmation
slm switch-profile delete experiment --confirm
```

**Warning:** This permanently deletes all memories in that profile!

**Backup first:**
```bash
# Backup before deletion
cp -r ~/.claude-memory/profiles/experiment/ ~/backups/experiment-$(date +%Y%m%d)/
slm switch-profile delete experiment --confirm
```

---

## Profile Isolation Guarantees

### Complete Data Isolation

**Each profile has:**
```
~/.claude-memory/profiles/work/
├── memory.db          # Separate SQLite database
├── graph_data.db      # Separate graph storage
├── patterns.db        # Separate learned patterns
└── config.json        # Profile-specific config
```

**Guarantee:** Memories in one profile NEVER appear in another profile.

### Independent Graphs

```bash
# Build graph in work profile
slm switch-profile work
slm build-graph
# Creates work-specific graph

# Build graph in personal profile
slm switch-profile personal
slm build-graph
# Creates completely separate graph
```

**No shared nodes or edges between profiles.**

### Separate Pattern Learning

```bash
# Work profile learns work patterns
slm switch-profile work
# Learns: Python, FastAPI, microservices

# Personal profile learns different patterns
slm switch-profile personal
# Learns: JavaScript, Next.js, serverless

# No pattern leakage
```

---

## Use Cases

### Use Case 1: Consultant with Multiple Clients

**Setup:**
```bash
# Client profiles
slm switch-profile create client-acme --description "Acme Corp (2026)"
slm switch-profile create client-techcorp --description "TechCorp (2026)"
slm switch-profile create client-startup --description "Startup Inc (2026)"

# Personal profile
slm switch-profile create personal --description "Personal projects"
```

**Daily workflow:**
```bash
# Morning: Client Acme
slm switch-profile client-acme
slm recall "last meeting notes"
# Work on Acme project

# Afternoon: Client TechCorp
slm switch-profile client-techcorp
slm recall "API architecture"
# Work on TechCorp project

# Evening: Personal
slm switch-profile personal
slm remember "New blog post idea"
```

**Benefits:**
- Clear context separation
- No accidental leaks
- Easy billing (track per client)
- Archive old clients easily

### Use Case 2: Work/Personal Split

**Setup:**
```bash
# Work profile
slm switch-profile create work --description "Day job"

# Personal profile
slm switch-profile create personal --description "Side projects"
```

**Work hours:**
```bash
slm switch-profile work
slm remember "Sprint planning: Implement OAuth2" --tags sprint
slm remember "Code review feedback: Add error handling" --tags review
```

**After hours:**
```bash
slm switch-profile personal
slm remember "Side project: Build portfolio site with Next.js" --tags project
slm remember "Learn Rust for fun" --tags learning
```

**Benefits:**
- Mental separation
- Privacy (work info not in personal)
- Different pattern learning

### Use Case 3: Project-Based Organization

**Setup:**
```bash
# One profile per major project
slm switch-profile create project-api --description "REST API rewrite"
slm switch-profile create project-frontend --description "React dashboard"
slm switch-profile create project-mobile --description "React Native app"
```

**Benefits:**
- Clear project boundaries
- Easy to archive finished projects
- Project-specific knowledge graphs
- No cross-project confusion

### Use Case 4: Experimentation

**Setup:**
```bash
# Experiment profile
slm switch-profile create experiment --description "Testing new patterns"

# Try new approaches
slm remember "Experimenting with GraphQL"
slm remember "Testing microservices with gRPC"
slm build-graph --clustering
```

**Cleanup:**
```bash
# Experiment failed, delete profile
slm switch-profile default
slm switch-profile delete experiment --confirm
```

**Benefits:**
- Safe to try new patterns
- No pollution of main database
- Easy to discard failed experiments

### Use Case 5: Team Shared Knowledge

**Setup:**
```bash
# Create team profile
slm switch-profile create team --description "Team shared knowledge"

# Save team decisions
slm remember "Team standard: TypeScript for all new code" --tags standard
slm remember "Team uses Jest for testing" --tags standard
slm remember "Code review checklist: Security, tests, docs" --tags checklist
```

**Sharing (via git):**
```bash
# Export team profile
cd ~/.claude-memory/profiles/
tar czf team-profile.tar.gz team/

# Team members import
cd ~/.claude-memory/profiles/
tar xzf team-profile.tar.gz
slm switch-profile team
```

**Benefits:**
- Shared context across team
- Consistent recommendations
- Onboarding new members

---

## Best Practices

### 1. Name Profiles Clearly

**Good:**
```bash
slm switch-profile create work-project-api
slm switch-profile create personal-blog
slm switch-profile create client-acme-2026
```

**Poor:**
```bash
slm switch-profile create p1
slm switch-profile create test
slm switch-profile create stuff
```

### 2. Add Descriptions

```bash
slm switch-profile create work \
  --description "Day job at TechCorp - API team (2026)"
```

**Benefits:**
- Easy to remember what profile is for
- Shows in `list` output
- Helps team members understand context

### 3. Use Default Profile for General Knowledge

```bash
# General programming knowledge
slm switch-profile default
slm remember "Python best practices" --tags reference
slm remember "Git cheatsheet" --tags reference

# Switch to project-specific for work
slm switch-profile work
```

### 4. Archive Old Profiles

```bash
# Archive completed project
tar czf ~/archives/client-acme-$(date +%Y%m%d).tar.gz \
  ~/.claude-memory/profiles/client-acme/

# Delete profile
slm switch-profile delete client-acme --confirm
```

### 5. Regular Backups

```bash
# Backup all profiles (cron)
#!/bin/bash
backup_dir=~/backups/slm-$(date +%Y%m%d)
mkdir -p "$backup_dir"
cp -r ~/.claude-memory/profiles/ "$backup_dir/"
```

### 6. Switch Profile at Start of Day

```bash
# Add to .bashrc or .zshrc
# Auto-prompt for profile on terminal start

if command -v slm &> /dev/null; then
  echo "Current profile: $(slm status | grep 'Current Profile' | cut -d: -f2)"
  echo "Switch profile? (work/personal/default): "
fi
```

---

## Profile Configuration

### Per-Profile Settings

Each profile can have different settings:

**Example: `~/.claude-memory/profiles/work/config.json`**
```json
{
  "profile_name": "work",
  "description": "Work projects",
  "created_at": "2026-02-07T14:23:00",
  "settings": {
    "default_importance": 5,
    "auto_build_graph": true,
    "pattern_learning_threshold": 0.5
  }
}
```

### Shared Global Settings

**Global config:** `~/.claude-memory/config.json`
```json
{
  "default_profile": "work",
  "mcp_server_enabled": true,
  "shell_integration": true
}
```

---

## Advanced Features

### Switch with Environment Variable

```bash
# Set profile via env var
export SLM_PROFILE=work
slm status  # Uses work profile

# Temporary switch
SLM_PROFILE=personal slm recall "blog ideas"
```

### Profile Auto-Switch by Directory

**Setup (zsh/bash):**
```bash
# Add to .bashrc or .zshrc
cd() {
  builtin cd "$@"

  # Auto-switch profile based on directory
  if [[ $PWD == ~/work/* ]]; then
    export SLM_PROFILE=work
  elif [[ $PWD == ~/personal/* ]]; then
    export SLM_PROFILE=personal
  else
    export SLM_PROFILE=default
  fi
}
```

### Profile-Specific Aliases

```bash
# Add to .bashrc or .zshrc

# Work aliases
alias work-slm='SLM_PROFILE=work slm'
alias work-recall='SLM_PROFILE=work slm recall'

# Personal aliases
alias personal-slm='SLM_PROFILE=personal slm'
alias personal-recall='SLM_PROFILE=personal slm recall'

# Usage
work-recall "API architecture"
personal-remember "Blog post idea"
```

---

## Troubleshooting

### "Profile not found"

**Cause:** Profile doesn't exist

**Solution:**
```bash
# List available profiles
slm switch-profile list

# Create if needed
slm switch-profile create missing-profile
```

### "Cannot switch to active profile"

**Cause:** Already using that profile

**Solution:**
```bash
# Check current profile
slm status | grep "Current Profile"

# Switch to different profile
slm switch-profile default
```

### "Profile database corrupted"

**Cause:** Database file damaged

**Solution:**
```bash
# Restore from backup
cp ~/backups/slm-20260207/profiles/work/memory.db \
   ~/.claude-memory/profiles/work/memory.db

# Or rebuild from scratch
slm switch-profile delete work --confirm
slm switch-profile create work
```

### "Memories not showing after switch"

**Cause:** Switched to wrong profile or profile empty

**Solution:**
```bash
# Verify current profile
slm status

# List all profiles and memory counts
slm switch-profile list

# Switch to correct profile
slm switch-profile work

# Verify memories exist
slm list
```

---

## Performance

### Profile Overhead

**Disk space per profile:**
- Empty: ~100 KB
- 1,000 memories: ~5 MB
- 10,000 memories: ~50 MB

**Switch time:**
- ~10ms (instant)

**No performance degradation with multiple profiles.**

---

## Migration Between Profiles

### Export from One Profile

```bash
# Switch to source profile
slm switch-profile work

# Export memories
sqlite3 ~/.claude-memory/profiles/work/memory.db \
  "SELECT json_group_array(json_object(
    'content', content,
    'tags', tags,
    'project_name', project_name,
    'importance', importance
  )) FROM memories;" > work_export.json
```

### Import to Another Profile

```bash
# Switch to destination profile
slm switch-profile personal

# Import memories (Python script)
python3 << 'EOF'
import json, sqlite3
conn = sqlite3.connect("/Users/$(whoami)/.claude-memory/profiles/personal/memory.db")
with open('work_export.json') as f:
    data = json.load(f)
    for mem in data:
        conn.execute(
            "INSERT INTO memories (content, tags, project_name, importance) VALUES (?, ?, ?, ?)",
            (mem['content'], mem['tags'], mem['project_name'], mem['importance'])
        )
conn.commit()
EOF

# Rebuild graph in destination
slm build-graph
```

---

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [CLI Cheatsheet](CLI-Cheatsheet) - Command reference
- [Configuration](Configuration) - Advanced settings
- [Why Local Matters](Why-Local-Matters) - Privacy benefits
- [Pattern Learning](Pattern-Learning-Explained) - How patterns work

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
