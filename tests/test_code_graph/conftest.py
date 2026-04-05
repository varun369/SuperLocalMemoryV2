# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Shared fixtures for CodeGraph tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.service import CodeGraphService


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Temporary directory for test databases."""
    return tmp_path


@pytest.fixture
def db_path(tmp_dir: Path) -> Path:
    """Path for a temporary code_graph.db."""
    return tmp_dir / "code_graph.db"


@pytest.fixture
def db(db_path: Path) -> CodeGraphDatabase:
    """Fresh CodeGraphDatabase instance."""
    return CodeGraphDatabase(db_path)


@pytest.fixture
def config(tmp_dir: Path) -> CodeGraphConfig:
    """CodeGraphConfig with enabled=True and tmp paths."""
    return CodeGraphConfig(
        enabled=True,
        repo_root=tmp_dir / "repo",
        db_path=tmp_dir / "code_graph.db",
    )


@pytest.fixture
def service(config: CodeGraphConfig) -> CodeGraphService:
    """CodeGraphService with test config."""
    return CodeGraphService(config)
