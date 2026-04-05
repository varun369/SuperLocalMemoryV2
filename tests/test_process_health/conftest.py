# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Conftest for Phase H0 process health tests.

Provides temporary PID file path and default ReaperConfig fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_pid_file(tmp_path: Path) -> Path:
    """Return path to a temporary PID file."""
    return tmp_path / "slm.pids"


@pytest.fixture
def default_reaper_config():
    """Return a ReaperConfig with defaults."""
    from superlocalmemory.infra.process_reaper import ReaperConfig

    return ReaperConfig()
