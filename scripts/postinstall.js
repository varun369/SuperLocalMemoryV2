#!/usr/bin/env node
/**
 * SuperLocalMemory V2 - NPM Postinstall Script
 *
 * Copyright (c) 2026 Varun Pratap Bhardwaj
 * Solution Architect & Original Creator
 *
 * Licensed under MIT License (see LICENSE file)
 * Repository: https://github.com/varun369/SuperLocalMemoryV2
 *
 * ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
 */

const { spawnSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

console.log('\n════════════════════════════════════════════════════════════');
console.log('  SuperLocalMemory V2 - Post-Installation');
console.log('  by Varun Pratap Bhardwaj');
console.log('  https://github.com/varun369/SuperLocalMemoryV2');
console.log('════════════════════════════════════════════════════════════\n');

// Detect if this is a global install
const isGlobal = process.env.npm_config_global === 'true' ||
                 process.env.npm_config_global === true ||
                 (process.env.npm_config_prefix && !process.env.npm_config_prefix.includes('node_modules'));

if (!isGlobal) {
    console.log('📦 Local installation detected.');
    console.log('   SuperLocalMemory is designed for global installation.');
    console.log('   Run: npm install -g superlocalmemory');
    console.log('');
    console.log('⏩ Skipping system installation for local install.');
    console.log('');
    process.exit(0);
}

console.log('🌍 Global installation detected. Running system setup...\n');

// Find the package root (where install.sh/install.ps1 lives)
const packageRoot = path.join(__dirname, '..');
const installScript = os.platform() === 'win32'
    ? path.join(packageRoot, 'install.ps1')
    : path.join(packageRoot, 'install.sh');

// Check if install script exists
if (!fs.existsSync(installScript)) {
    console.error('❌ Error: Install script not found at ' + installScript);
    console.error('   Package may be corrupted. Please reinstall:');
    console.error('   npm uninstall -g superlocalmemory');
    console.error('   npm install -g superlocalmemory');
    process.exit(1);
}

// Run the appropriate install script
console.log('Running installer: ' + path.basename(installScript));
console.log('This will:');
console.log('  • Copy files to ~/.claude-memory/');
console.log('  • Configure MCP for 11+ AI tools');
console.log('  • Install universal skills');
console.log('  • Set up CLI commands\n');

let result;

if (os.platform() === 'win32') {
    // Windows: Run PowerShell script
    console.log('Platform: Windows (PowerShell)\n');
    result = spawnSync('powershell', [
        '-ExecutionPolicy', 'Bypass',
        '-File', installScript,
        '--non-interactive'
    ], {
        stdio: 'inherit',
        cwd: packageRoot
    });
} else {
    // Mac/Linux: Run bash script
    console.log('Platform: ' + (os.platform() === 'darwin' ? 'macOS' : 'Linux') + ' (Bash)\n');
    result = spawnSync('bash', [installScript, '--non-interactive'], {
        stdio: 'inherit',
        cwd: packageRoot
    });
}

if (result.error) {
    console.error('\n❌ Installation failed with error:', result.error.message);
    console.error('\nPlease run the install script manually:');
    if (os.platform() === 'win32') {
        console.error('  powershell -ExecutionPolicy Bypass -File "' + installScript + '"');
    } else {
        console.error('  bash "' + installScript + '"');
    }
    process.exit(1);
}

if (result.status !== 0) {
    console.error('\n❌ Installation script exited with code ' + result.status);
    console.error('\nPlease run the install script manually:');
    if (os.platform() === 'win32') {
        console.error('  powershell -ExecutionPolicy Bypass -File "' + installScript + '"');
    } else {
        console.error('  bash "' + installScript + '"');
    }
    process.exit(result.status);
}

console.log('\n════════════════════════════════════════════════════════════');
console.log('  ✅ SuperLocalMemory V2 installed successfully!');
console.log('════════════════════════════════════════════════════════════\n');

console.log('Quick Start:');
console.log('  slm remember "Your first memory"');
console.log('  slm recall "search query"');
console.log('  slm status');
console.log('  slm help\n');

console.log('Documentation:');
console.log('  README: https://github.com/varun369/SuperLocalMemoryV2');
console.log('  Wiki: https://github.com/varun369/SuperLocalMemoryV2/wiki');
console.log('  Local: ~/.claude-memory/\n');

console.log('MCP Integration:');
console.log('  Auto-configured for: Claude Desktop, Cursor, Windsurf, etc.');
console.log('  Restart your AI tool to activate.\n');
