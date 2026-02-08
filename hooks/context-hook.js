#!/usr/bin/env node
/**
 * SuperLocalMemory V2 - Session Start Context Hook
 * Copyright (c) 2026 Varun Pratap Bhardwaj
 * Licensed under MIT License
 *
 * Loads recent memories and learned patterns on Claude Code session start.
 * Outputs context to stderr (Claude Code reads hook stderr as context).
 * Fails gracefully — never blocks session start if DB is missing or errors occur.
 */

const { execFile } = require('child_process');
const { promisify } = require('util');
const path = require('path');
const fs = require('fs');

const execFileAsync = promisify(execFile);

const MEMORY_DIR = path.join(process.env.HOME, '.claude-memory');
const DB_PATH = path.join(MEMORY_DIR, 'memory.db');
const MEMORY_SCRIPT = path.join(MEMORY_DIR, 'memory_store_v2.py');

async function loadSessionContext() {
  // Fail gracefully if not installed
  if (!fs.existsSync(DB_PATH)) {
    return;
  }

  if (!fs.existsSync(MEMORY_SCRIPT)) {
    return;
  }

  try {
    // Get stats (memory_store_v2.py stats → JSON output)
    const { stdout: statsOutput } = await execFileAsync('python3', [
      MEMORY_SCRIPT, 'stats'
    ], { timeout: 5000 });

    // Get recent memories (memory_store_v2.py list <limit>)
    const { stdout: recentOutput } = await execFileAsync('python3', [
      MEMORY_SCRIPT, 'list', '5'
    ], { timeout: 5000 });

    // Build context output
    let context = '';

    if (statsOutput && statsOutput.trim()) {
      try {
        const stats = JSON.parse(statsOutput.trim());
        const total = stats.total_memories || 0;
        const clusters = stats.total_clusters || 0;
        if (total > 0) {
          context += 'SuperLocalMemory: ' + total + ' memories, ' + clusters + ' clusters loaded.\n';
        }
      } catch (e) {
        // Stats output wasn't JSON — use first line as-is
        context += 'SuperLocalMemory: ' + statsOutput.trim().split('\n')[0] + '\n';
      }
    }

    if (context) {
      process.stderr.write(context);
    }
  } catch (error) {
    // Never fail — session start must not be blocked
    // Silently ignore errors (timeout, missing python, etc.)
  }
}

loadSessionContext();
