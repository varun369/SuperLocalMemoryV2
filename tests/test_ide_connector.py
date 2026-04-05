# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for IDE Connector — Task 17 of V3 build."""

import json

import pytest
from pathlib import Path

from superlocalmemory.hooks.ide_connector import IDEConnector, SLM_MARKER


@pytest.fixture
def connector(tmp_path):
    return IDEConnector(home=tmp_path)


def test_detect_claude_code(tmp_path):
    (tmp_path / ".claude").mkdir()
    connector = IDEConnector(home=tmp_path)
    detected = connector.detect_ides()
    assert detected["claude_code"] is True


def test_detect_cursor(tmp_path):
    (tmp_path / ".cursor").mkdir()
    connector = IDEConnector(home=tmp_path)
    detected = connector.detect_ides()
    assert detected["cursor"] is True


def test_detect_nothing(tmp_path):
    connector = IDEConnector(home=tmp_path)
    detected = connector.detect_ides()
    assert all(v is False for v in detected.values())


def test_connect_claude_code(tmp_path):
    (tmp_path / ".claude").mkdir()
    connector = IDEConnector(home=tmp_path)
    success = connector.connect("claude_code")
    assert success
    content = (tmp_path / ".claude" / "CLAUDE.md").read_text()
    assert SLM_MARKER in content


def test_connect_cursor(tmp_path):
    (tmp_path / ".cursor").mkdir()
    connector = IDEConnector(home=tmp_path)
    success = connector.connect("cursor")
    assert success
    content = (tmp_path / ".cursorrules").read_text()
    assert SLM_MARKER in content


def test_connect_does_not_overwrite(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# My Custom Rules\nDo not touch this.\n")

    connector = IDEConnector(home=tmp_path)
    connector.connect("claude_code")
    content = claude_md.read_text()
    assert "My Custom Rules" in content  # preserved
    assert SLM_MARKER in content  # appended


def test_connect_is_idempotent(tmp_path):
    (tmp_path / ".cursor").mkdir()
    connector = IDEConnector(home=tmp_path)
    connector.connect("cursor")
    connector.connect("cursor")  # run twice
    content = (tmp_path / ".cursorrules").read_text()
    # Should only have ONE SLM section
    assert content.count(SLM_MARKER) == 1


def test_connect_all(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cursor").mkdir()
    connector = IDEConnector(home=tmp_path)
    results = connector.connect_all()
    assert results["claude_code"] == "connected"
    assert results["cursor"] == "connected"
    assert results["windsurf"] == "not_installed"


def test_connect_json_ide(tmp_path):
    (tmp_path / ".continue").mkdir()
    connector = IDEConnector(home=tmp_path)
    success = connector.connect("continue_dev")
    assert success
    config = json.loads((tmp_path / ".continue" / "config.json").read_text())
    assert "superlocalmemory" in config.get("mcpServers", {})


def test_get_status(tmp_path):
    (tmp_path / ".claude").mkdir()
    connector = IDEConnector(home=tmp_path)
    status = connector.get_status()
    assert len(status) >= 5
    claude = next(s for s in status if s["id"] == "claude_code")
    assert claude["installed"] is True


def test_unknown_ide(tmp_path):
    connector = IDEConnector(home=tmp_path)
    assert connector.connect("unknown_ide") is False
