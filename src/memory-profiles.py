#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Intelligent Local Memory System
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
SuperLocalMemory V2 - Profile Management System

Allows users to maintain separate memory databases for different contexts/personalities:
- Work profile: Professional coding memories
- Personal profile: Personal projects and learning
- Client-specific profiles: Different clients get isolated memories
- Experimentation profile: Testing and experiments

Each profile is completely isolated with its own:
- Database (memory.db)
- Graph data
- Learned patterns
- Compressed archives
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse

MEMORY_DIR = Path.home() / ".claude-memory"
PROFILES_DIR = MEMORY_DIR / "profiles"
CURRENT_PROFILE_FILE = MEMORY_DIR / ".current_profile"
CONFIG_FILE = MEMORY_DIR / "profiles.json"


class ProfileManager:
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.profiles_dir = PROFILES_DIR
        self.current_profile_file = CURRENT_PROFILE_FILE
        self.config_file = CONFIG_FILE

        # Ensure profiles directory exists
        self.profiles_dir.mkdir(exist_ok=True)

        # Load or create config
        self.config = self._load_config()

    def _load_config(self):
        """Load profiles configuration."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Default config
            config = {
                'profiles': {
                    'default': {
                        'name': 'default',
                        'description': 'Default memory profile',
                        'created_at': datetime.now().isoformat(),
                        'last_used': datetime.now().isoformat()
                    }
                },
                'active_profile': 'default'
            }
            self._save_config(config)
            return config

    def _save_config(self, config=None):
        """Save profiles configuration."""
        if config is None:
            config = self.config

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _get_profile_path(self, profile_name):
        """Get directory path for a profile with security validation."""
        import re

        # SECURITY: Validate profile name to prevent path traversal
        if not profile_name:
            raise ValueError("Profile name cannot be empty")

        if not re.match(r'^[a-zA-Z0-9_-]+$', profile_name):
            raise ValueError("Invalid profile name. Use only letters, numbers, dash, underscore.")

        if len(profile_name) > 50:
            raise ValueError("Profile name too long (max 50 characters)")

        if profile_name in ['.', '..', 'default']:
            raise ValueError(f"Reserved profile name: {profile_name}")

        path = (self.profiles_dir / profile_name).resolve()

        # SECURITY: Ensure path stays within profiles directory
        if not str(path).startswith(str(self.profiles_dir.resolve())):
            raise ValueError("Invalid profile path - path traversal detected")

        return path

    def _get_main_files(self):
        """Get list of main memory system files to copy."""
        return [
            'memory.db',
            'config.json',
            'vectors'
        ]

    def list_profiles(self):
        """List all available profiles."""
        print("\n" + "="*60)
        print("AVAILABLE MEMORY PROFILES")
        print("="*60)

        active = self.config.get('active_profile', 'default')

        if not self.config['profiles']:
            print("\n  No profiles found. Create one with: create <name>")
            return

        print(f"\n{'Profile':20s} {'Description':35s} {'Status':10s}")
        print("-" * 70)

        for name, info in self.config['profiles'].items():
            status = "ACTIVE" if name == active else ""
            desc = info.get('description', 'No description')[:35]
            marker = "→ " if name == active else "  "
            print(f"{marker}{name:18s} {desc:35s} {status:10s}")

        print(f"\nTotal profiles: {len(self.config['profiles'])}")
        print(f"Active profile: {active}")

    def create_profile(self, name, description=None, from_current=False):
        """Create a new profile."""
        print(f"\nCreating profile: {name}")

        # Check if profile exists
        if name in self.config['profiles']:
            print(f"❌ Error: Profile '{name}' already exists")
            return False

        # Create profile directory
        profile_path = self._get_profile_path(name)
        profile_path.mkdir(exist_ok=True)

        if from_current:
            # Copy current memory system to new profile
            print("  Copying current memory system...")

            for file in self._get_main_files():
                src = self.memory_dir / file
                dst = profile_path / file

                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    print(f"    ✓ Copied {file}")
        else:
            # Initialize empty profile with V2 schema
            print("  Initializing empty profile with V2 schema...")
            self._initialize_empty_profile(profile_path)

        # Add to config
        self.config['profiles'][name] = {
            'name': name,
            'description': description or f"Memory profile: {name}",
            'created_at': datetime.now().isoformat(),
            'last_used': None,
            'created_from': 'current' if from_current else 'empty'
        }
        self._save_config()

        print(f"✅ Profile '{name}' created successfully")
        return True

    def _initialize_empty_profile(self, profile_path):
        """Initialize empty profile with V2 schema."""
        # Import the migration script's initialization logic
        import sqlite3

        db_path = profile_path / "memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create basic V2 schema (simplified version)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                summary TEXT,
                project_path TEXT,
                project_name TEXT,
                tags TEXT,
                category TEXT,
                memory_type TEXT DEFAULT 'session',
                importance INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                content_hash TEXT UNIQUE,
                parent_id INTEGER,
                tree_path TEXT,
                depth INTEGER DEFAULT 0,
                cluster_id INTEGER,
                tier INTEGER DEFAULT 1
            )
        ''')

        # Add other essential tables
        tables = [
            'memory_tree', 'graph_nodes', 'graph_edges',
            'graph_clusters', 'identity_patterns',
            'pattern_examples', 'memory_archive'
        ]

        for table in tables:
            cursor.execute(f'CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY)')

        conn.commit()
        conn.close()

        # Create basic config
        config = {
            "version": "2.0.0",
            "embedding_model": "local-tfidf",
            "max_context_tokens": 4000
        }

        with open(profile_path / "config.json", 'w') as f:
            json.dump(config, f, indent=2)

        print("    ✓ Initialized V2 schema")

    def switch_profile(self, name):
        """Switch to a different profile."""
        if name not in self.config['profiles']:
            print(f"❌ Error: Profile '{name}' not found")
            print(f"   Available: {', '.join(self.config['profiles'].keys())}")
            return False

        current = self.config.get('active_profile')

        if current == name:
            print(f"Already using profile: {name}")
            return True

        print(f"\nSwitching from '{current}' to '{name}'...")

        # Save current profile
        if current and current in self.config['profiles']:
            self._save_current_to_profile(current)

        # Load new profile
        self._load_profile_to_main(name)

        # Update config
        self.config['active_profile'] = name
        self.config['profiles'][name]['last_used'] = datetime.now().isoformat()
        self._save_config()

        print(f"✅ Switched to profile: {name}")
        print(f"\n⚠️  IMPORTANT: Restart Claude CLI to use new profile!")
        return True

    def _save_current_to_profile(self, profile_name):
        """Save current main memory system to profile."""
        print(f"  Saving current state to profile '{profile_name}'...")

        profile_path = self._get_profile_path(profile_name)
        profile_path.mkdir(exist_ok=True)

        for file in self._get_main_files():
            src = self.memory_dir / file
            dst = profile_path / file

            if src.exists():
                # Remove old version
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()

                # Copy current
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        print(f"    ✓ Saved to {profile_path}")

    def _load_profile_to_main(self, profile_name):
        """Load profile to main memory system."""
        print(f"  Loading profile '{profile_name}'...")

        profile_path = self._get_profile_path(profile_name)

        if not profile_path.exists():
            print(f"    ⚠️  Profile directory not found, will create on switch")
            return

        for file in self._get_main_files():
            src = profile_path / file
            dst = self.memory_dir / file

            if src.exists():
                # Remove old version
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()

                # Copy profile
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        print(f"    ✓ Loaded from {profile_path}")

    def delete_profile(self, name, force=False):
        """Delete a profile."""
        if name not in self.config['profiles']:
            print(f"❌ Error: Profile '{name}' not found")
            return False

        if name == 'default':
            print(f"❌ Error: Cannot delete 'default' profile")
            return False

        if self.config.get('active_profile') == name:
            print(f"❌ Error: Cannot delete active profile")
            print(f"   Switch to another profile first")
            return False

        if not force:
            print(f"\n⚠️  WARNING: This will permanently delete profile '{name}'")
            response = input(f"Type profile name '{name}' to confirm: ")

            if response != name:
                print("Cancelled.")
                return False

        # Delete profile directory
        profile_path = self._get_profile_path(name)
        if profile_path.exists():
            shutil.rmtree(profile_path)
            print(f"  ✓ Deleted profile directory")

        # Remove from config
        del self.config['profiles'][name]
        self._save_config()

        print(f"✅ Profile '{name}' deleted")
        return True

    def show_current(self):
        """Show current active profile."""
        active = self.config.get('active_profile', 'default')

        if active in self.config['profiles']:
            info = self.config['profiles'][active]

            print("\n" + "="*60)
            print("CURRENT ACTIVE PROFILE")
            print("="*60)
            print(f"\nProfile: {active}")
            print(f"Description: {info.get('description', 'N/A')}")
            print(f"Created: {info.get('created_at', 'N/A')}")
            print(f"Last used: {info.get('last_used', 'N/A')}")

            # Show stats if database exists
            db_path = self.memory_dir / "memory.db"
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                cursor.execute('SELECT COUNT(*) FROM memories')
                memory_count = cursor.fetchone()[0]

                print(f"\nMemories: {memory_count}")
                conn.close()
        else:
            print(f"⚠️  Current profile '{active}' not found in config")

    def rename_profile(self, old_name, new_name):
        """Rename a profile."""
        if old_name not in self.config['profiles']:
            print(f"❌ Error: Profile '{old_name}' not found")
            return False

        if new_name in self.config['profiles']:
            print(f"❌ Error: Profile '{new_name}' already exists")
            return False

        if old_name == 'default':
            print(f"❌ Error: Cannot rename 'default' profile")
            return False

        # Rename directory
        old_path = self._get_profile_path(old_name)
        new_path = self._get_profile_path(new_name)

        if old_path.exists():
            old_path.rename(new_path)

        # Update config
        self.config['profiles'][new_name] = self.config['profiles'][old_name]
        self.config['profiles'][new_name]['name'] = new_name
        del self.config['profiles'][old_name]

        if self.config.get('active_profile') == old_name:
            self.config['active_profile'] = new_name

        self._save_config()

        print(f"✅ Profile renamed: '{old_name}' → '{new_name}'")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='SuperLocalMemory V2 - Profile Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # List all profiles
  python memory-profiles.py list

  # Show current profile
  python memory-profiles.py current

  # Create new empty profile
  python memory-profiles.py create work --description "Work projects"

  # Create profile from current memories
  python memory-profiles.py create personal --from-current

  # Switch to different profile
  python memory-profiles.py switch work

  # Delete a profile
  python memory-profiles.py delete old-profile

  # Rename profile
  python memory-profiles.py rename old-name new-name
        '''
    )

    parser.add_argument('command',
                       choices=['list', 'current', 'create', 'switch', 'delete', 'rename'],
                       help='Profile command')
    parser.add_argument('name', nargs='?', help='Profile name')
    parser.add_argument('name2', nargs='?', help='Second name (for rename)')
    parser.add_argument('--description', help='Profile description')
    parser.add_argument('--from-current', action='store_true',
                       help='Create from current memory system')
    parser.add_argument('--force', action='store_true',
                       help='Force operation without confirmation')

    args = parser.parse_args()

    manager = ProfileManager()

    if args.command == 'list':
        manager.list_profiles()

    elif args.command == 'current':
        manager.show_current()

    elif args.command == 'create':
        if not args.name:
            print("❌ Error: Profile name required")
            print("   Usage: python memory-profiles.py create <name>")
            sys.exit(1)

        manager.create_profile(args.name, args.description, args.from_current)

    elif args.command == 'switch':
        if not args.name:
            print("❌ Error: Profile name required")
            sys.exit(1)

        manager.switch_profile(args.name)

    elif args.command == 'delete':
        if not args.name:
            print("❌ Error: Profile name required")
            sys.exit(1)

        manager.delete_profile(args.name, args.force)

    elif args.command == 'rename':
        if not args.name or not args.name2:
            print("❌ Error: Both old and new names required")
            print("   Usage: python memory-profiles.py rename <old> <new>")
            sys.exit(1)

        manager.rename_profile(args.name, args.name2)


if __name__ == '__main__':
    main()
