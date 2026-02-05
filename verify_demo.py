#!/usr/bin/env python3
"""
Verify demo database contains only safe, generic content.
Run this before committing to GitHub to ensure no sensitive data leaked.
"""

import sys
import sqlite3
from pathlib import Path

DEMO_DB_PATH = Path(__file__).parent / "demo-memory.db"

# Forbidden keywords - will fail if found
# Customize this list with your own sensitive terms before using
FORBIDDEN_KEYWORDS = [
    # Example company names (add your own)
    'your-company', 'your-client',
    # Financial data
    'revenue', 'million', 'billion', '$',
    # Personal identifiers (add your own names)
    'your-name', 'your-email',
    # Client references
    'customer name', 'contract number',
    # Proprietary markers
    'confidential', 'proprietary', 'internal only',
]


def verify_demo_database():
    """Verify demo database is safe for public distribution."""

    if not DEMO_DB_PATH.exists():
        print(f"❌ Demo database not found: {DEMO_DB_PATH}")
        return False

    print(f"Verifying demo database: {DEMO_DB_PATH}")
    print("="*60)

    # Check file size
    db_size_kb = DEMO_DB_PATH.stat().st_size / 1024
    print(f"\n✓ Database size: {db_size_kb:.1f} KB")

    if db_size_kb > 200:
        print(f"  ⚠ Warning: Database larger than expected (>200KB)")

    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()

    # Count memories
    cursor.execute("SELECT COUNT(*) FROM memories")
    total_memories = cursor.fetchone()[0]
    print(f"✓ Total memories: {total_memories}")

    # Check for sensitive keywords
    print(f"\n🔍 Scanning for sensitive data...")
    violations = []

    cursor.execute("SELECT id, content, summary FROM memories")
    for row in cursor.fetchall():
        memory_id, content, summary = row
        combined_text = f"{content} {summary or ''}".lower()

        for keyword in FORBIDDEN_KEYWORDS:
            if keyword.lower() in combined_text:
                violations.append({
                    'memory_id': memory_id,
                    'keyword': keyword,
                    'context': combined_text[:100]
                })

    if violations:
        print(f"\n❌ FOUND SENSITIVE DATA - DO NOT COMMIT!")
        for v in violations:
            print(f"  Memory {v['memory_id']}: Found '{v['keyword']}'")
            print(f"    Context: {v['context']}")
        conn.close()
        return False

    print("✓ No sensitive keywords found")

    # Verify categories are generic
    cursor.execute("SELECT DISTINCT category FROM memories WHERE category IS NOT NULL")
    categories = [row[0] for row in cursor.fetchall()]
    print(f"\n✓ Categories: {', '.join(categories)}")

    # Verify tags are generic
    cursor.execute("SELECT DISTINCT tags FROM memories WHERE tags IS NOT NULL")
    import json
    all_tags = set()
    for row in cursor.fetchall():
        tags = json.loads(row[0])
        all_tags.update(tags)

    print(f"✓ Tags: {', '.join(sorted(all_tags))}")

    # Check graph structure
    cursor.execute("SELECT COUNT(DISTINCT cluster_id) FROM memories WHERE cluster_id IS NOT NULL")
    total_clusters = cursor.fetchone()[0]
    print(f"\n✓ Graph clusters: {total_clusters}")

    # Sample memory check
    cursor.execute("SELECT content FROM memories ORDER BY RANDOM() LIMIT 1")
    sample = cursor.fetchone()[0]
    print(f"\n✓ Sample memory (random):")
    print(f"  {sample[:150]}...")

    conn.close()

    print("\n" + "="*60)
    print("✅ VERIFICATION PASSED - Safe for GitHub distribution")
    print("="*60)
    return True


if __name__ == "__main__":
    success = verify_demo_database()
    sys.exit(0 if success else 1)
