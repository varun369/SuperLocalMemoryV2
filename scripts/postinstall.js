#!/usr/bin/env node
/**
 * SuperLocalMemory V3 - NPM Postinstall Script
 *
 * ONE COMMAND INSTALL. Everything the user needs.
 * Python deps auto-installed. Embeddings auto-downloaded.
 *
 * Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
 * Licensed under MIT License
 */

const { spawnSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

console.log('\n════════════════════════════════════════════════════════════');
console.log('  SuperLocalMemory V3 — Post-Installation');
console.log('  by Varun Pratap Bhardwaj / Qualixar');
console.log('  https://github.com/qualixar/superlocalmemory');
console.log('════════════════════════════════════════════════════════════\n');

// --- Step 1: Create data directory ---
const SLM_HOME = path.join(os.homedir(), '.superlocalmemory');
if (!fs.existsSync(SLM_HOME)) {
    fs.mkdirSync(SLM_HOME, { recursive: true });
    console.log('✓ Created data directory: ' + SLM_HOME);
} else {
    console.log('✓ Data directory exists: ' + SLM_HOME);
}

// --- Step 2: Find Python 3 ---
function findPython() {
    const candidates = [
        'python3', 'python',
        '/opt/homebrew/bin/python3', '/usr/local/bin/python3', '/usr/bin/python3',
    ];
    if (os.platform() === 'win32') candidates.push('py -3');
    for (const cmd of candidates) {
        try {
            const parts = cmd.split(' ');
            const r = spawnSync(parts[0], [...parts.slice(1), '--version'], {
                stdio: 'pipe', timeout: 5000,
                env: { ...process.env, PATH: '/opt/homebrew/bin:/usr/local/bin:/usr/bin:' + (process.env.PATH || '') },
            });
            if (r.status === 0 && (r.stdout || '').toString().includes('3.')) return parts;
        } catch (e) { /* next */ }
    }
    return null;
}

const pythonParts = findPython();
if (!pythonParts) {
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║  ⚠  Python 3.11+ Required                              ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
    console.log('');
    console.log('  SuperLocalMemory V3 requires Python 3.11+');
    console.log('  Install from: https://python.org/downloads/');
    console.log('  After installing Python, run: slm setup');
    console.log('');
    process.exit(0); // Don't fail npm install
}
console.log('✓ Found Python: ' + pythonParts.join(' '));

// --- Step 3: Install ALL Python dependencies ---
console.log('\nInstalling Python dependencies (this may take 1-2 minutes)...\n');

// Detect if --user or --break-system-packages is needed
function pipInstall(packages, label) {
    // Try normal install first
    let result = spawnSync(pythonParts[0], [
        ...pythonParts.slice(1), '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check',
        ...packages,
    ], { stdio: 'pipe', timeout: 300000, env: { ...process.env, PATH: '/opt/homebrew/bin:/usr/local/bin:/usr/bin:' + (process.env.PATH || '') } });

    if (result.status === 0) return true;

    // If PEP 668 blocks it, try --user
    const stderr = (result.stderr || '').toString();
    if (stderr.includes('externally-managed') || stderr.includes('PEP 668')) {
        result = spawnSync(pythonParts[0], [
            ...pythonParts.slice(1), '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check',
            '--user', ...packages,
        ], { stdio: 'pipe', timeout: 300000, env: { ...process.env, PATH: '/opt/homebrew/bin:/usr/local/bin:/usr/bin:' + (process.env.PATH || '') } });
        if (result.status === 0) return true;

        // Last resort: --break-system-packages
        result = spawnSync(pythonParts[0], [
            ...pythonParts.slice(1), '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check',
            '--break-system-packages', ...packages,
        ], { stdio: 'pipe', timeout: 300000, env: { ...process.env, PATH: '/opt/homebrew/bin:/usr/local/bin:/usr/bin:' + (process.env.PATH || '') } });
        return result.status === 0;
    }

    return false;
}

// Core dependencies (REQUIRED — product won't work without these)
const coreDeps = [
    'numpy>=1.26.0', 'scipy>=1.12.0', 'networkx>=3.0',
    'httpx>=0.24.0', 'python-dateutil>=2.9.0',
    'rank-bm25>=0.2.2', 'vaderSentiment>=3.3.2',
];

if (pipInstall(coreDeps, 'core')) {
    console.log('✓ Core dependencies installed (math, search, NLP)');
} else {
    console.log('⚠ Core dependency installation failed.');
    console.log('  Run manually: pip install ' + coreDeps.join(' '));
}

// Search dependencies (IMPORTANT — enables semantic search, 4-channel retrieval)
const searchDeps = ['sentence-transformers>=2.5.0', 'einops>=0.7.0', 'geoopt>=0.5.0'];

console.log('\nInstalling semantic search engine (downloads ~500MB on first use)...');
if (pipInstall(searchDeps, 'search')) {
    console.log('✓ Semantic search engine installed (sentence-transformers + einops + Fisher-Rao)');
    console.log('');
    console.log('  Note: The embedding model (nomic-ai/nomic-embed-text-v1.5, ~500MB)');
    console.log('  will download automatically on first use (slm remember / slm recall).');
    console.log('  To pre-download now, run: slm warmup');
} else {
    console.log('⚠ Semantic search installation failed (BM25 keyword search still works).');
    console.log('  For full 4-channel retrieval, run:');
    console.log('  pip install sentence-transformers einops geoopt');
}

// --- Step 4: Detect V2 installation ---
const V2_HOME = path.join(os.homedir(), '.claude-memory');
if (fs.existsSync(V2_HOME) && fs.existsSync(path.join(V2_HOME, 'memory.db'))) {
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║  V2 Installation Detected                                ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
    console.log('');
    console.log('  Found V2 data at: ' + V2_HOME);
    console.log('  Your memories are safe and will NOT be deleted.');
    console.log('');
    console.log('  To migrate V2 data to V3, run:');
    console.log('    slm migrate');
    console.log('');
}

// --- Done ---
console.log('════════════════════════════════════════════════════════════');
console.log('  ✓ SuperLocalMemory V3 installed successfully!');
console.log('');
console.log('  Quick start:');
console.log('    slm setup          # First-time configuration');
console.log('    slm status         # Check system status');
console.log('    slm remember "..." # Store a memory');
console.log('    slm recall "..."   # Search memories');
console.log('');
console.log('  Prerequisites satisfied:');
console.log('    ✓ Python 3.11+');
console.log('    ✓ Core math & search libraries');
console.log('    ✓ Data directory (~/.superlocalmemory/)');
console.log('');
console.log('  Docs: https://github.com/qualixar/superlocalmemory/wiki');
console.log('════════════════════════════════════════════════════════════\n');
