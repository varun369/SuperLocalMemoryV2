#!/usr/bin/env node
/**
 * Memory Reset CLI Skill
 * Provides /memory-reset command with safety warnings
 */

const { execFile } = require('child_process');
const { promisify } = require('util');
const path = require('path');
const readline = require('readline');

const execFileAsync = promisify(execFile);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

async function memoryResetSkill() {
  const resetScript = path.join(process.env.HOME, '.claude-memory', 'memory-reset.py');
  const args = process.argv.slice(2); // Get command line arguments

  // Show help if no args
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║       SuperLocalMemory V2 - Reset Commands              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Usage: /memory-reset <command> [options]

Commands:
  status              Show current memory system status (SAFE)
  soft                Clear all memories, keep V2 schema (⚠️  DESTRUCTIVE)
  hard --confirm      Delete everything, reinitialize (🔴 NUCLEAR)
  layer --layers X    Clear specific layers only (⚠️  SELECTIVE)

Examples:
  /memory-reset status
  /memory-reset soft
  /memory-reset hard --confirm
  /memory-reset layer --layers graph patterns

⚠️  WARNING: soft/hard/layer operations create automatic backups
             but will delete data. Always check status first!

Quick commands:
  /memory-status      Alias for: /memory-reset status
  /memory-soft-reset  Alias for: /memory-reset soft
`);
    rl.close();
    return;
  }

  const command = args[0];

  // STATUS command (safe, no warnings)
  if (command === 'status') {
    try {
      const { stdout } = await execFileAsync('python', [resetScript, 'status']);
      console.log(stdout);
    } catch (error) {
      console.error('❌ Error:', error.message);
    }
    rl.close();
    return;
  }

  // SOFT RESET command (destructive, show warning)
  if (command === 'soft') {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                    ⚠️  WARNING ⚠️                        ║
╚══════════════════════════════════════════════════════════╝

SOFT RESET will:
  ✓ Delete ALL memories from current profile
  ✓ Clear graph data (nodes, edges, clusters)
  ✓ Clear learned identity patterns
  ✓ Clear tree structure
  ✓ Create automatic backup before deletion
  ✓ Keep V2 schema structure intact

What it WON'T delete:
  ✓ Python code (graph_engine.py, etc.)
  ✓ Other profiles (if using profile system)
  ✓ Documentation files

Backup location: ~/.claude-memory/backups/pre-reset-[timestamp].db
`);

    const answer = await question('Proceed with soft reset? (yes/no): ');

    if (answer.toLowerCase() === 'yes') {
      try {
        const { stdout } = await execFileAsync('python', [resetScript, 'soft']);
        console.log(stdout);
      } catch (error) {
        console.error('❌ Error:', error.message);
      }
    } else {
      console.log('\nCancelled. No changes made.');
    }

    rl.close();
    return;
  }

  // HARD RESET command (nuclear, extra warnings)
  if (command === 'hard') {
    if (!args.includes('--confirm')) {
      console.log(`
❌ ERROR: Hard reset requires --confirm flag

HARD RESET is DESTRUCTIVE and will:
  🔴 Delete the ENTIRE database file
  🔴 Remove ALL memories permanently
  🔴 Remove ALL graph data permanently
  🔴 Remove ALL learned patterns permanently

This is the NUCLEAR option. Use only if:
  - You want to completely start over
  - You're sure you don't need any current data
  - You've manually backed up anything important

A backup will be created automatically, but this is irreversible
within the system.

To proceed, use:
  /memory-reset hard --confirm
`);
      rl.close();
      return;
    }

    console.log(`
╔══════════════════════════════════════════════════════════╗
║                  🔴 DANGER ZONE 🔴                       ║
╚══════════════════════════════════════════════════════════╝

HARD RESET will:
  🔴 DELETE the entire database file (memory.db)
  🔴 DESTROY all memories (cannot undo within system)
  🔴 ERASE all graph relationships
  🔴 REMOVE all learned patterns
  🔴 Reinitialize fresh V2 schema

What it KEEPS:
  ✓ Python code
  ✓ Virtual environment
  ✓ Documentation
  ✓ Backups (one will be created now)

This is the MOST DESTRUCTIVE option.

Backup location: ~/.claude-memory/backups/pre-reset-[timestamp].db
`);

    const answer = await question('Type "DELETE EVERYTHING" to confirm: ');

    if (answer === 'DELETE EVERYTHING') {
      try {
        const { stdout } = await execFileAsync('python', [
          resetScript,
          'hard',
          '--confirm'
        ]);
        console.log(stdout);
      } catch (error) {
        console.error('❌ Error:', error.message);
      }
    } else {
      console.log('\nCancelled. No changes made.');
      console.log('(You must type exactly "DELETE EVERYTHING" to confirm)');
    }

    rl.close();
    return;
  }

  // LAYER RESET command (selective)
  if (command === 'layer') {
    const layersIndex = args.indexOf('--layers');

    if (layersIndex === -1 || layersIndex === args.length - 1) {
      console.log(`
❌ ERROR: --layers flag required with layer names

Usage: /memory-reset layer --layers <layer1> [layer2] [layer3]

Available layers:
  graph     - Clear graph nodes, edges, clusters (keeps memories)
  patterns  - Clear learned identity patterns (keeps memories)
  tree      - Clear hierarchical structure (keeps memories)
  archive   - Clear compressed memory archives

Examples:
  /memory-reset layer --layers graph
  /memory-reset layer --layers graph patterns
  /memory-reset layer --layers graph patterns tree

This is SELECTIVE - only specified layers are cleared.
Memories remain intact unless you clear 'archive' layer.
`);
      rl.close();
      return;
    }

    const layers = args.slice(layersIndex + 1);

    console.log(`
╔══════════════════════════════════════════════════════════╗
║              ⚠️  SELECTIVE LAYER RESET ⚠️                ║
╚══════════════════════════════════════════════════════════╝

Will clear these layers: ${layers.join(', ')}

What this does:
  ${layers.includes('graph') ? '✓ Clears graph nodes, edges, clusters' : ''}
  ${layers.includes('patterns') ? '✓ Clears learned identity patterns' : ''}
  ${layers.includes('tree') ? '✓ Clears hierarchical tree structure' : ''}
  ${layers.includes('archive') ? '✓ Clears compressed memory archives' : ''}

What it KEEPS:
  ✓ Raw memories (unless clearing archive)
  ✓ Unaffected layers
  ✓ All backups

You can rebuild cleared layers:
  - Graph: python graph_engine.py build
  - Patterns: python pattern_learner.py update
  - Tree: python tree_manager.py build_tree

Backup location: ~/.claude-memory/backups/pre-reset-[timestamp].db
`);

    const answer = await question('Proceed with layer reset? (yes/no): ');

    if (answer.toLowerCase() === 'yes') {
      try {
        const { stdout } = await execFileAsync('python', [
          resetScript,
          'layer',
          '--layers',
          ...layers
        ]);
        console.log(stdout);
      } catch (error) {
        console.error('❌ Error:', error.message);
      }
    } else {
      console.log('\nCancelled. No changes made.');
    }

    rl.close();
    return;
  }

  // Unknown command
  console.log(`
❌ Unknown command: ${command}

Valid commands: status, soft, hard, layer

Use: /memory-reset --help for more information
`);
  rl.close();
}

memoryResetSkill();
