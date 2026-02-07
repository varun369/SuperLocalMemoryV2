#!/usr/bin/env python3
"""
SuperLocalMemory V2.2.0 - Backward Compatibility Test

Tests that v2.2.0 code works with v2.1.0 databases without data loss.

Copyright (c) 2026 Varun Pratap Bhardwaj
Solution Architect & Original Creator

Licensed under MIT License (see LICENSE file)
Repository: https://github.com/varun369/SuperLocalMemoryV2

ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
"""

import sys
import os
import sqlite3
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_v210_database():
    """Test that v2.1.0 database works with v2.2.0 code"""

    print("=" * 70)
    print("SuperLocalMemory V2.2.0 - Backward Compatibility Test")
    print("=" * 70)
    print("")

    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix="slm_compat_test_")
    test_db = os.path.join(test_dir, "memory.db")

    try:
        # Step 1: Create v2.1.0-style database (minimal schema)
        print("📝 Step 1: Creating v2.1.0-style database...")
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Minimal v2.1.0 schema (only essential columns)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT,
                project_name TEXT,
                category TEXT,
                importance INTEGER DEFAULT 5
            )
        ''')

        # Add test memory
        cursor.execute('''
            INSERT INTO memories (content, tags, project_name, importance)
            VALUES (?, ?, ?, ?)
        ''', ('Test memory from v2.1.0', 'test,compatibility', 'test-project', 7))

        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"   ✅ Created v2.1.0 database with memory ID {memory_id}")
        print("")

        # Step 2: Load with v2.2.0 code
        print("📝 Step 2: Loading with v2.2.0 code...")
        os.environ['MEMORY_DB_PATH'] = test_db

        from memory_store_v2 import MemoryStoreV2

        store = MemoryStoreV2(db_path=test_db)
        print("   ✅ MemoryStoreV2 initialized successfully")
        print("")

        # Step 3: Verify existing memory
        print("📝 Step 3: Verifying existing memory...")
        memories = store.list_all(limit=10)

        assert len(memories) >= 1, "Expected at least 1 memory"
        found = False
        for mem in memories:
            if 'Test memory from v2.1.0' in mem.get('content', ''):
                found = True
                print(f"   ✅ Found original memory: {mem['content'][:50]}...")
                print(f"   ✅ Memory ID: {mem['id']}")
                print(f"   ✅ Tags: {mem.get('tags', 'N/A')}")
                print(f"   ✅ Importance: {mem.get('importance', 'N/A')}")
                break

        assert found, "Original memory not found!"
        print("")

        # Step 4: Add new memory with v2.2.0 code
        print("📝 Step 4: Adding new memory with v2.2.0...")
        new_id = store.add_memory(
            content="New memory added with v2.2.0",
            tags=["v2.2.0", "test"],
            project_name="test-project",
            importance=8
        )
        print(f"   ✅ Added new memory with ID {new_id}")
        print("")

        # Step 5: Search (test v2.2.0 search features)
        print("📝 Step 5: Testing search...")
        results = store.search("memory", limit=10)
        assert len(results) >= 2, f"Expected at least 2 results, got {len(results)}"
        print(f"   ✅ Search returned {len(results)} results")
        print("")

        # Step 6: Verify database integrity
        print("📝 Step 6: Verifying database integrity...")
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        assert result[0] == 'ok', f"Database integrity check failed: {result[0]}"
        print("   ✅ Database integrity: OK")

        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        print(f"   ✅ Total memories: {count}")

        conn.close()
        print("")

        # Success
        print("=" * 70)
        print("✅ BACKWARD COMPATIBILITY TEST PASSED")
        print("=" * 70)
        print("")
        print("Summary:")
        print(f"  • v2.1.0 database loaded successfully")
        print(f"  • Existing data preserved (0 data loss)")
        print(f"  • New features work with old database")
        print(f"  • Database integrity maintained")
        print("")
        return True

    except Exception as e:
        print("")
        print("=" * 70)
        print("❌ BACKWARD COMPATIBILITY TEST FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        try:
            shutil.rmtree(test_dir)
        except:
            pass

if __name__ == '__main__':
    success = test_v210_database()
    sys.exit(0 if success else 1)
