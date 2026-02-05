#!/bin/bash
# SuperLocalMemory V2 Installation Script

set -e

INSTALL_DIR="${HOME}/.claude-memory"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing SuperLocalMemory V2..."

# Create installation directory
mkdir -p "${INSTALL_DIR}"

# Copy source files
echo "Copying source files..."
cp -r "${REPO_DIR}/src/"* "${INSTALL_DIR}/"

# Copy hooks
echo "Copying hooks..."
mkdir -p "${INSTALL_DIR}/hooks"
cp -r "${REPO_DIR}/hooks/"* "${INSTALL_DIR}/hooks/"

# Copy CLI wrappers
echo "Copying CLI wrappers..."
mkdir -p "${INSTALL_DIR}/bin"
cp -r "${REPO_DIR}/bin/"* "${INSTALL_DIR}/bin/"
chmod +x "${INSTALL_DIR}/bin/"*

# Copy config if not exists
if [ ! -f "${INSTALL_DIR}/config.json" ]; then
    echo "Creating default config..."
    cp "${REPO_DIR}/config.json" "${INSTALL_DIR}/config.json"
fi

# Create necessary directories
mkdir -p "${INSTALL_DIR}/backups"
mkdir -p "${INSTALL_DIR}/profiles"
mkdir -p "${INSTALL_DIR}/vectors"
mkdir -p "${INSTALL_DIR}/cold-storage"
mkdir -p "${INSTALL_DIR}/jobs"

# Make Python scripts executable
chmod +x "${INSTALL_DIR}/"*.py

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import sqlite3, json, re" 2>/dev/null || {
    echo "Warning: Some Python dependencies may be missing"
    echo "Required: sqlite3, json, re (usually built-in)"
}

# Add bin to PATH instruction
echo ""
echo "Installation complete!"
echo ""
echo "To use the CLI commands, add this to your ~/.zshrc or ~/.bashrc:"
echo "export PATH=\"\${HOME}/.claude-memory/bin:\${PATH}\""
echo ""
echo "Then run: source ~/.zshrc  (or ~/.bashrc)"
echo ""
echo "Available commands:"
echo "  memory-reset   - Reset/clean memory database"
echo "  memory-profile - Manage memory profiles"
echo "  memory-status  - Check memory status"
