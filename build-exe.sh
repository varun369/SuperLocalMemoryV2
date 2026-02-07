#!/bin/bash
# SuperLocalMemory V2 - Windows Installer Builder (Bash Script for macOS/Linux)
#
# Copyright (c) 2026 Varun Pratap Bhardwaj
# Licensed under MIT License
# Repository: https://github.com/varun369/SuperLocalMemoryV2
#
# ATTRIBUTION REQUIRED: This notice must be preserved in all copies.

set -e

# Configuration
VERSION="2.1.0"
OUTPUT_DIR="dist"
OUTPUT_EXE="SuperLocalMemory-Setup-v${VERSION}-windows.exe"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Banner
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  SuperLocalMemory V2 - Windows Installer Builder"
echo "  Version: $VERSION"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

# Check if running in repo root
if [ ! -f "installer.iss" ]; then
    log_error "Must run from repository root directory"
    log_error "Expected file: installer.iss"
    exit 1
fi
log_success "Repository structure validated"

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker not found!"
    log_info "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi
log_success "Docker: $(docker --version)"

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon not running"
    log_info "Start Docker Desktop and try again"
    exit 1
fi
log_success "Docker daemon is running"

# Create output directory
if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    log_success "Created $OUTPUT_DIR directory"
fi

# Create assets directory if missing
if [ ! -d "assets" ]; then
    mkdir -p assets
    log_success "Created assets directory"
fi

# Create installer documentation
log_info "Creating installer documentation..."

mkdir -p docs

cat > docs/WINDOWS-INSTALL-README.txt << 'EOF'
SuperLocalMemory V2.1.0 - Windows Installation
==============================================

Thank you for installing SuperLocalMemory V2!

This installer will:
1. Copy all necessary files to your system
2. Install Python modules to %USERPROFILE%\.claude-memory\
3. Configure MCP integration for supported IDEs
4. Install universal skills for AI tools
5. Add 'slm' command to your system PATH

System Requirements:
--------------------
• Windows 10 or higher (64-bit)
• Python 3.8 or higher
• 100 MB disk space
• Internet connection (for Python packages)

After Installation:
-------------------
1. Open Command Prompt or PowerShell
2. Run: slm status
3. Test: slm remember "Test memory"
4. Search: slm recall "test"

Documentation:
--------------
• GitHub: https://github.com/varun369/SuperLocalMemoryV2
• Wiki: https://github.com/varun369/SuperLocalMemoryV2/wiki
• Issues: https://github.com/varun369/SuperLocalMemoryV2/issues

Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
EOF

cat > docs/WINDOWS-POST-INSTALL.txt << 'EOF'
SuperLocalMemory V2.1.0 - Installation Complete!
================================================

Installation successful!

Location: %USERPROFILE%\.claude-memory\
CLI Command: slm

Quick Start:
------------
1. Open a NEW Command Prompt or PowerShell window
   (Required for PATH changes to take effect)

2. Verify installation:
   > slm status

3. Store your first memory:
   > slm remember "React is my preferred framework" --tags frontend

4. Search memories:
   > slm recall "React"

5. Launch dashboard (optional):
   > powershell -ExecutionPolicy Bypass -File start-dashboard.ps1

Integrated IDEs:
----------------
SuperLocalMemory is now available in:
✓ Claude Desktop (restart to see @SuperLocalMemory)
✓ Cursor (restart IDE)
✓ Windsurf (restart IDE)
✓ Continue.dev (use /slm-* skills)
✓ Cody (use custom commands)
✓ And 6 more tools...

Troubleshooting:
----------------
• 'slm' not found: Open NEW terminal window
• Python errors: Ensure Python 3.8+ is installed
• Permission errors: Run PowerShell as Administrator

Documentation: https://github.com/varun369/SuperLocalMemoryV2/wiki
Support: https://github.com/varun369/SuperLocalMemoryV2/issues

Copyright (c) 2026 Varun Pratap Bhardwaj
EOF

log_success "Created installer documentation"

# Pre-build validation
log_info "Running pre-build validation..."

REQUIRED_FILES=(
    "install.ps1"
    "src/memory_store_v2.py"
    "mcp_server.py"
    "LICENSE"
    "README.md"
)

ALL_VALID=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "Found: $file"
    else
        log_error "Missing: $file"
        ALL_VALID=false
    fi
done

if [ "$ALL_VALID" = false ]; then
    log_error "Required files missing. Aborting build."
    exit 1
fi

# Build Docker image
log_info "Building Docker image (this may take 5-10 minutes on first run)..."
docker build -t superlocalmemory-builder -f Dockerfile.innosetup .

if [ $? -ne 0 ]; then
    log_error "Docker image build failed"
    exit 1
fi
log_success "Docker image built"

# Run build in Docker
log_info "Running Inno Setup in Docker..."
docker run --rm \
    -v "$(pwd):/build" \
    -w /build \
    superlocalmemory-builder

if [ $? -eq 0 ]; then
    log_success "Docker build successful"

    # Check output
    OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_EXE"
    if [ -f "$OUTPUT_PATH" ]; then
        FILE_SIZE=$(ls -lh "$OUTPUT_PATH" | awk '{print $5}')
        log_success "Created: $OUTPUT_PATH ($FILE_SIZE)"
    else
        log_error "Output file not found: $OUTPUT_PATH"
        exit 1
    fi
else
    log_error "Docker build failed"
    exit 1
fi

# Generate checksums
log_info "Generating checksums..."
if [ -f "$OUTPUT_PATH" ]; then
    # SHA256
    if command -v shasum &> /dev/null; then
        SHA256=$(shasum -a 256 "$OUTPUT_PATH" | awk '{print $1}')
        echo "$SHA256  $OUTPUT_EXE" > "$OUTPUT_PATH.sha256"
        log_success "SHA256: $SHA256"
    elif command -v sha256sum &> /dev/null; then
        SHA256=$(sha256sum "$OUTPUT_PATH" | awk '{print $1}')
        echo "$SHA256  $OUTPUT_EXE" > "$OUTPUT_PATH.sha256"
        log_success "SHA256: $SHA256"
    else
        log_warning "SHA256 tool not found, skipping checksum"
    fi

    # MD5
    if command -v md5 &> /dev/null; then
        MD5=$(md5 -q "$OUTPUT_PATH")
        echo "$MD5  $OUTPUT_EXE" > "$OUTPUT_PATH.md5"
        log_success "MD5: $MD5"
    elif command -v md5sum &> /dev/null; then
        MD5=$(md5sum "$OUTPUT_PATH" | awk '{print $1}')
        echo "$MD5  $OUTPUT_EXE" > "$OUTPUT_PATH.md5"
        log_success "MD5: $MD5"
    else
        log_warning "MD5 tool not found, skipping checksum"
    fi
fi

# Final summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Build Summary"
echo "═══════════════════════════════════════════════════════════"
echo ""
log_success "Build completed successfully!"
echo ""
log_info "Output: $OUTPUT_DIR/$OUTPUT_EXE"
echo ""
log_info "Next steps:"
echo "  1. Test the installer on a clean Windows VM"
echo "  2. Upload to GitHub Releases"
echo "  3. Update download links in README.md"
echo ""
log_info "Upload command:"
echo "  gh release upload v$VERSION $OUTPUT_DIR/$OUTPUT_EXE"
echo ""

# List all generated files
echo "Generated files:"
ls -lh "$OUTPUT_DIR/$OUTPUT_EXE"* | while read -r line; do
    echo "  • $(echo "$line" | awk '{print $9, "(" $5 ")"}')"
done
echo ""

log_success "All done!"
echo ""
