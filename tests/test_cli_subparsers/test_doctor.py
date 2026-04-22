# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for slm doctor."""

from __future__ import annotations

import json
from pathlib import Path


def _imports():
    from superlocalmemory.cli import doctor_cmd
    return doctor_cmd


def test_run_checks_on_clean_env(tmp_path: Path) -> None:
    dc = _imports()
    report = dc.run_checks(data_dir=tmp_path)
    assert "checks" in report
    assert len(report["checks"]) >= 5
    assert isinstance(report["exit_code"], int)


def test_report_flags_missing_migration_marker(tmp_path: Path) -> None:
    dc = _imports()
    report = dc.run_checks(data_dir=tmp_path)
    names = {c["name"] for c in report["checks"]}
    assert "v3.4.26 migration" in names
    migration = next(c for c in report["checks"] if c["name"] == "v3.4.26 migration")
    assert migration["status"] == "warn"


def test_report_passes_after_migration(tmp_path: Path) -> None:
    from superlocalmemory.migrations.v3_4_25_to_v3_4_26 import migrate
    migrate(tmp_path)
    dc = _imports()
    report = dc.run_checks(data_dir=tmp_path)
    migration = next(c for c in report["checks"] if c["name"] == "v3.4.26 migration")
    assert migration["status"] == "ok"


def test_json_output_shape(tmp_path: Path) -> None:
    dc = _imports()
    report = dc.run_checks(data_dir=tmp_path)
    blob = json.dumps(report)
    back = json.loads(blob)
    assert back == report


def test_cloud_sync_refusal_detected(tmp_path: Path) -> None:
    dc = _imports()
    bad = tmp_path / "Dropbox" / "slm"
    bad.mkdir(parents=True)
    report = dc.run_checks(data_dir=bad)
    cloud = next(
        (c for c in report["checks"] if c["name"] == "data directory"),
        None,
    )
    assert cloud is not None
    assert cloud["status"] == "error"
    assert report["exit_code"] != 0
