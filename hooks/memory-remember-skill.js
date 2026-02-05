#!/usr/bin/env node
/**
 * Memory Remember CLI Skill
 * Save memories with tags, project context, and importance levels
 */

const { execFile } = require('child_process');
const { promisify } = require('util');
const path = require('path');

const execFileAsync = promisify(execFile);

async function memoryRememberSkill() {
  const memoryScript = path.join(process.env.HOME, '.claude-memory', 'memory_store_v2.py');
  const args = process.argv.slice(2);

  // Show help if no args or --help
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     SuperLocalMemory V2 - Remember (Save Memory)         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Save important information to your persistent memory store.
Memories are indexed, searchable, and integrated with graph knowledge.

Usage: memory-remember <content> [options]

Arguments:
  <content>               The memory content to save (required)

Options:
  --tags <tag1,tag2>      Comma-separated tags for categorization
  --project <path>        Project path context

Examples:
  memory-remember "API key stored in .env file" --tags security,config

  memory-remember "User prefers tabs over spaces"

  memory-remember "Bug in auth.js line 42" --project ~/work/app --tags bug

  memory-remember "Meeting notes: Q1 launch March 15" --tags meeting,deadline

Notes:
  • Content is deduplicated automatically
  • Tags enable fast filtering during recall
  • Project context links memories to codebases
  • Use semantic search to find related memories
`);
    return;
  }

  // Parse content (first non-flag argument) and options
  let content = null;
  let tags = null;
  let project = null;

  let i = 0;
  while (i < args.length) {
    const arg = args[i];

    if (arg === '--tags' && i + 1 < args.length) {
      tags = args[i + 1];
      i += 2; // Skip flag and value
    } else if (arg === '--project' && i + 1 < args.length) {
      project = args[i + 1];
      i += 2; // Skip flag and value
    } else if (!arg.startsWith('--') && content === null) {
      content = arg;
      i++;
    } else {
      i++;
    }
  }

  // Validate content
  if (!content || content.trim().length === 0) {
    console.log(`
❌ ERROR: Memory content required

Usage: memory-remember <content> [options]

Example:
  memory-remember "Important information here" --tags example

Use --help for more information
`);
    return;
  }

  // Build Python command: add <content> [--project <path>] [--tags tag1,tag2]
  const pythonArgs = ['add', content];

  if (project) {
    pythonArgs.push('--project', project);
  }

  if (tags) {
    pythonArgs.push('--tags', tags);
  }

  try {
    const { stdout, stderr } = await execFileAsync('python3', [memoryScript, ...pythonArgs]);

    if (stderr) {
      console.error('⚠️  Warning:', stderr);
    }

    console.log(stdout);
    console.log('✅ Memory saved successfully\n');

    // Show helpful next steps
    console.log('Next steps:');
    console.log('  • Use `memory-recall <query>` to search this memory');
    console.log('  • Use `memory-list` to see recent memories');

  } catch (error) {
    console.error('❌ Error saving memory:', error.message);
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
  }
}

memoryRememberSkill();
