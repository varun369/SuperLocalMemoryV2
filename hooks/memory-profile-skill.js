#!/usr/bin/env node
/**
 * Memory Profile CLI Skill
 * Provides memory-profile commands for managing multiple memory contexts
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

async function memoryProfileSkill() {
  const profileScript = path.join(process.env.HOME, '.claude-memory', 'memory-profiles.py');
  const args = process.argv.slice(2); // Get command line arguments

  // Show help if no args
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     SuperLocalMemory V2 - Profile Management            ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Profiles let you maintain separate memory databases for different contexts:
  • Work vs Personal projects
  • Different clients or teams
  • Different AI personalities
  • Experimentation vs Production

Each profile has isolated: memories, graph, patterns, archives

Usage: memory-profile <command> [options]

Commands:
  list                List all profiles and show active one
  current             Show current active profile
  create <name>       Create a new empty profile
  switch <name>       Switch to a different profile (requires restart)
  delete <name>       Delete a profile (with confirmation)

Examples:
  memory-profile list
  memory-profile current
  memory-profile create work
  memory-profile switch work
  memory-profile delete old-project

Notes:
  • Default profile is always available
  • Switching profiles requires restarting Claude CLI
  • Deleting a profile is permanent (but creates backup)
`);
    rl.close();
    return;
  }

  const command = args[0];

  // LIST command
  if (command === 'list') {
    try {
      const { stdout } = await execFileAsync('python', [profileScript, 'list']);
      console.log(stdout);
    } catch (error) {
      console.error('❌ Error:', error.message);
    }
    rl.close();
    return;
  }

  // CURRENT command
  if (command === 'current') {
    try {
      const { stdout } = await execFileAsync('python', [profileScript, 'current']);
      console.log(stdout);
    } catch (error) {
      console.error('❌ Error:', error.message);
    }
    rl.close();
    return;
  }

  // CREATE command
  if (command === 'create') {
    if (args.length < 2) {
      console.log(`
❌ ERROR: Profile name required

Usage: memory-profile create <name> [options]

Options:
  --description "text"    Profile description
  --from-current          Copy current profile's data to new profile

Examples:
  memory-profile create work
  memory-profile create work --description "Work projects"
  memory-profile create personal --from-current
`);
      rl.close();
      return;
    }

    const profileName = args[1];
    const pythonArgs = ['create', profileName];

    // Check for --description flag
    const descIndex = args.indexOf('--description');
    if (descIndex !== -1 && descIndex + 1 < args.length) {
      pythonArgs.push('--description', args[descIndex + 1]);
    }

    // Check for --from-current flag
    if (args.includes('--from-current')) {
      pythonArgs.push('--from-current');
    }

    try {
      const { stdout } = await execFileAsync('python', [profileScript, ...pythonArgs]);
      console.log(stdout);
    } catch (error) {
      console.error('❌ Error:', error.message);
      if (error.stdout) console.log(error.stdout);
    }
    rl.close();
    return;
  }

  // SWITCH command
  if (command === 'switch') {
    if (args.length < 2) {
      console.log(`
❌ ERROR: Profile name required

Usage: memory-profile switch <name>

Example:
  memory-profile switch work

After switching, restart Claude CLI for changes to take effect.
`);
      rl.close();
      return;
    }

    const profileName = args[1];

    console.log(`
╔══════════════════════════════════════════════════════════╗
║              Profile Switch Confirmation                 ║
╚══════════════════════════════════════════════════════════╝

This will:
  ✓ Save current profile state
  ✓ Load profile "${profileName}"
  ✓ Update active profile marker

After switching, you MUST restart Claude CLI for the new profile
to take effect.

Current memories will be preserved in the old profile.
`);

    const answer = await question('Proceed with profile switch? (yes/no): ');

    if (answer.toLowerCase() === 'yes') {
      try {
        const { stdout } = await execFileAsync('python', [
          profileScript,
          'switch',
          profileName
        ]);
        console.log(stdout);
        console.log(`
⚠️  IMPORTANT: Restart Claude CLI now for profile switch to complete.

The new profile will not be active until you restart.
`);
      } catch (error) {
        console.error('❌ Error:', error.message);
        if (error.stdout) console.log(error.stdout);
      }
    } else {
      console.log('\nCancelled. No changes made.');
    }

    rl.close();
    return;
  }

  // DELETE command
  if (command === 'delete') {
    if (args.length < 2) {
      console.log(`
❌ ERROR: Profile name required

Usage: memory-profile delete <name>

Example:
  memory-profile delete old-project

Cannot delete:
  • The "default" profile
  • The currently active profile
`);
      rl.close();
      return;
    }

    const profileName = args[1];

    // Prevent deleting default
    if (profileName === 'default') {
      console.log(`
❌ ERROR: Cannot delete the default profile

The default profile is protected and cannot be deleted.
`);
      rl.close();
      return;
    }

    console.log(`
╔══════════════════════════════════════════════════════════╗
║              ⚠️  DELETE PROFILE WARNING ⚠️               ║
╚══════════════════════════════════════════════════════════╝

This will PERMANENTLY delete profile: "${profileName}"

What will be deleted:
  🔴 All memories in this profile
  🔴 Graph data (nodes, edges, clusters)
  🔴 Learned patterns
  🔴 Compressed archives

A backup will be created before deletion.

`);

    const answer = await question(`Type the profile name "${profileName}" to confirm: `);

    if (answer === profileName) {
      try {
        const { stdout } = await execFileAsync('python', [
          profileScript,
          'delete',
          profileName
        ]);
        console.log(stdout);
      } catch (error) {
        console.error('❌ Error:', error.message);
        if (error.stdout) console.log(error.stdout);
      }
    } else {
      console.log('\nCancelled. No changes made.');
      console.log(`(You must type exactly "${profileName}" to confirm)`);
    }

    rl.close();
    return;
  }

  // Unknown command
  console.log(`
❌ Unknown command: ${command}

Valid commands: list, current, create, switch, delete

Use: memory-profile --help for more information
`);
  rl.close();
}

memoryProfileSkill();
