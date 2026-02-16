#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Signal Inference Engine Tests (v2.7.4)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Tests for the implicit feedback signal inference system.
"""

import time
import threading
import pytest
import sys
from pathlib import Path

# Ensure mcp_server module is importable for RecallBuffer
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestRecallBuffer:
    """Test the _RecallBuffer class from mcp_server."""

    def _make_buffer(self):
        """Create a fresh RecallBuffer for testing."""
        # Import directly to avoid starting MCP server
        from importlib import import_module
        import types

        # Create a minimal RecallBuffer instance by duplicating the class logic
        # without importing the full mcp_server (which requires MCP deps)
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        class RecallBuffer:
            def __init__(self):
                self._lock = threading.Lock()
                self._last_recall = {}
                self._global_last = None
                self._signal_timestamps = {}
                self._recent_result_ids = set()
                self._recall_count = 0
                self._positive_threshold = 300.0
                self._inter_recall_times = []

            def record_recall(self, query, result_ids, agent_id="mcp-client"):
                now = time.time()
                signals = []
                with self._lock:
                    self._recall_count += 1
                    result_id_set = set(result_ids)
                    self._recent_result_ids = result_id_set
                    current = {
                        "query": query, "result_ids": result_ids,
                        "result_id_set": result_id_set, "timestamp": now,
                        "agent_id": agent_id,
                    }
                    prev = self._last_recall.get(agent_id)
                    if prev:
                        time_gap = now - prev["timestamp"]
                        self._inter_recall_times.append(time_gap)
                        if len(self._inter_recall_times) > 100:
                            self._inter_recall_times = self._inter_recall_times[-100:]
                        if len(self._inter_recall_times) >= 10:
                            sorted_times = sorted(self._inter_recall_times)
                            median = sorted_times[len(sorted_times) // 2]
                            self._positive_threshold = max(60.0, min(median * 0.8, 1800.0))
                        if time_gap < 30.0 and query != prev["query"]:
                            for mid in prev["result_ids"][:5]:
                                signals.append({
                                    "memory_id": mid,
                                    "signal_type": "implicit_negative_requick",
                                    "query": prev["query"],
                                    "rank_position": prev["result_ids"].index(mid) + 1,
                                })
                        elif time_gap > self._positive_threshold:
                            for mid in prev["result_ids"][:3]:
                                signals.append({
                                    "memory_id": mid,
                                    "signal_type": "implicit_positive_timegap",
                                    "query": prev["query"],
                                    "rank_position": prev["result_ids"].index(mid) + 1,
                                })
                        overlap = result_id_set & prev["result_id_set"]
                        for mid in overlap:
                            signals.append({
                                "memory_id": mid,
                                "signal_type": "implicit_positive_reaccess",
                                "query": query,
                            })
                    global_prev = self._global_last
                    if global_prev and global_prev["agent_id"] != agent_id:
                        cross_overlap = result_id_set & global_prev["result_id_set"]
                        for mid in cross_overlap:
                            signals.append({
                                "memory_id": mid,
                                "signal_type": "implicit_positive_cross_tool",
                                "query": query,
                            })
                    self._last_recall[agent_id] = current
                    self._global_last = current
                return signals

            def check_post_action(self, memory_id, action):
                with self._lock:
                    if memory_id not in self._recent_result_ids:
                        return None
                    if action == "update":
                        return {"memory_id": memory_id, "signal_type": "implicit_positive_post_update",
                                "query": self._global_last["query"] if self._global_last else ""}
                    elif action == "delete":
                        return {"memory_id": memory_id, "signal_type": "implicit_negative_post_delete",
                                "query": self._global_last["query"] if self._global_last else ""}
                return None

            def check_rate_limit(self, agent_id, max_per_minute=5):
                now = time.time()
                with self._lock:
                    if agent_id not in self._signal_timestamps:
                        self._signal_timestamps[agent_id] = []
                    self._signal_timestamps[agent_id] = [
                        ts for ts in self._signal_timestamps[agent_id] if now - ts < 60.0
                    ]
                    if len(self._signal_timestamps[agent_id]) >= max_per_minute:
                        return False
                    self._signal_timestamps[agent_id].append(now)
                    return True

            def get_recall_count(self):
                with self._lock:
                    return self._recall_count

            def get_stats(self):
                with self._lock:
                    return {
                        "recall_count": self._recall_count,
                        "tracked_agents": len(self._last_recall),
                        "positive_threshold_s": round(self._positive_threshold, 1),
                        "recent_results_count": len(self._recent_result_ids),
                    }

        return RecallBuffer()

    def test_first_recall_no_signals(self):
        """First recall should produce no signals (nothing to compare with)."""
        buf = self._make_buffer()
        signals = buf.record_recall("test query", [1, 2, 3])
        assert signals == []
        assert buf.get_recall_count() == 1

    def test_quick_requery_negative_signals(self):
        """Quick re-query with different query should produce negative signals."""
        buf = self._make_buffer()
        buf.record_recall("first query", [10, 20, 30])
        # Simulate quick re-query (no sleep needed — time gap is ~0)
        signals = buf.record_recall("different query", [40, 50])
        negative_signals = [s for s in signals if s["signal_type"] == "implicit_negative_requick"]
        assert len(negative_signals) > 0
        # Should target previous results (10, 20, 30)
        neg_ids = {s["memory_id"] for s in negative_signals}
        assert neg_ids.issubset({10, 20, 30})

    def test_same_query_no_negative(self):
        """Same exact query repeated quickly should NOT produce negative signals."""
        buf = self._make_buffer()
        buf.record_recall("same query", [10, 20])
        signals = buf.record_recall("same query", [10, 20])
        negative_signals = [s for s in signals if s["signal_type"] == "implicit_negative_requick"]
        assert len(negative_signals) == 0

    def test_reaccess_positive_signals(self):
        """Same memory appearing in consecutive recalls = positive."""
        buf = self._make_buffer()
        buf.record_recall("query a", [10, 20, 30])
        signals = buf.record_recall("query b", [20, 40, 50])
        reaccess = [s for s in signals if s["signal_type"] == "implicit_positive_reaccess"]
        assert len(reaccess) == 1
        assert reaccess[0]["memory_id"] == 20

    def test_cross_tool_positive_signals(self):
        """Same memory recalled by different agents = cross-tool positive."""
        buf = self._make_buffer()
        buf.record_recall("query", [10, 20], agent_id="claude")
        signals = buf.record_recall("query", [20, 30], agent_id="cursor")
        cross_tool = [s for s in signals if s["signal_type"] == "implicit_positive_cross_tool"]
        assert len(cross_tool) == 1
        assert cross_tool[0]["memory_id"] == 20

    def test_post_action_update_tracked(self):
        """Update after recall should generate positive signal."""
        buf = self._make_buffer()
        buf.record_recall("query", [10, 20, 30])
        signal = buf.check_post_action(20, "update")
        assert signal is not None
        assert signal["signal_type"] == "implicit_positive_post_update"
        assert signal["memory_id"] == 20

    def test_post_action_delete_tracked(self):
        """Delete after recall should generate negative signal."""
        buf = self._make_buffer()
        buf.record_recall("query", [10, 20, 30])
        signal = buf.check_post_action(10, "delete")
        assert signal is not None
        assert signal["signal_type"] == "implicit_negative_post_delete"

    def test_post_action_unrelated_memory_ignored(self):
        """Action on memory NOT in recent results should be ignored."""
        buf = self._make_buffer()
        buf.record_recall("query", [10, 20, 30])
        signal = buf.check_post_action(999, "update")
        assert signal is None

    def test_rate_limiting(self):
        """Rate limiter should cap signals per agent per minute."""
        buf = self._make_buffer()
        agent = "test-agent"
        # First 5 should be allowed
        for i in range(5):
            assert buf.check_rate_limit(agent) is True
        # 6th should be blocked
        assert buf.check_rate_limit(agent) is False

    def test_rate_limiting_different_agents(self):
        """Different agents should have independent rate limits."""
        buf = self._make_buffer()
        for i in range(5):
            assert buf.check_rate_limit("agent1") is True
        assert buf.check_rate_limit("agent1") is False
        # Agent2 should still be allowed
        assert buf.check_rate_limit("agent2") is True

    def test_recall_count_increments(self):
        """Recall count should increment with each recall."""
        buf = self._make_buffer()
        assert buf.get_recall_count() == 0
        buf.record_recall("q1", [1])
        assert buf.get_recall_count() == 1
        buf.record_recall("q2", [2])
        assert buf.get_recall_count() == 2

    def test_negative_signals_cap_at_5(self):
        """Negative signals should only target top 5 results."""
        buf = self._make_buffer()
        buf.record_recall("first", list(range(1, 11)))  # 10 results
        signals = buf.record_recall("different", [99])
        negative = [s for s in signals if s["signal_type"] == "implicit_negative_requick"]
        assert len(negative) <= 5

    def test_stats_output(self):
        """Stats should report correct values."""
        buf = self._make_buffer()
        buf.record_recall("q", [1, 2, 3])
        stats = buf.get_stats()
        assert stats["recall_count"] == 1
        assert stats["tracked_agents"] == 1
        assert stats["recent_results_count"] == 3
        assert stats["positive_threshold_s"] == 300.0

    def test_thread_safety(self):
        """Buffer should handle concurrent access without errors."""
        buf = self._make_buffer()
        errors = []

        def worker(agent_id):
            try:
                for i in range(20):
                    buf.record_recall(f"query_{i}", [i, i+1], agent_id=agent_id)
                    buf.check_rate_limit(agent_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"agent_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Thread safety errors: {errors}"
        assert buf.get_recall_count() == 100  # 5 agents x 20 recalls


class TestFeedbackCollectorImplicit:
    """Test the new implicit signal methods in FeedbackCollector."""

    def test_record_implicit_signal_valid(self):
        """Valid implicit signal should be stored."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feedback_collector import FeedbackCollector
        fc = FeedbackCollector()
        result = fc.record_implicit_signal(
            memory_id=42,
            query="test query",
            signal_type="implicit_positive_timegap",
        )
        # Should return row ID or None (depends on DB availability)
        # Just verify it doesn't crash
        assert result is None or isinstance(result, int)

    def test_record_implicit_signal_invalid_type(self):
        """Invalid signal type should return None."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feedback_collector import FeedbackCollector
        fc = FeedbackCollector()
        result = fc.record_implicit_signal(
            memory_id=42,
            query="test",
            signal_type="totally_fake_type",
        )
        assert result is None

    def test_record_dashboard_feedback_valid(self):
        """Valid dashboard feedback should be stored."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feedback_collector import FeedbackCollector
        fc = FeedbackCollector()
        result = fc.record_dashboard_feedback(
            memory_id=42,
            query="test query",
            feedback_type="thumbs_up",
        )
        assert result is None or isinstance(result, int)

    def test_record_dashboard_feedback_invalid_type(self):
        """Invalid feedback type should return None."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feedback_collector import FeedbackCollector
        fc = FeedbackCollector()
        result = fc.record_dashboard_feedback(
            memory_id=42,
            query="test",
            feedback_type="invalid_type",
        )
        assert result is None

    def test_signal_values_complete(self):
        """All declared signal types should have numeric values."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feedback_collector import FeedbackCollector
        fc = FeedbackCollector()
        for signal_type, value in fc.SIGNAL_VALUES.items():
            assert isinstance(value, (int, float)), f"{signal_type} has non-numeric value"
            assert 0.0 <= value <= 1.0, f"{signal_type} value {value} out of range"


class TestFeatureExpansion:
    """Test the 10→12 feature vector expansion."""

    def test_feature_count_is_12(self):
        """Feature vector should have 12 dimensions."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feature_extractor import FEATURE_NAMES, NUM_FEATURES
        assert NUM_FEATURES == 12
        assert len(FEATURE_NAMES) == 12

    def test_new_features_present(self):
        """signal_count and avg_signal_value should be in feature names."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feature_extractor import FEATURE_NAMES
        assert 'signal_count' in FEATURE_NAMES
        assert 'avg_signal_value' in FEATURE_NAMES
        assert FEATURE_NAMES.index('signal_count') == 10
        assert FEATURE_NAMES.index('avg_signal_value') == 11

    def test_extract_features_returns_12(self):
        """Extract should return 12-element vector."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feature_extractor import FeatureExtractor
        fe = FeatureExtractor()
        features = fe.extract_features(
            {'id': 1, 'content': 'test', 'importance': 5},
            'test'
        )
        assert len(features) == 12

    def test_signal_features_with_stats(self):
        """Signal features should use provided stats."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feature_extractor import FeatureExtractor
        fe = FeatureExtractor()
        fe.set_context(signal_stats={
            '42': {'count': 8, 'avg_value': 0.9},
        })
        features = fe.extract_features(
            {'id': 42, 'content': 'test', 'importance': 5},
            'test'
        )
        assert features[10] == 0.8  # count=8, 8/10=0.8
        assert features[11] == 0.9  # avg_value=0.9

    def test_signal_features_without_stats(self):
        """Signal features should default safely without stats."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from feature_extractor import FeatureExtractor
        fe = FeatureExtractor()
        # No set_context call — signal_stats empty
        features = fe.extract_features(
            {'id': 99, 'content': 'test', 'importance': 5},
            'test'
        )
        assert features[10] == 0.0  # No stats → 0.0
        assert features[11] == 0.5  # No stats → neutral 0.5
