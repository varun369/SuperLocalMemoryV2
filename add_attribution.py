#!/usr/bin/env python3
"""
Attribution Header Injection Script
Adds copyright and attribution headers to all source files

Created by: Varun Pratap Bhardwaj
License: MIT
"""

import os
import glob

# Attribution header for Python files
PYTHON_HEADER = '''#!/usr/bin/env python3
"""
SuperLocalMemory V2 - {filename}

Copyright (c) 2026 Varun Pratap Bhardwaj
Solution Architect & Original Creator

Licensed under MIT License (see LICENSE file)
Repository: https://github.com/varun369/SuperLocalMemoryV2

ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
"""

'''

# Attribution footer for Markdown files
MARKDOWN_FOOTER = '''
---

**Created by:** [Varun Pratap Bhardwaj](https://github.com/varun369) (Solution Architect)
**Project:** SuperLocalMemory V2
**License:** MIT with attribution requirements (see [ATTRIBUTION.md](../../ATTRIBUTION.md))
**Repository:** https://github.com/varun369/SuperLocalMemoryV2

*Open source doesn't mean removing credit. Attribution must be preserved per MIT License terms.*
'''

def add_python_header(filepath):
    """Add attribution header to Python file if not present"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if already has attribution
    if 'Varun Pratap Bhardwaj' in content[:500]:
        print(f"✓ {filepath} - Already has attribution")
        return False

    filename = os.path.basename(filepath)
    header = PYTHON_HEADER.format(filename=filename)

    # Remove shebang if exists
    if content.startswith('#!/usr/bin/env python3'):
        content = content.split('\n', 1)[1].lstrip()

    # Remove existing docstring if present
    if content.startswith('"""') or content.startswith("'''"):
        # Find end of docstring
        delimiter = '"""' if content.startswith('"""') else "'''"
        try:
            end_idx = content.index(delimiter, 3) + 3
            content = content[end_idx:].lstrip()
        except ValueError:
            pass

    new_content = header + content

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ {filepath} - Attribution added")
    return True

def add_markdown_footer(filepath):
    """Add attribution footer to Markdown file if not present"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if already has attribution
    if 'Varun Pratap Bhardwaj' in content:
        print(f"✓ {filepath} - Already has attribution")
        return False

    # Remove old footer if present
    if '**Created by:** SuperLocalMemory V2' in content:
        # Find and remove old footer
        lines = content.split('\n')
        # Find the ---  divider before footer
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '---' and i > 0:
                # Check if this is the footer divider
                if '**Created by:**' in '\n'.join(lines[i:]):
                    content = '\n'.join(lines[:i]).rstrip()
                    break

    new_content = content.rstrip() + '\n' + MARKDOWN_FOOTER

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ {filepath} - Attribution added")
    return True

def main():
    """Add attribution to all files"""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)

    print("🔧 Adding attribution headers to SuperLocalMemory V2...")
    print(f"📁 Repository: {repo_root}\n")

    modified_count = 0

    # Process Python files
    print("📝 Processing Python files...")
    python_files = glob.glob('**/*.py', recursive=True)
    for filepath in python_files:
        # Skip venv, .git, etc.
        if any(skip in filepath for skip in ['.git', 'venv', '__pycache__', 'node_modules']):
            continue
        if add_python_header(filepath):
            modified_count += 1

    print()

    # Process SKILL.md files
    print("📝 Processing SKILL.md files...")
    skill_files = glob.glob('skills/*/SKILL.md', recursive=True)
    for filepath in skill_files:
        if add_markdown_footer(filepath):
            modified_count += 1

    print()

    print(f"✅ Attribution injection complete!")
    print(f"📊 Files modified: {modified_count}")
    print()
    print("⚠️  IMPORTANT: These headers are REQUIRED by MIT License.")
    print("   Removing them violates the license terms.")

if __name__ == '__main__':
    main()
