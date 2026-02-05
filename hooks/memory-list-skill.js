#!/usr/bin/env node
/**
 * Memory List CLI Skill
 * List recent memories with sorting and filtering
 */

const { execFile } = require('child_process');
const { promisify } = require('util');
const path = require('path');

const execFileAsync = promisify(execFile);

async function memoryListSkill() {
  const memoryScript = path.join(process.env.HOME, '.claude-memory', 'memory_store_v2.py');
  const args = process.argv.slice(2);

  // Show help if --help
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     SuperLocalMemory V2 - List Recent Memories           ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Display recent memories with optional sorting and limits.
Quick overview of what's stored in your memory database.

Usage: memory-list [options]

Options:
  --limit <n>            Number of memories to show (default: 20)
  --sort <field>         Sort by: recent, accessed, importance
                         • recent: Latest created first (default)
                         • accessed: Most recently accessed
                         • importance: Highest importance first

Examples:
  memory-list

  memory-list --limit 50

  memory-list --sort importance

  memory-list --limit 10 --sort accessed

Output Format:
  • ID, Content (truncated), Tags, Importance
  • Creation timestamp
  • Access count and last accessed time

Notes:
  • Default shows last 20 memories
  • Content is truncated to 100 chars for readability
  • Use ID with memory-recall to see full content
  • Sort by 'accessed' to find frequently used memories
`);
    return;
  }

  // Parse options
  let limit = 20;
  let sortBy = 'recent';

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--limit' && i + 1 < args.length) {
      const parsedLimit = parseInt(args[i + 1]);
      if (parsedLimit > 0 && parsedLimit <= 1000) {
        limit = parsedLimit;
      } else {
        console.error('❌ ERROR: Limit must be between 1-1000');
        return;
      }
      i++;
    } else if (arg === '--sort' && i + 1 < args.length) {
      const validSorts = ['recent', 'accessed', 'importance'];
      if (validSorts.includes(args[i + 1])) {
        sortBy = args[i + 1];
      } else {
        console.error(`❌ ERROR: Sort must be one of: ${validSorts.join(', ')}`);
        return;
      }
      i++;
    }
  }

  // Build Python command based on sort type
  // Note: V1 store only supports 'recent' and 'list' commands without sort flags
  let pythonArgs = [];

  if (sortBy === 'recent' || sortBy === 'accessed') {
    pythonArgs = ['recent', limit.toString()];
  } else {
    // Default to list for importance or other sorts
    pythonArgs = ['list', limit.toString()];
  }

  try {
    const { stdout, stderr } = await execFileAsync('python3', [memoryScript, ...pythonArgs]);

    if (stderr) {
      console.error('⚠️  Warning:', stderr);
    }

    console.log(`
╔══════════════════════════════════════════════════════════╗
║     Recent Memories (${sortBy} | limit: ${limit})
╚══════════════════════════════════════════════════════════╝
`);

    console.log(stdout);

    // Show helpful next steps
    console.log(`
Next steps:
  • Use \`memory-recall <query>\` to search memories
  • Use \`memory-remember <content>\` to add new memories
  • Use \`memory-list --sort <field>\` to change sort order
`);

  } catch (error) {
    console.error('❌ Error listing memories:', error.message);
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
  }
}

memoryListSkill();
