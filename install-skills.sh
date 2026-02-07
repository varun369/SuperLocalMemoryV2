#!/bin/bash

# SuperLocalMemory V2 - Universal Skills Installer
# Installs skills for Claude Code, Codex, Gemini CLI, Antigravity, and Windsurf

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SOURCE="$REPO_DIR/skills"

# Tool definitions (parallel arrays for bash 3.2 compatibility)
TOOL_IDS=("claude_code" "codex" "gemini_cli" "antigravity" "windsurf")
TOOL_NAMES=("Claude Code" "Codex" "Gemini CLI" "Antigravity" "Windsurf")
TOOL_DIRS=(
    "$HOME/.claude/skills"
    "$HOME/.codex/skills"
    "$HOME/.gemini/skills"
    "$HOME/.gemini/antigravity/skills"
    "$HOME/.windsurf/skills"
)

# Helper function to get tool name by ID
get_tool_name() {
    local tool_id="$1"
    for i in "${!TOOL_IDS[@]}"; do
        if [ "${TOOL_IDS[$i]}" = "$tool_id" ]; then
            echo "${TOOL_NAMES[$i]}"
            return
        fi
    done
    echo "$tool_id"
}

# Helper function to get tool directory by ID
get_tool_dir() {
    local tool_id="$1"
    for i in "${!TOOL_IDS[@]}"; do
        if [ "${TOOL_IDS[$i]}" = "$tool_id" ]; then
            echo "${TOOL_DIRS[$i]}"
            return
        fi
    done
    echo ""
}

# Skills to install (from skills/ directory)
SKILLS=(
    "slm-remember"
    "slm-recall"
    "slm-status"
    "slm-list-recent"
    "slm-build-graph"
    "slm-switch-profile"
)

echo "=========================================="
echo "SuperLocalMemory V2 - Universal Skills Installer"
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

# Check if skills source directory exists
if [ ! -d "$SKILLS_SOURCE" ]; then
    echo -e "${RED}Error:${NC} Skills directory not found: $SKILLS_SOURCE"
    echo "Please run this script from the SuperLocalMemoryV2-repo directory."
    exit 1
fi

# Verify all skill directories exist
echo "Verifying skill files..."
MISSING_SKILLS=0
for skill in "${SKILLS[@]}"; do
    if [ ! -d "$SKILLS_SOURCE/$skill" ]; then
        echo -e "${RED}✗${NC} Missing: $skill/"
        ((MISSING_SKILLS++))
    elif [ ! -f "$SKILLS_SOURCE/$skill/SKILL.md" ]; then
        echo -e "${RED}✗${NC} Missing: $skill/SKILL.md"
        ((MISSING_SKILLS++))
    else
        echo -e "${GREEN}✓${NC} Found: $skill/SKILL.md"
    fi
done

if [ "$MISSING_SKILLS" -gt 0 ]; then
    echo -e "${RED}Error:${NC} $MISSING_SKILLS skill(s) missing. Cannot proceed."
    exit 1
fi

echo ""
echo "Found ${#SKILLS[@]} skills to install"
echo ""

# Detect available tools
echo "=========================================="
echo "Detecting AI Tools"
echo "=========================================="
echo ""

DETECTED_TOOLS=()

for i in "${!TOOL_IDS[@]}"; do
    tool_id="${TOOL_IDS[$i]}"
    tool_name="${TOOL_NAMES[$i]}"
    tool_dir="${TOOL_DIRS[$i]}"
    parent_dir=$(dirname "$tool_dir")

    # Check if parent directory exists (tool is installed)
    if [ -d "$parent_dir" ]; then
        echo -e "${GREEN}✓${NC} $tool_name detected: $tool_dir"
        DETECTED_TOOLS+=("$tool_id")
    else
        echo -e "${BLUE}○${NC} $tool_name not found: $parent_dir"
    fi
done

echo ""

if [ ${#DETECTED_TOOLS[@]} -eq 0 ]; then
    echo -e "${YELLOW}Warning:${NC} No supported AI tools detected."
    echo ""
    echo "Supported tools:"
    for i in "${!TOOL_IDS[@]}"; do
        echo "  - ${TOOL_NAMES[$i]}: ${TOOL_DIRS[$i]}"
    done
    echo ""
    read -p "Do you want to continue and create directories anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
    # If user wants to continue, add all tools to install list
    for tool_id in "${TOOL_IDS[@]}"; do
        DETECTED_TOOLS+=("$tool_id")
    done
else
    echo "Will install skills for ${#DETECTED_TOOLS[@]} tool(s)"
    echo ""
fi

# Ask user for installation method
echo "Installation Methods:"
echo "  1. Symlink (recommended) - Changes in repo reflect immediately"
echo "  2. Copy - Stable, requires manual updates"
echo ""
read -p "Choose installation method (1 or 2): " -n 1 -r
echo ""
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

echo ""

# Install skills for each detected tool
TOTAL_INSTALLED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

for tool_id in "${DETECTED_TOOLS[@]}"; do
    tool_name=$(get_tool_name "$tool_id")
    echo "=========================================="
    echo "Installing for: $tool_name"
    echo "=========================================="

    skills_dir=$(get_tool_dir "$tool_id")

    # Create skills directory if it doesn't exist
    if [ ! -d "$skills_dir" ]; then
        echo "Creating directory: $skills_dir"
        if mkdir -p "$skills_dir"; then
            echo -e "${GREEN}✓${NC} Directory created"
        else
            echo -e "${RED}✗${NC} Failed to create directory"
            echo ""
            ((TOTAL_SKIPPED+=${#SKILLS[@]}))
            continue
        fi
    else
        echo "Directory exists: $skills_dir"
    fi

    echo ""

    # Install each skill
    for skill in "${SKILLS[@]}"; do
        source_file="$SKILLS_SOURCE/$skill/SKILL.md"
        target_file="$skills_dir/$skill.md"

        # Remove existing file or symlink
        if [ -e "$target_file" ] || [ -L "$target_file" ]; then
            rm "$target_file"
        fi

        if [ "$METHOD" == "symlink" ]; then
            if ln -s "$source_file" "$target_file" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Symlinked: $skill.md"
                ((TOTAL_INSTALLED++))
            else
                echo -e "${RED}✗${NC} Failed to symlink: $skill.md"
                ((TOTAL_FAILED++))
            fi
        else
            if cp "$source_file" "$target_file" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Copied: $skill.md"
                ((TOTAL_INSTALLED++))
            else
                echo -e "${RED}✗${NC} Failed to copy: $skill.md"
                ((TOTAL_FAILED++))
            fi
        fi
    done

    # Make skills executable (if they have execute permissions)
    chmod +x "$skills_dir"/*.md 2>/dev/null || true

    echo ""
done

# Installation Summary
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo ""
echo -e "Tools configured: ${BLUE}${#DETECTED_TOOLS[@]}${NC}"
echo -e "Skills installed: ${GREEN}$TOTAL_INSTALLED${NC}"
if [ "$TOTAL_FAILED" -gt 0 ]; then
    echo -e "Failed: ${RED}$TOTAL_FAILED${NC}"
fi
if [ "$TOTAL_SKIPPED" -gt 0 ]; then
    echo -e "Skipped: ${YELLOW}$TOTAL_SKIPPED${NC}"
fi
echo "Installation method: $METHOD"
echo ""

# List installation locations
echo "Skills installed to:"
for tool_id in "${DETECTED_TOOLS[@]}"; do
    tool_name=$(get_tool_name "$tool_id")
    tool_dir=$(get_tool_dir "$tool_id")
    if [ -d "$tool_dir" ] && [ "$(ls -A "$tool_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
        count=$(ls -1 "$tool_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✓${NC} $tool_name: $tool_dir ($count skills)"
    fi
done

echo ""

# Verify installation
EXPECTED_TOTAL=$((${#DETECTED_TOOLS[@]} * ${#SKILLS[@]}))
if [ "$TOTAL_INSTALLED" -eq "$EXPECTED_TOTAL" ]; then
    echo -e "${GREEN}✓${NC} All skills installed successfully!"
else
    echo -e "${YELLOW}⚠${NC} Some skills failed to install."
    echo "Expected: $EXPECTED_TOTAL, Installed: $TOTAL_INSTALLED"
fi

echo ""

# List available skills
echo "=========================================="
echo "Available Skills"
echo "=========================================="
echo ""
for skill in "${SKILLS[@]}"; do
    echo "  • $skill"
done
echo ""

# Legacy Claude CLI skills (from claude-skills/)
if [ -d "$REPO_DIR/claude-skills" ] && [ -d "$HOME/.claude/skills" ]; then
    echo "=========================================="
    echo "Legacy Claude CLI Skills"
    echo "=========================================="
    echo ""
    echo "Found legacy claude-skills/ directory for Claude CLI."
    echo "These are different from the universal skills above."
    echo ""
    read -p "Do you want to install legacy Claude CLI skills too? (y/n) " -n 1 -r
    echo ""
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        LEGACY_COUNT=0
        for skill_file in "$REPO_DIR/claude-skills"/superlocalmemoryv2-*.md; do
            if [ -f "$skill_file" ]; then
                skill_name=$(basename "$skill_file")
                target="$HOME/.claude/skills/$skill_name"

                if [ -e "$target" ] || [ -L "$target" ]; then
                    rm "$target"
                fi

                if [ "$METHOD" == "symlink" ]; then
                    ln -s "$skill_file" "$target" 2>/dev/null && ((LEGACY_COUNT++))
                else
                    cp "$skill_file" "$target" 2>/dev/null && ((LEGACY_COUNT++))
                fi
            fi
        done
        echo -e "${GREEN}✓${NC} Installed $LEGACY_COUNT legacy Claude CLI skills"
        echo ""
    fi
fi

# Next Steps
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. ${YELLOW}Restart your AI tool${NC} to load the new skills"
echo ""
echo "2. Verify skills are loaded:"
for tool_id in "${DETECTED_TOOLS[@]}"; do
    case "$tool_id" in
        "claude_code")
            echo "   ${GREEN}claude${NC} (type /skills to list)"
            ;;
        "codex")
            echo "   ${GREEN}codex${NC} (type /skills to list)"
            ;;
        "gemini_cli")
            echo "   ${GREEN}gemini${NC} (check available commands)"
            ;;
        "antigravity")
            echo "   ${GREEN}antigravity${NC} (check available commands)"
            ;;
        "windsurf")
            echo "   ${GREEN}windsurf${NC} (check available commands)"
            ;;
    esac
done
echo ""
echo "3. Try your first skill:"
echo "   ${GREEN}/slm-status${NC} or ${GREEN}/slm-remember \"test\"${NC}"
echo ""
echo "4. Read skill documentation:"
echo "   Each skill has detailed docs in: $SKILLS_SOURCE/<skill-name>/SKILL.md"
echo ""

if [ "$METHOD" == "symlink" ]; then
    echo "Note: Using symlinks. To update skills:"
    echo "  cd $REPO_DIR"
    echo "  git pull"
    echo "  # Restart your AI tool"
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
echo -e "${GREEN}✓ Universal skills installation complete!${NC}"
echo ""
echo "Skills installed for:"
for tool_id in "${DETECTED_TOOLS[@]}"; do
    tool_name=$(get_tool_name "$tool_id")
    echo "  • $tool_name"
done
echo ""
echo "Remember: Skills are OPTIONAL convenience wrappers."
echo "SuperLocalMemory V2 works standalone via terminal commands."
echo ""
