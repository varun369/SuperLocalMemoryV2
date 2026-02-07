#!/bin/bash

# SuperLocalMemory V2 - Claude CLI Skills Installer
# Installs optional Claude CLI skills for convenient slash commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SKILLS_DIR="$HOME/.claude/skills"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SOURCE="$REPO_DIR/claude-skills"

echo "=========================================="
echo "SuperLocalMemory V2 - Skills Installer"
echo "=========================================="
echo ""

# Check if SuperLocalMemory V2 is installed
if [ ! -d "$HOME/.claude-memory" ]; then
    echo -e "${YELLOW}Warning:${NC} SuperLocalMemory V2 not found at ~/.claude-memory/"
    echo "Skills require SuperLocalMemory V2 to be installed first."
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        echo "Please install SuperLocalMemory V2 first: ./install.sh"
        exit 1
    fi
fi

# Check if Claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}Warning:${NC} Claude CLI not found in PATH"
    echo "Skills are designed for Claude CLI. You may not need them if using"
    echo "SuperLocalMemory V2 standalone via terminal commands."
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

# Check if skills source directory exists
if [ ! -d "$SKILLS_SOURCE" ]; then
    echo -e "${RED}Error:${NC} Skills directory not found: $SKILLS_SOURCE"
    echo "Please run this script from the SuperLocalMemoryV2-repo directory."
    exit 1
fi

# Count skills to install
SKILL_COUNT=$(find "$SKILLS_SOURCE" -name "superlocalmemoryv2-*.md" | wc -l | tr -d ' ')
if [ "$SKILL_COUNT" -eq 0 ]; then
    echo -e "${RED}Error:${NC} No skill files found in $SKILLS_SOURCE"
    exit 1
fi

echo "Found $SKILL_COUNT skills to install"
echo ""

# Create skills directory if it doesn't exist
if [ ! -d "$SKILLS_DIR" ]; then
    echo "Creating skills directory: $SKILLS_DIR"
    mkdir -p "$SKILLS_DIR"
fi

# Ask user for installation method
echo "Installation Methods:"
echo "  1. Symlink (recommended) - Changes in repo reflect immediately"
echo "  2. Copy - Stable, requires manual updates"
echo ""
read -p "Choose installation method (1 or 2): " -n 1 -r
echo ""

if [[ $REPLY == "1" ]]; then
    METHOD="symlink"
    echo "Installing via symlink..."
elif [[ $REPLY == "2" ]]; then
    METHOD="copy"
    echo "Installing via copy..."
else
    echo -e "${RED}Invalid choice.${NC} Please enter 1 or 2."
    exit 1
fi

# Install skills
echo ""
INSTALLED=0
FAILED=0

for skill_file in "$SKILLS_SOURCE"/superlocalmemoryv2-*.md; do
    skill_name=$(basename "$skill_file")
    target="$SKILLS_DIR/$skill_name"

    # Remove existing file or symlink
    if [ -e "$target" ] || [ -L "$target" ]; then
        echo "Removing existing: $skill_name"
        rm "$target"
    fi

    if [ "$METHOD" == "symlink" ]; then
        if ln -s "$skill_file" "$target"; then
            echo -e "${GREEN}✓${NC} Symlinked: $skill_name"
            ((INSTALLED++))
        else
            echo -e "${RED}✗${NC} Failed to symlink: $skill_name"
            ((FAILED++))
        fi
    else
        if cp "$skill_file" "$target"; then
            echo -e "${GREEN}✓${NC} Copied: $skill_name"
            ((INSTALLED++))
        else
            echo -e "${RED}✗${NC} Failed to copy: $skill_name"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo -e "Successfully installed: ${GREEN}$INSTALLED${NC} skills"
if [ "$FAILED" -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILED${NC} skills"
fi
echo "Installation method: $METHOD"
echo "Skills location: $SKILLS_DIR"
echo ""

# Verify installation
echo "Verifying installation..."
if [ "$INSTALLED" -eq "$SKILL_COUNT" ]; then
    echo -e "${GREEN}✓${NC} All skills installed successfully!"
else
    echo -e "${YELLOW}⚠${NC} Some skills failed to install."
fi

# List installed skills
echo ""
echo "Installed skills:"
ls -1 "$SKILLS_DIR"/superlocalmemoryv2-*.md | while read -r file; do
    skill_name=$(basename "$file" .md | sed 's/superlocalmemoryv2-//')
    echo "  - superlocalmemoryv2:$skill_name"
done

echo ""
echo "=========================================="
echo "Universal Skills Configuration"
echo "=========================================="
echo ""
echo "Detecting other tools that support skills/commands..."
echo ""

# Detect and configure Continue.dev
if [ -d "$HOME/.continue" ]; then
    echo "✓ Continue.dev detected"

    CONTINUE_CONFIG="$HOME/.continue/config.yaml"

    if [ -f "$REPO_DIR/configs/continue-skills.yaml" ]; then
        mkdir -p "$HOME/.continue"

        if [ -f "$CONTINUE_CONFIG" ]; then
            # Backup existing config
            cp "$CONTINUE_CONFIG" "$CONTINUE_CONFIG.backup.$(date +%Y%m%d-%H%M%S)"
            echo "  ✓ Backed up existing Continue.dev config"

            # Check if our skills already added
            if grep -q "slm-remember" "$CONTINUE_CONFIG" 2>/dev/null; then
                echo "  ○ SuperLocalMemory skills already configured"
            else
                echo "  ○ Config exists - manual merge recommended"
                echo "    See: $REPO_DIR/configs/continue-skills.yaml"
                echo "    Append slash commands to: $CONTINUE_CONFIG"
            fi
        else
            # Create new config with skills
            cp "$REPO_DIR/configs/continue-skills.yaml" "$CONTINUE_CONFIG"
            echo "  ✓ Continue.dev slash commands configured"
            echo "    Available: /slm-remember, /slm-recall, /slm-list, /slm-status"
        fi
    fi
fi

# Detect and configure Cody
if [ -d "$HOME/.vscode/extensions" ] && ls "$HOME/.vscode/extensions" 2>/dev/null | grep -q "sourcegraph.cody"; then
    echo "✓ Cody (VS Code) detected"

    if [ -f "$REPO_DIR/configs/cody-commands.json" ]; then
        VSCODE_SETTINGS="$HOME/.vscode/settings.json"
        mkdir -p "$HOME/.vscode"

        if [ -f "$VSCODE_SETTINGS" ]; then
            # Backup existing settings
            cp "$VSCODE_SETTINGS" "$VSCODE_SETTINGS.backup.$(date +%Y%m%d-%H%M%S)"
            echo "  ✓ Backed up existing VS Code settings"

            # Check if our commands already added
            if grep -q "slm-remember" "$VSCODE_SETTINGS" 2>/dev/null; then
                echo "  ○ SuperLocalMemory commands already configured"
            else
                echo "  ○ Settings exist - manual merge recommended"
                echo "    See: $REPO_DIR/configs/cody-commands.json"
                echo "    Add custom commands to: $VSCODE_SETTINGS"
            fi
        else
            # Create new settings with commands
            cp "$REPO_DIR/configs/cody-commands.json" "$VSCODE_SETTINGS"
            echo "  ✓ Cody custom commands configured"
            echo "    Available: /slm-remember, /slm-recall, /slm-context"
        fi
    fi
fi

# Summary
echo ""
if [ -d "$HOME/.continue" ] || ([ -d "$HOME/.vscode/extensions" ] && ls "$HOME/.vscode/extensions" 2>/dev/null | grep -q "sourcegraph.cody"); then
    echo "Universal integration configured! Your skills work in:"
    [ -d "$HOME/.continue" ] && echo "  • Continue.dev (VS Code)"
    ([ -d "$HOME/.vscode/extensions" ] && ls "$HOME/.vscode/extensions" 2>/dev/null | grep -q "sourcegraph.cody") && echo "  • Cody (VS Code)"
    echo "  • Claude CLI (if installed)"
else
    echo "No additional tools detected."
    echo "Skills configured for Claude CLI only."
fi

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. ${YELLOW}Restart Claude CLI${NC} to load the new skills"
echo "   (Skills are loaded at startup)"
echo ""
echo "2. Verify skills loaded:"
echo "   ${GREEN}/skills${NC}"
echo ""
echo "3. Try your first skill:"
echo "   ${GREEN}/superlocalmemoryv2:status${NC}"
echo ""
echo "4. Read documentation:"
echo "   - Quick overview: claude-skills/README.md"
echo "   - Full guide: claude-skills/CLAUDE_CLI_INSTALLATION.md"
echo ""

if [ "$METHOD" == "symlink" ]; then
    echo "Note: Using symlinks. To update skills:"
    echo "  cd $REPO_DIR"
    echo "  git pull"
    echo "  # Restart Claude CLI"
    echo ""
fi

if [ "$METHOD" == "copy" ]; then
    echo "Note: Using copies. To update skills:"
    echo "  cd $REPO_DIR"
    echo "  git pull"
    echo "  ./install-skills.sh"
    echo "  # Choose option 2 again"
    echo ""
fi

echo "=========================================="
echo ""
echo -e "${GREEN}✓ Claude CLI skills installation complete!${NC}"
echo ""
echo "Remember: Skills are OPTIONAL convenience wrappers."
echo "SuperLocalMemory V2 works standalone via terminal commands."
echo ""
