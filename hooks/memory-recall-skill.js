#!/usr/bin/env node
/**
 * Memory Recall CLI Skill
 * Search and retrieve memories with advanced filtering
 */

const { execFile } = require('child_process');
const { promisify } = require('util');
const path = require('path');

const execFileAsync = promisify(execFile);

async function memoryRecallSkill() {
  const memoryScript = path.join(process.env.HOME, '.claude-memory', 'memory_store_v2.py');
  const args = process.argv.slice(2);

  // Show help if no args or --help
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     SuperLocalMemory V2 - Recall (Search Memories)       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Search your memory store using semantic search and filters.
Finds relevant memories using TF-IDF similarity and metadata.

Usage: memory-recall <query> [options]

Arguments:
  <query>                 Search query (required)

Options:
  --limit <n>            Maximum results to return (default: 10)
  --full                 Show complete content without truncation

Examples:
  memory-recall "authentication bug"

  memory-recall "API configuration" --limit 5

  memory-recall "security best practices" --full

  memory-recall "user preferences"

Output Format:
  • Ranked by relevance (TF-IDF cosine similarity)
  • Shows: ID, Content, Tags, Importance, Timestamp
  • Higher scores = better matches
  • Smart truncation: full content if <5000 chars, preview if ≥5000 chars
  • Use --full flag to always show complete content

Notes:
  • Uses local TF-IDF search (no external APIs)
  • Searches content, summary, and tags
  • Empty query returns recent memories
  • Use quotes for multi-word queries
`);
    return;
  }

  // Parse query and options
  let query = null;
  const pythonArgs = ['search'];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--limit' && i + 1 < args.length) {
      // Note: V1 store doesn't support --limit in search, will truncate output instead
      i++; // Skip but don't add to pythonArgs
    } else if (arg === '--full') {
      pythonArgs.push('--full');
    } else if (!arg.startsWith('--') && query === null) {
      query = arg;
    }
  }

  // Validate query
  if (!query || query.trim().length === 0) {
    console.log(`
❌ ERROR: Search query required

Usage: memory-recall <query> [options]

Example:
  memory-recall "search term" --limit 10

Use --help for more information
`);
    return;
  }

  // Add query to Python args
  pythonArgs.push(query);

  try {
    const { stdout, stderr } = await execFileAsync('python3', [memoryScript, ...pythonArgs]);

    if (stderr) {
      console.error('⚠️  Warning:', stderr);
    }

    console.log(stdout);

  } catch (error) {
    console.error('❌ Error searching memories:', error.message);
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
  }
}

memoryRecallSkill();
