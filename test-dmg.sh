#!/usr/bin/env bash
#
# SuperLocalMemory V2 - DMG Testing Script
#
# Copyright (c) 2026 Varun Pratap Bhardwaj
# Solution Architect & Original Creator
#
# Licensed under MIT License (see LICENSE file)
# Repository: https://github.com/varun369/SuperLocalMemoryV2
#
# ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

DMG_FILE="SuperLocalMemory-v2.1.0-macos.dmg"

if [ ! -f "${DMG_FILE}" ]; then
    log_error "DMG file not found: ${DMG_FILE}"
    exit 1
fi

log_info "Testing DMG: ${DMG_FILE}"
echo ""

# Test 1: DMG Integrity
log_info "Test 1: Checking DMG integrity..."
if hdiutil verify "${DMG_FILE}" 2>&1 | grep -q "verified"; then
    log_success "DMG integrity check passed"
else
    log_error "DMG integrity check failed"
    exit 1
fi

# Test 2: Mount DMG
log_info "Test 2: Mounting DMG..."
MOUNT_OUTPUT=$(hdiutil attach "${DMG_FILE}" -nobrowse -readonly)
MOUNT_POINT=$(echo "$MOUNT_OUTPUT" | grep -E '/Volumes/' | awk '{print $3}')

if [ -z "$MOUNT_POINT" ]; then
    log_error "Failed to mount DMG"
    exit 1
fi

log_success "DMG mounted at: $MOUNT_POINT"

# Test 3: Verify Contents
log_info "Test 3: Checking DMG contents..."

REQUIRED_FILES=(
    "SuperLocalMemory/install.sh"
    "SuperLocalMemory/src"
    "SuperLocalMemory/bin"
    "SuperLocalMemory/configs"
    "SuperLocalMemory/skills"
    "SuperLocalMemory/mcp_server.py"
    "SuperLocalMemory/README.md"
    "SuperLocalMemory/LICENSE"
    "SuperLocalMemory/ATTRIBUTION.md"
    "SuperLocalMemory/README-INSTALLATION.txt"
    "SuperLocalMemory/INSTALL"
    "Applications"
)

ALL_PRESENT=true
for item in "${REQUIRED_FILES[@]}"; do
    if [ -e "${MOUNT_POINT}/${item}" ]; then
        log_success "  ✓ ${item}"
    else
        log_error "  ✗ ${item} (MISSING)"
        ALL_PRESENT=false
    fi
done

if [ "$ALL_PRESENT" = false ]; then
    log_error "Some required files are missing"
    hdiutil detach "${MOUNT_POINT}" -quiet
    exit 1
fi

# Test 4: Check installer script
log_info "Test 4: Checking installer script..."
if [ -x "${MOUNT_POINT}/SuperLocalMemory/install.sh" ]; then
    log_success "install.sh is executable"
else
    log_error "install.sh is not executable"
    hdiutil detach "${MOUNT_POINT}" -quiet
    exit 1
fi

# Test 5: Check Applications symlink
log_info "Test 5: Checking Applications symlink..."
if [ -L "${MOUNT_POINT}/Applications" ]; then
    TARGET=$(readlink "${MOUNT_POINT}/Applications")
    if [ "$TARGET" = "/Applications" ]; then
        log_success "Applications symlink is correct"
    else
        log_error "Applications symlink points to wrong location: $TARGET"
    fi
else
    log_error "Applications symlink not found"
fi

# Test 6: Check file sizes
log_info "Test 6: Checking file sizes..."
INSTALLER_SIZE=$(du -sh "${MOUNT_POINT}/SuperLocalMemory" | awk '{print $1}')
log_success "Installer size: ${INSTALLER_SIZE}"

# Test 7: Verify attribution
log_info "Test 7: Checking attribution headers..."
if grep -q "Varun Pratap Bhardwaj" "${MOUNT_POINT}/SuperLocalMemory/src/memory_store_v2.py"; then
    log_success "Attribution headers present"
else
    log_error "Attribution headers missing"
fi

# Test 8: Check INSTALL wrapper
log_info "Test 8: Checking INSTALL wrapper..."
if [ -x "${MOUNT_POINT}/SuperLocalMemory/INSTALL" ]; then
    log_success "INSTALL wrapper is executable"
else
    log_error "INSTALL wrapper is not executable"
fi

# Cleanup
log_info "Unmounting DMG..."
hdiutil detach "${MOUNT_POINT}" -quiet
log_success "DMG unmounted"

echo ""
echo "============================================================================"
log_success "ALL TESTS PASSED!"
echo "============================================================================"
echo ""
echo "DMG is ready for distribution."
echo ""
echo "To test installation:"
echo "  1. Open ${DMG_FILE}"
echo "  2. Double-click INSTALL"
echo "  3. Follow prompts"
echo "  4. Run: slm status"
echo ""
