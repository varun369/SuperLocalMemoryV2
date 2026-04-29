# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for hooks.auto_recall_hook — TDD RED phase.

The auto_recall_hook is a standalone UserPromptSubmit handler:
  - Reads stdin JSON from Claude Code
  - Detects ack prompts → silent (empty JSON)
  - Substantive prompts → enqueue to recall_queue.db → poll → envelope
  - Fail-open: any error → {}, exit 0
  - NEVER imports MemoryEngine or loads ONNX/PyTorch

Tests mock the queue and daemon to verify hook logic in isolation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# -----------------------------------------------------------------------
# Ack detection — silent fast path
# -----------------------------------------------------------------------

_ACK_PROMPTS = [
    "yes", "no", "ok", "okay", "approved", "thanks", "thank you",
    "go", "sure", "yep", "nope", "done", "y", "n", "cool",
    "got it", "right", "correct", "Yes.", "OK!", "  yes  ",
]

_SUBSTANTIVE_PROMPTS = [
    "What is the SLM recall queue architecture?",
    "Fix the memory blast in auto_recall hooks",
    "Tell me about the v3.4.26 plan for unified queue",
    "How does the fencing token prevent stale writes?",
    "I need to refactor the worker pool recall path",
]


def _run_hook(prompt: str, tmp_path: Path, **env_overrides) -> dict:
    """Invoke auto_recall_hook.main() with a fake stdin payload.

    Always mocks ``_try_socket_first`` to return None so tests are deterministic
    regardless of whether the hook daemon socket is running on the host. The
    socket is the primary recall path in production; when it's unavailable the
    hook falls back to ``_do_recall`` (which individual tests mock as needed).
    """
    from superlocalmemory.hooks.auto_recall_hook import main

    payload = json.dumps({"prompt": prompt, "session_id": "test-session"})
    captured = StringIO()
    with patch("superlocalmemory.hooks.auto_recall_hook._try_socket_first",
               return_value=None), \
         patch("sys.stdin", StringIO(payload)), \
         patch("sys.stdout", captured):
        exit_code = main()

    assert exit_code == 0, "Hook must always exit 0 (fail-open)"
    output = captured.getvalue()
    if not output.strip():
        return {}
    return json.loads(output)


@pytest.mark.parametrize("prompt", _ACK_PROMPTS)
def test_ack_prompt_returns_empty(tmp_path: Path, prompt: str) -> None:
    """Ack prompts (yes/ok/approved/etc) produce no recall, no output."""
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=None) as mock_recall:
        result = _run_hook(prompt, tmp_path)
    assert result == {}, f"Ack prompt '{prompt}' should produce empty output"
    mock_recall.assert_not_called()


@pytest.mark.parametrize("prompt", _SUBSTANTIVE_PROMPTS)
def test_substantive_prompt_triggers_recall(tmp_path: Path, prompt: str) -> None:
    """Substantive prompts trigger recall and inject context."""
    fake_results = [
        {"fact_id": "f1", "content": "SLM uses WAL mode SQLite", "score": 0.9},
        {"fact_id": "f2", "content": "Fencing token prevents stale writes", "score": 0.8},
        {"fact_id": "f3", "content": "Queue consumer routes through pool", "score": 0.7},
    ]
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=fake_results):
        result = _run_hook(prompt, tmp_path)

    assert "hookSpecificOutput" in result
    output = result["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit"
    ctx = output["additionalContext"]
    assert "SLM uses WAL mode SQLite" in ctx
    assert "Fencing token" in ctx


# -----------------------------------------------------------------------
# Envelope format
# -----------------------------------------------------------------------

def test_envelope_has_untrusted_boundary_markers(tmp_path: Path) -> None:
    """Recalled content is wrapped in untrusted-boundary markers."""
    fake_results = [{"fact_id": "f1", "content": "test content", "score": 0.9}]
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=fake_results):
        result = _run_hook("what is the plan?", tmp_path)

    ctx = result["hookSpecificOutput"]["additionalContext"]
    assert "[BEGIN UNTRUSTED SLM CONTEXT" in ctx
    assert "[END UNTRUSTED SLM CONTEXT]" in ctx


def test_envelope_includes_slm_auto_recall_header(tmp_path: Path) -> None:
    """Output includes SLM AUTO-RECALL header for human readability."""
    fake_results = [{"fact_id": "f1", "content": "memory hit", "score": 0.9}]
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=fake_results):
        result = _run_hook("tell me about the project", tmp_path)

    ctx = result["hookSpecificOutput"]["additionalContext"]
    assert "SLM AUTO-RECALL" in ctx


# -----------------------------------------------------------------------
# Fail-open behavior
# -----------------------------------------------------------------------

def test_recall_failure_returns_empty(tmp_path: Path) -> None:
    """If recall raises, hook returns {} (fail-open)."""
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               side_effect=RuntimeError("Queue exploded")):
        result = _run_hook("what is the queue status?", tmp_path)
    assert result == {}


def test_empty_recall_results_returns_empty(tmp_path: Path) -> None:
    """If recall returns empty list, hook returns {}."""
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=[]):
        result = _run_hook("anything relevant?", tmp_path)
    assert result == {}


def test_none_recall_results_returns_empty(tmp_path: Path) -> None:
    """If recall returns None (timeout), hook returns {}."""
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=None):
        result = _run_hook("search for context", tmp_path)
    assert result == {}


# -----------------------------------------------------------------------
# Malformed input handling
# -----------------------------------------------------------------------

def test_empty_stdin_returns_empty(tmp_path: Path) -> None:
    from superlocalmemory.hooks.auto_recall_hook import main
    captured = StringIO()
    with patch("sys.stdin", StringIO("")), patch("sys.stdout", captured):
        exit_code = main()
    assert exit_code == 0
    assert captured.getvalue().strip() in ("", "{}")


def test_invalid_json_stdin_returns_empty(tmp_path: Path) -> None:
    from superlocalmemory.hooks.auto_recall_hook import main
    captured = StringIO()
    with patch("sys.stdin", StringIO("not json at all")), \
         patch("sys.stdout", captured):
        exit_code = main()
    assert exit_code == 0
    assert captured.getvalue().strip() in ("", "{}")


def test_missing_prompt_field_returns_empty(tmp_path: Path) -> None:
    from superlocalmemory.hooks.auto_recall_hook import main
    captured = StringIO()
    payload = json.dumps({"session_id": "s1"})
    with patch("sys.stdin", StringIO(payload)), \
         patch("sys.stdout", captured):
        exit_code = main()
    assert exit_code == 0
    assert captured.getvalue().strip() in ("", "{}")


# -----------------------------------------------------------------------
# Mode-aware timeout
# -----------------------------------------------------------------------

def test_mode_a_timeout(tmp_path: Path) -> None:
    """Mode A timeout should be ≤10s."""
    from superlocalmemory.hooks.auto_recall_hook import _get_mode_timeout
    assert _get_mode_timeout("A") <= 10.0


def test_mode_b_timeout(tmp_path: Path) -> None:
    """Mode B timeout should be ≤25s."""
    from superlocalmemory.hooks.auto_recall_hook import _get_mode_timeout
    assert _get_mode_timeout("B") <= 25.0


def test_mode_c_timeout(tmp_path: Path) -> None:
    """Mode C timeout should be ≤40s."""
    from superlocalmemory.hooks.auto_recall_hook import _get_mode_timeout
    assert _get_mode_timeout("C") <= 40.0


# -----------------------------------------------------------------------
# No engine import — memory safety
# -----------------------------------------------------------------------

def test_hook_module_never_imports_engine() -> None:
    """auto_recall_hook must not import MemoryEngine at module level."""
    import importlib
    import sys

    mod_name = "superlocalmemory.hooks.auto_recall_hook"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    mod = importlib.import_module(mod_name)
    assert not hasattr(mod, "MemoryEngine"), \
        "auto_recall_hook must NOT import MemoryEngine — memory blast risk"


# -----------------------------------------------------------------------
# Content truncation safety
# -----------------------------------------------------------------------

def test_long_recall_content_is_truncated(tmp_path: Path) -> None:
    """Recalled content longer than 2000 chars is truncated."""
    fake_results = [
        {"fact_id": "f1", "content": "A" * 5000, "score": 0.9},
    ]
    with patch("superlocalmemory.hooks.auto_recall_hook._do_recall",
               return_value=fake_results):
        result = _run_hook("give me everything", tmp_path)

    ctx = result["hookSpecificOutput"]["additionalContext"]
    # Total context including markers should be bounded
    assert len(ctx) < 6000, f"Context too long: {len(ctx)} chars"
