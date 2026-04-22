"""Silent debug-swallows were elevated to warnings in v3.4.26.

This test pins down one representative call site — a schema migration
failure on engine initialization — and asserts the operator-visible
log level is WARNING, not DEBUG. If any of the other sites regress to
``logger.debug`` the grep-based check at the bottom flags it.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from superlocalmemory.core.config import SLMConfig
from superlocalmemory.core.engine import MemoryEngine
from superlocalmemory.core.engine_capabilities import Capabilities
from superlocalmemory.storage.models import Mode


@pytest.fixture
def mode_a_config(tmp_path):
    cfg = SLMConfig.for_mode(Mode.A)
    cfg.base_dir = tmp_path
    cfg.db_path = tmp_path / "memory.db"
    return cfg


def test_schema_migration_failure_emits_warning(mode_a_config, monkeypatch, caplog):
    """Force V3.4.11 schema migration to blow up — must hit WARNING."""
    def _boom(*_a, **_kw):
        raise RuntimeError("synthetic migration failure")

    import superlocalmemory.storage.schema_v3411 as mod
    monkeypatch.setattr(mod, "apply_v3411_schema", _boom)

    caplog.set_level(logging.WARNING, logger="superlocalmemory.core.engine")
    engine = MemoryEngine(mode_a_config, capabilities=Capabilities.LIGHT)
    engine.initialize()

    warnings = [r for r in caplog.records
                if r.levelno >= logging.WARNING and "V3.4.11" in r.getMessage()]
    assert warnings, f"expected WARNING for V3.4.11 failure, got {caplog.records}"


def test_no_silent_debug_swallows_in_shipped_paths():
    """Grep-style check — the five call sites elevated in v3.4.26 must
    never regress back to ``logger.debug``. If you intentionally lower
    one, update this test."""
    root = Path(__file__).resolve().parents[2] / "src" / "superlocalmemory"
    targets = [
        root / "core" / "engine.py",
        root / "mcp" / "server.py",
        root / "hooks" / "auto_recall.py",
        root / "hooks" / "auto_capture.py",
    ]
    # Phrases that previously accompanied logger.debug in these files.
    forbidden_combos = [
        ("logger.debug", "schema migration"),
        ("_logger.debug", "pre-warmup failed"),
        ("_logger.debug", "Daemon auto-start failed"),
        ("_logger.debug", "Mesh auto-register failed"),
        ("logger.debug", "Auto-recall failed"),
        ("logger.debug", "Auto-recall query failed"),
        ("logger.debug", "Auto-capture store failed"),
    ]
    offences: list[str] = []
    for path in targets:
        text = path.read_text()
        for needle_logger, needle_context in forbidden_combos:
            if needle_logger in text and needle_context in text:
                # Same-line correlation check.
                for line in text.splitlines():
                    if needle_logger in line and needle_context in line:
                        offences.append(f"{path.name}: {line.strip()}")
    assert not offences, "\n".join(offences)
