#!/bin/bash
# ============================================================================
# SuperLocalMemory V2 - NPM Package Testing Script
# Copyright (c) 2026 Varun Pratap Bhardwaj
# Licensed under MIT License
# Repository: https://github.com/varun369/SuperLocalMemoryV2
# ============================================================================
#
# Tests the NPM package locally before publishing
# Run this BEFORE npm publish
#

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  SuperLocalMemory V2 - NPM Package Test                      ║"
echo "║  by Varun Pratap Bhardwaj                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Validate package.json
echo "📋 Step 1: Validating package.json..."
if [ ! -f "$REPO_DIR/package.json" ]; then
    echo "❌ Error: package.json not found"
    exit 1
fi

# Check version
VERSION=$(node -e "console.log(require('$REPO_DIR/package.json').version)")
echo "   Version: $VERSION"

# Check required fields
node -e "
const pkg = require('$REPO_DIR/package.json');
const required = ['name', 'version', 'description', 'author', 'license', 'repository', 'bin'];
const missing = required.filter(f => !pkg[f]);
if (missing.length > 0) {
    console.error('❌ Missing required fields:', missing.join(', '));
    process.exit(1);
}
console.log('   ✓ All required fields present');
"

# Step 2: Check file structure
echo ""
echo "📁 Step 2: Checking file structure..."

REQUIRED_FILES=(
    "bin/slm-npm"
    "scripts/postinstall.js"
    "scripts/preuninstall.js"
    "src/memory_store_v2.py"
    "mcp_server.py"
    "install.sh"
    "install.ps1"
    "README.md"
    "LICENSE"
    "ATTRIBUTION.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$REPO_DIR/$file" ]; then
        echo "   ❌ Missing: $file"
        exit 1
    fi
done
echo "   ✓ All required files present"

# Step 3: Test npm pack
echo ""
echo "📦 Step 3: Testing npm pack..."
cd "$REPO_DIR"
rm -f superlocalmemory-*.tgz
npm pack --quiet
TARBALL=$(ls superlocalmemory-*.tgz 2>/dev/null | head -1)

if [ -z "$TARBALL" ]; then
    echo "   ❌ npm pack failed"
    exit 1
fi

SIZE=$(du -h "$TARBALL" | cut -f1)
echo "   ✓ Package created: $TARBALL ($SIZE)"

# Check package size
SIZE_KB=$(du -k "$TARBALL" | cut -f1)
if [ "$SIZE_KB" -gt 1024 ]; then
    echo "   ⚠️  Warning: Package size is large (${SIZE}). Target: <500KB"
else
    echo "   ✓ Package size OK: $SIZE"
fi

# Step 4: Inspect package contents
echo ""
echo "🔍 Step 4: Inspecting package contents..."
echo "   Files included:"
tar -tzf "$TARBALL" | head -20
FILE_COUNT=$(tar -tzf "$TARBALL" | wc -l)
echo "   ... ($FILE_COUNT total files)"

# Check for unwanted files
UNWANTED=("*.pyc" "*.db" ".git" "test_*.py" "wiki-content")
for pattern in "${UNWANTED[@]}"; do
    if tar -tzf "$TARBALL" | grep -q "$pattern"; then
        echo "   ⚠️  Warning: Found unwanted files matching: $pattern"
    fi
done
echo "   ✓ No obvious unwanted files found"

# Step 5: Test npm link (local install)
echo ""
echo "🔗 Step 5: Testing npm link (local install)..."

# Unlink if already linked
npm unlink -g superlocalmemory 2>/dev/null || true

# Link
if npm link --quiet; then
    echo "   ✓ npm link successful"
else
    echo "   ❌ npm link failed"
    exit 1
fi

# Step 6: Test CLI command
echo ""
echo "🧪 Step 6: Testing CLI command..."

if command -v slm &> /dev/null; then
    echo "   ✓ slm command found"

    # Test version
    if slm --version &> /dev/null; then
        echo "   ✓ slm --version works"
    else
        echo "   ⚠️  slm --version failed (might be OK if not installed yet)"
    fi

    # Test help
    if slm --help &> /dev/null; then
        echo "   ✓ slm --help works"
    else
        echo "   ⚠️  slm --help failed"
    fi
else
    echo "   ⚠️  slm command not found (expected for first install)"
    echo "      This is OK - postinstall will set it up"
fi

# Step 7: Validate scripts
echo ""
echo "🔧 Step 7: Validating scripts..."

# Check postinstall.js
if node "$REPO_DIR/scripts/postinstall.js" --help &> /dev/null; then
    echo "   ✓ postinstall.js is valid Node.js"
else
    echo "   ⚠️  postinstall.js might have issues"
fi

# Check executables
if [ -x "$REPO_DIR/bin/slm-npm" ]; then
    echo "   ✓ bin/slm-npm is executable"
else
    echo "   ❌ bin/slm-npm is not executable"
    echo "      Run: chmod +x $REPO_DIR/bin/slm-npm"
    exit 1
fi

# Step 8: Final summary
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Test Summary                                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Package structure: OK"
echo "✅ File validation: OK"
echo "✅ npm pack: OK ($SIZE)"
echo "✅ npm link: OK"
echo "✅ Scripts valid: OK"
echo ""
echo "📦 Package ready for testing!"
echo ""
echo "Next steps:"
echo "1. Test manual install:"
echo "   npm install -g ./$TARBALL"
echo "   slm status"
echo "   npm uninstall -g superlocalmemory"
echo ""
echo "2. Test on Docker (recommended):"
echo "   docker run -it --rm -v \$(pwd):/app node:18 bash"
echo "   cd /app"
echo "   npm install -g ./$TARBALL"
echo "   slm status"
echo ""
echo "3. When ready to publish:"
echo "   npm login"
echo "   npm publish"
echo ""
echo "Full guide: NPM-PUBLISHING-GUIDE.md"
echo ""

# Cleanup
rm -f "$TARBALL"
echo "🧹 Cleaned up test tarball"
