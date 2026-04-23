"""Hooks decouple from the engine — accept recall_fn / store_fn callables.

Purpose: in multi-IDE MCP processes the engine is LIGHT (no embedder).
Hooks must be able to operate there by calling through a supplied
worker-pool-shaped callable instead of the engine. The existing
``engine=...`` construction continues to work unchanged for CLI callers.
"""
from __future__ import annotations

from types import SimpleNamespace

from superlocalmemory.hooks.auto_capture import AutoCapture
from superlocalmemory.hooks.auto_recall import AutoRecall


def _response(fact_ids, score=0.9, content="Some memory"):
    results = [
        SimpleNamespace(
            fact=SimpleNamespace(fact_id=fid, content=content),
            score=score,
        )
        for fid in fact_ids
    ]
    return SimpleNamespace(results=results)


class TestAutoRecallCallable:
    def test_recall_fn_bypasses_engine(self):
        captured = {}

        def fake_recall(query, limit=10, **_):
            captured["query"] = query
            captured["limit"] = limit
            return _response(["f1", "f2"], score=0.8)

        auto = AutoRecall(recall_fn=fake_recall)
        out = auto.get_session_context(query="what did we ship")
        assert "Some memory" in out
        assert captured["query"] == "what did we ship"

    def test_engine_fallback_when_no_fn(self):
        # Backward compat — existing callers supply engine, not fn
        calls = []

        class FakeEngine:
            def recall(self, q, limit=10, **_):
                calls.append((q, limit))
                return _response(["f1"])

        auto = AutoRecall(engine=FakeEngine())
        auto.get_session_context(query="hi")
        assert calls == [("hi", 10)]

    def test_fn_takes_precedence_over_engine(self):
        fn_calls = []
        engine_calls = []

        def fn(q, limit=10, **_):
            fn_calls.append(q)
            return _response(["f1"])

        class E:
            def recall(self, q, limit=10, **_):
                engine_calls.append(q)
                return _response(["f2"])

        auto = AutoRecall(engine=E(), recall_fn=fn)
        auto.get_session_context(query="x")
        assert fn_calls and not engine_calls

    def test_no_fn_no_engine_returns_empty(self):
        auto = AutoRecall()
        assert auto.get_session_context(query="anything") == ""
        assert auto.get_query_context("anything") == []

    def test_query_context_uses_fn(self):
        def fn(q, limit=10, **_):
            return _response(["f1", "f2"], score=0.7)

        auto = AutoRecall(recall_fn=fn)
        results = auto.get_query_context("q")
        assert len(results) == 2
        assert results[0]["fact_id"] == "f1"


class TestAutoCaptureCallable:
    def test_store_fn_bypasses_engine(self):
        captured = {}

        def fake_store(content, metadata=None):
            captured["content"] = content
            captured["metadata"] = metadata
            return ["stored-id-1"]

        auto = AutoCapture(store_fn=fake_store)
        ok = auto.capture("a decision was made here", category="decision")
        assert ok is True
        assert "decision" in captured["content"]
        assert captured["metadata"]["source"] == "auto-capture"
        assert captured["metadata"]["category"] == "decision"

    def test_engine_fallback_when_no_fn(self):
        calls = []

        class FakeEngine:
            def store(self, content, metadata=None):
                calls.append((content, metadata))
                return ["id1"]

        auto = AutoCapture(engine=FakeEngine())
        assert auto.capture("content", category="bug") is True
        assert calls and calls[0][1]["category"] == "bug"

    def test_fn_takes_precedence_over_engine(self):
        fn_calls = []
        engine_calls = []

        def fn(content, metadata=None):
            fn_calls.append(content)
            return ["f1"]

        class E:
            def store(self, content, metadata=None):
                engine_calls.append(content)
                return ["e1"]

        auto = AutoCapture(engine=E(), store_fn=fn)
        auto.capture("something", category="decision")
        assert fn_calls and not engine_calls

    def test_no_fn_no_engine_returns_false(self):
        auto = AutoCapture()
        assert auto.capture("content") is False

    def test_capture_does_not_mutate_caller_metadata(self):
        """Regression guard for Stage 9 P9-C-02: pool_store ships the
        metadata dict cross-process; callers often reuse the same dict
        across captures. Auto-capture must not inject its own keys into
        the caller's dict."""
        captured_meta = {}

        def fn(content, metadata=None):
            captured_meta.clear()
            captured_meta.update(metadata or {})
            return ["id1"]

        auto = AutoCapture(store_fn=fn)
        user_dict = {"user_key": "user_value"}
        auto.capture("content here", category="bug", metadata=user_dict)
        assert user_dict == {"user_key": "user_value"}, \
            f"caller metadata was mutated: {user_dict}"
        # store_fn still saw the enriched metadata
        assert captured_meta.get("source") == "auto-capture"
        assert captured_meta.get("user_key") == "user_value"
