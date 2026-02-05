# SuperLocalMemory V2 - Claude CLI Skills Installation Guide

Quick installation guide for SuperLocalMemory V2 Claude CLI skills.

## Prerequisites

Before installing skills, ensure you have:

1. **SuperLocalMemory V2 installed**
   ```bash
   ls -la ~/.claude-memory/bin/superlocalmemoryv2:*
   # Should show 6+ executable commands
   ```

2. **Claude CLI installed and running**
   ```bash
   claude --version
   # Requires version >= 0.8.0 for skill support
   ```

3. **Python 3.8+ available**
   ```bash
   python3 --version
   ```

## Installation Methods

### Method 1: Quick Copy (Recommended for Users)

```bash
# Create skills directory
mkdir -p ~/.claude/skills/

# Copy the 6 core skills
cp ~/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/claude-skills/superlocalmemoryv2-*-skill.md ~/.claude/skills/

# Verify
ls -1 ~/.claude/skills/superlocalmemoryv2-*-skill.md | wc -l
# Should output: 6
```

### Method 2: Symlink (Recommended for Developers)

Use this if you're developing and want changes to reflect immediately:

```bash
# Create skills directory
mkdir -p ~/.claude/skills/

# Create symlinks
cd ~/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/claude-skills/
for skill in superlocalmemoryv2-*-skill.md; do
  ln -sf "$(pwd)/$skill" ~/.claude/skills/
done

# Verify
ls -l ~/.claude/skills/superlocalmemoryv2-*-skill.md
# Should show symlinks pointing to repo
```

### Method 3: Clone from GitHub (For New Users)

```bash
# Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git ~/Documents/SuperLocalMemoryV2

# Copy skills
mkdir -p ~/.claude/skills/
cp ~/Documents/SuperLocalMemoryV2/claude-skills/superlocalmemoryv2-*-skill.md ~/.claude/skills/

# Install SuperLocalMemory V2 system
cd ~/Documents/SuperLocalMemoryV2
./install.sh
```

## Verification

### Step 1: Check Files Installed

```bash
ls -1 ~/.claude/skills/superlocalmemoryv2-*-skill.md
```

Expected output:
```
/Users/yourname/.claude/skills/superlocalmemoryv2-list-skill.md
/Users/yourname/.claude/skills/superlocalmemoryv2-profile-skill.md
/Users/yourname/.claude/skills/superlocalmemoryv2-recall-skill.md
/Users/yourname/.claude/skills/superlocalmemoryv2-remember-skill.md
/Users/yourname/.claude/skills/superlocalmemoryv2-reset-skill.md
/Users/yourname/.claude/skills/superlocalmemoryv2-status-skill.md
```

### Step 2: Restart Claude CLI

Skills are loaded at startup. Restart your session:

```bash
# Exit current session
exit

# Start new session
claude
```

### Step 3: Test Autocomplete

In Claude CLI, type:

```
/super
```

Then press TAB. You should see autocomplete options:

```
/superlocalmemoryv2:remember
/superlocalmemoryv2:recall
/superlocalmemoryv2:list
/superlocalmemoryv2:status
/superlocalmemoryv2:reset
/superlocalmemoryv2:profile
```

### Step 4: Test Execution

Try a simple command:

```
/superlocalmemoryv2:status
```

Expected output: System status with memory count, database size, and profile info.

## Testing Individual Skills

### Test Remember
```
/superlocalmemoryv2:remember "Test memory for verification" --tags test
```

### Test Recall
```
/superlocalmemoryv2:recall "test"
```

### Test List
```
/superlocalmemoryv2:list --limit 5
```

### Test Status
```
/superlocalmemoryv2:status
```

### Test Profile
```
/superlocalmemoryv2:profile list
```

### Test Reset (Safe Command)
```
/superlocalmemoryv2:reset status
```

## Troubleshooting

### Issue: Skills Not Appearing in Autocomplete

**Solution 1: Verify file location**
```bash
ls -la ~/.claude/skills/superlocalmemoryv2-*-skill.md
```

**Solution 2: Check file format**
```bash
head -5 ~/.claude/skills/superlocalmemoryv2-remember-skill.md
```

Should start with:
```yaml
---
name: superlocalmemoryv2:remember
description: Save a memory to SuperLocalMemory V2...
---
```

**Solution 3: Restart Claude CLI**
```bash
exit
claude
```

**Solution 4: Check Claude CLI version**
```bash
claude --version
# Must be >= 0.8.0
```

---

### Issue: "Command Not Found" When Executing Skills

**Solution 1: Verify SuperLocalMemory V2 installation**
```bash
ls -la ~/.claude-memory/bin/superlocalmemoryv2:*
chmod +x ~/.claude-memory/bin/superlocalmemoryv2:*
```

**Solution 2: Test command directly**
```bash
~/.claude-memory/bin/superlocalmemoryv2:status
```

**Solution 3: Check PATH**
```bash
echo $PATH | grep -o "\.claude-memory/bin"
```

If empty, add to PATH:
```bash
echo 'export PATH="$HOME/.claude-memory/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

### Issue: Permission Denied

**Solution: Fix file permissions**
```bash
# Make skills readable
chmod 644 ~/.claude/skills/superlocalmemoryv2-*-skill.md

# Make commands executable
chmod +x ~/.claude-memory/bin/superlocalmemoryv2:*
```

---

### Issue: Skills Execute But Show Errors

**Solution: Check Python environment**
```bash
# Verify Python version
python3 --version  # Must be 3.8+

# Test SuperLocalMemory V2 directly
cd ~/.claude-memory
python3 -c "import memory_store_v2; print('OK')"
```

---

### Issue: Profile Switch Not Taking Effect

**Solution: Restart Claude CLI after switching**
```bash
/superlocalmemoryv2:profile switch work
exit
claude
/superlocalmemoryv2:status  # Should show "Profile: work"
```

## Updating Skills

### Update from Repository

If using **symlinks** (Method 2), changes reflect automatically.

If using **copy** (Method 1):

```bash
# Pull latest from git
cd ~/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo
git pull

# Copy updated skills
cp claude-skills/superlocalmemoryv2-*-skill.md ~/.claude/skills/

# Restart Claude CLI
exit
claude
```

### Manual Updates

Edit skills directly:

```bash
# Edit skill file
vim ~/.claude/skills/superlocalmemoryv2-remember-skill.md

# Restart Claude CLI to reload
exit
claude
```

## Uninstallation

### Remove Skills Only

```bash
# Remove skill files
rm ~/.claude/skills/superlocalmemoryv2-*-skill.md

# Restart Claude CLI
exit
claude
```

This removes CLI integration but keeps SuperLocalMemory V2 system intact.

### Remove Everything

```bash
# Remove skills
rm ~/.claude/skills/superlocalmemoryv2-*-skill.md

# Remove SuperLocalMemory V2
rm -rf ~/.claude-memory

# Remove from PATH (edit ~/.zshrc or ~/.bashrc)
# Remove the line: export PATH="$HOME/.claude-memory/bin:$PATH"

# Restart shell
source ~/.zshrc
```

## Next Steps

After successful installation:

1. **Read the README**: [claude-skills/README.md](./README.md)
2. **Try the skills**: Start with `/superlocalmemoryv2:status`
3. **Create memories**: Use `/superlocalmemoryv2:remember` to add your first memories
4. **Explore profiles**: Use `/superlocalmemoryv2:profile` for multi-context isolation
5. **Check documentation**: See main [README.md](../README.md) for full system documentation

## Support

- **Installation issues**: Check this guide and [README.md](./README.md)
- **Skill errors**: Verify prerequisites and file permissions
- **System issues**: See main [docs/](../docs/) directory
- **GitHub issues**: [Report bugs](https://github.com/varun369/SuperLocalMemoryV2/issues)

## Quick Reference

**6 Core Skills:**
1. `remember` - Save memories
2. `recall` - Search memories
3. `list` - List memories
4. `status` - System status
5. `reset` - Reset operations
6. `profile` - Multi-profile management

**Installation Command:**
```bash
cp ~/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/claude-skills/superlocalmemoryv2-*-skill.md ~/.claude/skills/
```

**Verification:**
```bash
# In Claude CLI
/super<TAB>
```

**Test:**
```bash
/superlocalmemoryv2:status
```

---

**Installation complete? Type `/superlocalmemoryv2:status` in Claude CLI to verify.**
