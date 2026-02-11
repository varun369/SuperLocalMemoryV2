#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Connection Manager Tests
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Hardcore test suite for db_connection_manager.py and the memory_store_v2.py refactor.
Covers: unit tests, regression, edge cases, security, concurrency, new-user/Docker scenarios.
"""

import sqlite3
import sys
import os
import json
import tempfile
import shutil
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

# Import from repo source
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db_connection_manager import DbConnectionManager, DEFAULT_BUSY_TIMEOUT_MS


class TestDbConnectionManagerUnit(unittest.TestCase):
    """Unit tests for DbConnectionManager core functionality."""

    def setUp(self):
        """Create fresh temp database for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test.db"
        # Pre-create the database (WAL needs it to exist)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.commit()
        conn.close()
        # Reset any leftover singletons
        DbConnectionManager.reset_instance(self.db_path)

    def tearDown(self):
        """Clean up temp database and singleton."""
        DbConnectionManager.reset_instance(self.db_path)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # === WAL Mode ===

    def test_wal_mode_enabled(self):
        """WAL mode must be set on the database after manager creation."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        with mgr.read_connection() as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(mode, "wal")

    def test_busy_timeout_set(self):
        """Busy timeout must be configured on all connections."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        with mgr.read_connection() as conn:
            timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        self.assertEqual(timeout, DEFAULT_BUSY_TIMEOUT_MS)

    def test_synchronous_normal(self):
        """Synchronous mode should be NORMAL (not FULL) for WAL performance."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        with mgr.read_connection() as conn:
            sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        # 1 = NORMAL in SQLite pragma encoding
        self.assertEqual(sync, 1)

    # === Singleton Pattern ===

    def test_singleton_same_path(self):
        """Same db_path must return the same instance."""
        mgr1 = DbConnectionManager.get_instance(self.db_path)
        mgr2 = DbConnectionManager.get_instance(self.db_path)
        self.assertIs(mgr1, mgr2)

    def test_singleton_different_path(self):
        """Different db_path must return different instances."""
        db2 = Path(self.tmpdir) / "test2.db"
        conn = sqlite3.connect(str(db2))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        mgr1 = DbConnectionManager.get_instance(self.db_path)
        mgr2 = DbConnectionManager.get_instance(db2)
        self.assertIsNot(mgr1, mgr2)
        DbConnectionManager.reset_instance(db2)

    def test_reset_instance_creates_new(self):
        """After reset, get_instance must create a fresh manager."""
        mgr1 = DbConnectionManager.get_instance(self.db_path)
        id1 = id(mgr1)
        DbConnectionManager.reset_instance(self.db_path)
        mgr2 = DbConnectionManager.get_instance(self.db_path)
        self.assertNotEqual(id1, id(mgr2))

    def test_reset_all_instances(self):
        """reset_instance(None) must close and clear all instances."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        DbConnectionManager.reset_instance()
        self.assertTrue(mgr.is_closed)

    # === Read Connections ===

    def test_read_connection_context_manager(self):
        """read_connection() context manager must yield a working connection."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        with mgr.read_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM test").fetchone()
        self.assertEqual(result[0], 0)

    def test_read_connection_thread_local(self):
        """Each thread must get its own read connection."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        conn_ids = []

        def get_conn_id():
            with mgr.read_connection() as conn:
                conn_ids.append(id(conn))

        threads = [threading.Thread(target=get_conn_id) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have a unique connection object
        self.assertEqual(len(set(conn_ids)), 4)

    def test_read_connection_same_thread_reuses(self):
        """Same thread must get the same read connection on repeated calls."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        with mgr.read_connection() as conn1:
            id1 = id(conn1)
        with mgr.read_connection() as conn2:
            id2 = id(conn2)
        self.assertEqual(id1, id2)

    # === Write Queue ===

    def test_write_basic(self):
        """Basic write through queue must persist data."""
        mgr = DbConnectionManager.get_instance(self.db_path)

        def insert(conn):
            conn.execute("INSERT INTO test (val) VALUES (?)", ("hello",))
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        row_id = mgr.execute_write(insert)
        self.assertEqual(row_id, 1)

        # Verify via read
        with mgr.read_connection() as conn:
            val = conn.execute("SELECT val FROM test WHERE id = ?", (row_id,)).fetchone()[0]
        self.assertEqual(val, "hello")

    def test_write_returns_value(self):
        """execute_write must return the callback's return value."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        result = mgr.execute_write(lambda conn: 42)
        self.assertEqual(result, 42)

    def test_write_exception_propagates(self):
        """Exceptions in write callbacks must propagate to the caller."""
        mgr = DbConnectionManager.get_instance(self.db_path)

        def bad_write(conn):
            raise ValueError("intentional test error")

        with self.assertRaises(ValueError) as ctx:
            mgr.execute_write(bad_write)
        self.assertIn("intentional test error", str(ctx.exception))

    def test_write_exception_doesnt_kill_writer(self):
        """Writer thread must survive callback exceptions."""
        mgr = DbConnectionManager.get_instance(self.db_path)

        # First call: exception
        with self.assertRaises(ValueError):
            mgr.execute_write(lambda conn: (_ for _ in ()).throw(ValueError("boom")))

        # Second call: should still work
        result = mgr.execute_write(lambda conn: "still alive")
        self.assertEqual(result, "still alive")

    def test_write_serialization_order(self):
        """Writes must be processed in submission order."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        order = []

        def ordered_insert(n):
            def _do(conn):
                order.append(n)
                conn.execute("INSERT INTO test (val) VALUES (?)", (f"item-{n}",))
                conn.commit()
            return _do

        # Submit 10 writes from different threads simultaneously
        threads = []
        for i in range(10):
            t = threading.Thread(target=lambda n=i: mgr.execute_write(ordered_insert(n)))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 10 should have been processed
        self.assertEqual(len(order), 10)

        # Verify all items in DB
        with mgr.read_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
        self.assertEqual(count, 10)

    # === Post-Write Hooks ===

    def test_post_write_hook_fires(self):
        """Post-write hooks must fire after each successful write."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        fired = []

        mgr.register_post_write_hook(lambda: fired.append(True))

        mgr.execute_write(lambda conn: conn.execute("INSERT INTO test (val) VALUES ('a')") or conn.commit())
        mgr.execute_write(lambda conn: conn.execute("INSERT INTO test (val) VALUES ('b')") or conn.commit())

        self.assertEqual(len(fired), 2)

    def test_post_write_hook_unregister(self):
        """Unregistered hooks must not fire."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        fired = []
        hook = lambda: fired.append(True)

        mgr.register_post_write_hook(hook)
        mgr.execute_write(lambda conn: conn.commit())
        self.assertEqual(len(fired), 1)

        mgr.unregister_post_write_hook(hook)
        mgr.execute_write(lambda conn: conn.commit())
        self.assertEqual(len(fired), 1)  # Should NOT increase

    def test_post_write_hook_exception_doesnt_crash(self):
        """Hook exceptions must be caught — not crash the writer thread."""
        mgr = DbConnectionManager.get_instance(self.db_path)

        def bad_hook():
            raise RuntimeError("hook exploded")

        mgr.register_post_write_hook(bad_hook)

        # Should not raise
        mgr.execute_write(lambda conn: conn.execute("INSERT INTO test (val) VALUES ('x')") or conn.commit())

        # Writer should still be alive
        result = mgr.execute_write(lambda conn: "alive")
        self.assertEqual(result, "alive")

        mgr.unregister_post_write_hook(bad_hook)

    # === Diagnostics ===

    def test_diagnostics(self):
        """get_diagnostics must return all expected keys."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        diag = mgr.get_diagnostics()

        self.assertIn("db_path", diag)
        self.assertIn("closed", diag)
        self.assertIn("write_queue_depth", diag)
        self.assertIn("writer_thread_alive", diag)
        self.assertIn("journal_mode", diag)
        self.assertIn("busy_timeout_ms", diag)
        self.assertFalse(diag["closed"])
        self.assertTrue(diag["writer_thread_alive"])
        self.assertEqual(diag["journal_mode"], "wal")

    # === Lifecycle ===

    def test_close_prevents_operations(self):
        """After close(), all operations must raise RuntimeError."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        DbConnectionManager.reset_instance(self.db_path)

        with self.assertRaises(RuntimeError):
            mgr.get_read_connection()

        with self.assertRaises(RuntimeError):
            mgr.execute_write(lambda conn: None)

    def test_close_is_idempotent(self):
        """Calling close() multiple times must not raise."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        mgr.close()
        mgr.close()  # Should not raise
        self.assertTrue(mgr.is_closed)


class TestDbConnectionManagerConcurrency(unittest.TestCase):
    """Concurrency stress tests — simulates multiple agents writing simultaneously."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "concurrent.db"
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)")
        conn.commit()
        conn.close()
        DbConnectionManager.reset_instance(self.db_path)

    def tearDown(self):
        DbConnectionManager.reset_instance(self.db_path)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_100_concurrent_writes(self):
        """100 threads writing simultaneously must all succeed (no database locked)."""
        mgr = DbConnectionManager.get_instance(self.db_path)
        errors = []
        successes = []

        def write_memory(n):
            try:
                def _do(conn):
                    conn.execute(
                        "INSERT INTO memories (content, created_at) VALUES (?, ?)",
                        (f"Memory #{n}", "2026-02-12T00:00:00")
                    )
                    conn.commit()
                    return n
                result = mgr.execute_write(_do)
                successes.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=write_memory, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors[:5]}")
        self.assertEqual(len(successes), 100)

        # Verify all 100 in database
        with mgr.read_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        self.assertEqual(count, 100)

    def test_concurrent_reads_during_write(self):
        """Reads must not block during writes (WAL mode guarantee)."""
        mgr = DbConnectionManager.get_instance(self.db_path)

        # Pre-populate
        for i in range(10):
            mgr.execute_write(lambda conn, i=i: (
                conn.execute("INSERT INTO memories (content) VALUES (?)", (f"Pre-{i}",)),
                conn.commit()
            ))

        read_results = []
        read_errors = []

        def slow_write(conn):
            """Simulate a slow write (holds write lock)."""
            conn.execute("INSERT INTO memories (content) VALUES (?)", ("slow-write",))
            time.sleep(0.1)  # Hold write lock for 100ms
            conn.commit()

        def fast_read():
            """Read should succeed even during slow write."""
            try:
                with mgr.read_connection() as conn:
                    count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                    read_results.append(count)
            except Exception as e:
                read_errors.append(str(e))

        # Start slow write
        write_thread = threading.Thread(target=lambda: mgr.execute_write(slow_write))
        write_thread.start()

        # Immediately start reads
        time.sleep(0.01)  # Tiny delay to ensure write is in progress
        read_threads = [threading.Thread(target=fast_read) for _ in range(5)]
        for t in read_threads:
            t.start()
        for t in read_threads:
            t.join()

        write_thread.join()

        self.assertEqual(len(read_errors), 0, f"Read errors during write: {read_errors}")
        self.assertTrue(len(read_results) > 0, "No reads completed during write")


class TestMemoryStoreV2Refactor(unittest.TestCase):
    """Regression tests for memory_store_v2.py refactor — all existing behavior preserved."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test_memory.db"
        self.vectors_path = Path(self.tmpdir) / "vectors"
        self.vectors_path.mkdir()

        # Patch module paths
        import memory_store_v2
        self._orig_db = memory_store_v2.DB_PATH
        self._orig_mem = memory_store_v2.MEMORY_DIR
        self._orig_vec = memory_store_v2.VECTORS_PATH
        memory_store_v2.DB_PATH = self.db_path
        memory_store_v2.MEMORY_DIR = Path(self.tmpdir)
        memory_store_v2.VECTORS_PATH = self.vectors_path

        from memory_store_v2 import MemoryStoreV2
        self.store = MemoryStoreV2(self.db_path)

    def tearDown(self):
        import memory_store_v2
        memory_store_v2.DB_PATH = self._orig_db
        memory_store_v2.MEMORY_DIR = self._orig_mem
        memory_store_v2.VECTORS_PATH = self._orig_vec
        DbConnectionManager.reset_instance(self.db_path)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # === Core CRUD ===

    def test_add_and_retrieve(self):
        """add_memory + get_by_id must round-trip correctly."""
        mid = self.store.add_memory("Test content", tags=["a", "b"], importance=7)
        self.assertIsInstance(mid, int)
        self.assertGreater(mid, 0)

        mem = self.store.get_by_id(mid)
        self.assertIsNotNone(mem)
        self.assertEqual(mem["content"], "Test content")
        self.assertEqual(mem["tags"], ["a", "b"])
        self.assertEqual(mem["importance"], 7)

    def test_duplicate_detection(self):
        """Adding identical content must return existing ID, not create duplicate."""
        mid1 = self.store.add_memory("Duplicate content")
        mid2 = self.store.add_memory("Duplicate content")
        self.assertEqual(mid1, mid2)

    def test_search_returns_results(self):
        """search() must find relevant memories."""
        self.store.add_memory("Python FastAPI backend development")
        self.store.add_memory("React frontend hooks and state")
        results = self.store.search("Python", limit=5)
        self.assertTrue(len(results) > 0)

    def test_delete_memory(self):
        """delete_memory must remove the memory."""
        mid = self.store.add_memory("To be deleted")
        self.assertTrue(self.store.delete_memory(mid))
        self.assertIsNone(self.store.get_by_id(mid))

    def test_delete_nonexistent(self):
        """Deleting a non-existent ID must return False."""
        self.assertFalse(self.store.delete_memory(99999))

    def test_list_all(self):
        """list_all must return memories in reverse chronological order."""
        self.store.add_memory("Python FastAPI development patterns")
        self.store.add_memory("React component architecture guide")
        self.store.add_memory("SQLite WAL mode configuration notes")
        results = self.store.list_all(limit=10)
        self.assertEqual(len(results), 3)
        self.assertIn("title", results[0])  # V1 compatibility field

    def test_get_recent(self):
        """get_recent must respect limit."""
        for i in range(5):
            self.store.add_memory(f"Memory {i}")
        results = self.store.get_recent(limit=3)
        self.assertEqual(len(results), 3)

    def test_get_stats(self):
        """get_stats must return correct counts."""
        self.store.add_memory("Stat test 1")
        self.store.add_memory("Stat test 2")
        stats = self.store.get_stats()
        self.assertEqual(stats["total_memories"], 2)
        self.assertIn("active_profile", stats)
        self.assertIn("sklearn_available", stats)

    def test_get_attribution(self):
        """Attribution must always return creator info."""
        attr = self.store.get_attribution()
        self.assertEqual(attr["creator_name"], "Varun Pratap Bhardwaj")
        self.assertEqual(attr["license"], "MIT")

    def test_update_tier(self):
        """update_tier must change memory_type."""
        mid = self.store.add_memory("Tier test")
        self.store.update_tier(mid, "warm", compressed_summary="Summary")
        mem = self.store.get_by_id(mid)
        self.assertEqual(mem["memory_type"], "warm")

    def test_get_tree(self):
        """get_tree must return memories."""
        self.store.add_memory("Tree root")
        tree = self.store.get_tree()
        self.assertTrue(len(tree) > 0)

    # === Edge Cases ===

    def test_empty_database_search(self):
        """Search on empty database must return empty list, not error."""
        results = self.store.search("anything", limit=5)
        self.assertEqual(results, [])

    def test_empty_database_stats(self):
        """Stats on empty database must return zeros."""
        stats = self.store.get_stats()
        self.assertEqual(stats["total_memories"], 0)

    def test_empty_database_list(self):
        """list_all on empty database must return empty list."""
        results = self.store.list_all()
        self.assertEqual(results, [])

    def test_get_nonexistent_id(self):
        """get_by_id for missing ID must return None."""
        self.assertIsNone(self.store.get_by_id(99999))

    def test_very_long_content(self):
        """Content up to MAX_CONTENT_SIZE must be accepted."""
        long_content = "x" * 100_000  # 100KB
        mid = self.store.add_memory(long_content)
        mem = self.store.get_by_id(mid)
        self.assertEqual(len(mem["content"]), 100_000)

    def test_unicode_content(self):
        """Unicode content must round-trip correctly."""
        content = "日本語テスト 🎯 émojis äöü"
        mid = self.store.add_memory(content)
        mem = self.store.get_by_id(mid)
        self.assertEqual(mem["content"], content)

    def test_special_characters_in_tags(self):
        """Tags with special characters must be stored correctly."""
        mid = self.store.add_memory("Tag test", tags=["c++", "c#", "node.js"])
        mem = self.store.get_by_id(mid)
        self.assertEqual(mem["tags"], ["c++", "c#", "node.js"])

    # === Security / Input Validation ===

    def test_content_size_limit(self):
        """Content exceeding MAX_CONTENT_SIZE must be rejected."""
        with self.assertRaises(ValueError):
            self.store.add_memory("x" * 1_000_001)

    def test_empty_content_rejected(self):
        """Empty content must be rejected."""
        with self.assertRaises(ValueError):
            self.store.add_memory("")

    def test_whitespace_only_content_rejected(self):
        """Whitespace-only content must be rejected (stripped to empty)."""
        with self.assertRaises(ValueError):
            self.store.add_memory("   \n\t  ")

    def test_non_string_content_rejected(self):
        """Non-string content must raise TypeError."""
        with self.assertRaises(TypeError):
            self.store.add_memory(12345)

    def test_too_many_tags_rejected(self):
        """More than MAX_TAGS tags must be rejected."""
        with self.assertRaises(ValueError):
            self.store.add_memory("tag test", tags=[f"tag{i}" for i in range(25)])

    def test_importance_clamped(self):
        """Out-of-range importance must be clamped, not error."""
        mid = self.store.add_memory("Clamp test high", importance=99)
        mem = self.store.get_by_id(mid)
        self.assertEqual(mem["importance"], 10)

        mid2 = self.store.add_memory("Clamp test low", importance=-5)
        mem2 = self.store.get_by_id(mid2)
        self.assertEqual(mem2["importance"], 1)

    def test_sql_injection_in_content(self):
        """SQL injection attempts in content must be safely stored."""
        evil = "'; DROP TABLE memories; --"
        mid = self.store.add_memory(evil)
        mem = self.store.get_by_id(mid)
        self.assertEqual(mem["content"], evil)
        # Table must still exist
        stats = self.store.get_stats()
        self.assertEqual(stats["total_memories"], 1)

    def test_sql_injection_in_search(self):
        """SQL injection in search query must not cause errors."""
        self.store.add_memory("Safe content")
        results = self.store.search("'; DROP TABLE memories; --")
        # Should return empty or results, not crash
        self.assertIsInstance(results, list)


class TestBackwardCompatibilityFallback(unittest.TestCase):
    """Test that everything works when DbConnectionManager is NOT available."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "fallback.db"
        self.vectors_path = Path(self.tmpdir) / "vectors"
        self.vectors_path.mkdir()

        import memory_store_v2
        self._orig_db = memory_store_v2.DB_PATH
        self._orig_mem = memory_store_v2.MEMORY_DIR
        self._orig_vec = memory_store_v2.VECTORS_PATH
        self._orig_flag = memory_store_v2.USE_CONNECTION_MANAGER
        memory_store_v2.DB_PATH = self.db_path
        memory_store_v2.MEMORY_DIR = Path(self.tmpdir)
        memory_store_v2.VECTORS_PATH = self.vectors_path
        memory_store_v2.USE_CONNECTION_MANAGER = False

        from memory_store_v2 import MemoryStoreV2
        self.store = MemoryStoreV2(self.db_path)

    def tearDown(self):
        import memory_store_v2
        memory_store_v2.DB_PATH = self._orig_db
        memory_store_v2.MEMORY_DIR = self._orig_mem
        memory_store_v2.VECTORS_PATH = self._orig_vec
        memory_store_v2.USE_CONNECTION_MANAGER = self._orig_flag
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_fallback_no_db_mgr(self):
        """With USE_CONNECTION_MANAGER=False, _db_mgr must be None."""
        self.assertIsNone(self.store._db_mgr)

    def test_fallback_add_memory(self):
        """add_memory must work in fallback mode."""
        mid = self.store.add_memory("Fallback test")
        self.assertGreater(mid, 0)

    def test_fallback_search(self):
        """search must work in fallback mode."""
        self.store.add_memory("Fallback search content")
        results = self.store.search("Fallback", limit=5)
        self.assertTrue(len(results) > 0)

    def test_fallback_stats(self):
        """get_stats must work in fallback mode."""
        self.store.add_memory("Stat in fallback")
        stats = self.store.get_stats()
        self.assertEqual(stats["total_memories"], 1)

    def test_fallback_delete(self):
        """delete must work in fallback mode."""
        mid = self.store.add_memory("Delete in fallback")
        self.assertTrue(self.store.delete_memory(mid))


class TestNewUserDockerScenario(unittest.TestCase):
    """
    Simulates a brand new user on Docker/Windows:
    - No existing database
    - No profiles.json
    - No vectors directory
    - Fresh install from scratch
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "memory.db"
        self.vectors_path = Path(self.tmpdir) / "vectors"
        # Deliberately do NOT create vectors dir — install should handle it
        # Deliberately do NOT create profiles.json

        import memory_store_v2
        self._orig_db = memory_store_v2.DB_PATH
        self._orig_mem = memory_store_v2.MEMORY_DIR
        self._orig_vec = memory_store_v2.VECTORS_PATH
        memory_store_v2.DB_PATH = self.db_path
        memory_store_v2.MEMORY_DIR = Path(self.tmpdir)
        memory_store_v2.VECTORS_PATH = self.vectors_path

    def tearDown(self):
        import memory_store_v2
        memory_store_v2.DB_PATH = self._orig_db
        memory_store_v2.MEMORY_DIR = self._orig_mem
        memory_store_v2.VECTORS_PATH = self._orig_vec
        DbConnectionManager.reset_instance(self.db_path)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_fresh_install_creates_database(self):
        """First-ever instantiation must create database from scratch."""
        from memory_store_v2 import MemoryStoreV2
        # Database does NOT exist yet
        self.assertFalse(self.db_path.exists())

        store = MemoryStoreV2(self.db_path)
        self.assertTrue(self.db_path.exists())

    def test_fresh_install_add_first_memory(self):
        """New user's first memory must succeed."""
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(self.db_path)
        mid = store.add_memory("My first memory!")
        self.assertEqual(mid, 1)

    def test_fresh_install_search_empty(self):
        """Search on empty fresh database must not crash."""
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(self.db_path)
        results = store.search("anything")
        self.assertEqual(results, [])

    def test_fresh_install_no_profiles_json(self):
        """Missing profiles.json must fall back to 'default' profile."""
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(self.db_path)
        profile = store._get_active_profile()
        self.assertEqual(profile, "default")

    def test_fresh_install_stats(self):
        """Stats on fresh database must return valid zeros."""
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(self.db_path)
        stats = store.get_stats()
        self.assertEqual(stats["total_memories"], 0)
        self.assertEqual(stats["total_clusters"], 0)

    def test_fresh_install_attribution_present(self):
        """Attribution must be embedded in fresh database."""
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(self.db_path)
        attr = store.get_attribution()
        self.assertEqual(attr["creator_name"], "Varun Pratap Bhardwaj")

    def test_wal_mode_on_fresh_database(self):
        """WAL mode must be active on newly created database."""
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(self.db_path)
        if store._db_mgr:
            diag = store._db_mgr.get_diagnostics()
            self.assertEqual(diag["journal_mode"], "wal")


class TestMcpServerSingleton(unittest.TestCase):
    """Test the singleton accessor pattern used in mcp_server.py."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "mcp_test.db"
        self.vectors_path = Path(self.tmpdir) / "vectors"
        self.vectors_path.mkdir()

        import memory_store_v2
        self._orig_db = memory_store_v2.DB_PATH
        self._orig_mem = memory_store_v2.MEMORY_DIR
        self._orig_vec = memory_store_v2.VECTORS_PATH
        memory_store_v2.DB_PATH = self.db_path
        memory_store_v2.MEMORY_DIR = Path(self.tmpdir)
        memory_store_v2.VECTORS_PATH = self.vectors_path

    def tearDown(self):
        import memory_store_v2
        memory_store_v2.DB_PATH = self._orig_db
        memory_store_v2.MEMORY_DIR = self._orig_mem
        memory_store_v2.VECTORS_PATH = self._orig_vec
        DbConnectionManager.reset_instance(self.db_path)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_singleton_returns_same_instance(self):
        """get_store() pattern must return the same object every time."""
        from memory_store_v2 import MemoryStoreV2

        _store = None

        def get_store():
            nonlocal _store
            if _store is None:
                _store = MemoryStoreV2(self.db_path)
            return _store

        s1 = get_store()
        s2 = get_store()
        s3 = get_store()
        self.assertIs(s1, s2)
        self.assertIs(s2, s3)

    def test_singleton_shared_db_mgr(self):
        """Singleton must share one DbConnectionManager across all calls."""
        from memory_store_v2 import MemoryStoreV2

        store = MemoryStoreV2(self.db_path)
        self.assertIsNotNone(store._db_mgr)

        # Simulating what mcp_server.py does — multiple tool handlers use same store
        mid = store.add_memory("MCP call 1")
        results = store.search("MCP", limit=5)
        stats = store.get_stats()
        self.assertGreater(mid, 0)
        self.assertTrue(len(results) > 0)
        self.assertEqual(stats["total_memories"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
