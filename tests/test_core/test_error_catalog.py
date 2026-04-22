# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for core.error_catalog."""

from __future__ import annotations

from superlocalmemory.core.error_envelope import ErrorCode
from superlocalmemory.core import error_catalog as ec


def test_all_error_codes_have_entries() -> None:
    for code in ErrorCode:
        entry = ec.lookup(code)
        assert entry["code"] == code.value
        assert entry["title"]
        assert entry["cli_message"]
        assert isinstance(entry["recovery"], list)
        assert isinstance(entry["exit_code"], int)


def test_unknown_code_falls_back_to_internal() -> None:
    entry = ec.lookup("NONSENSE")
    assert entry["code"] == "INTERNAL"


def test_format_cli_includes_title_and_recovery() -> None:
    msg = ec.format_cli(ErrorCode.DEAD_LETTER, detail="r-abc")
    assert "Request failed after retries" in msg
    assert "r-abc" in msg
    assert "slm queue dlq" in msg


def test_format_cli_works_with_string_code() -> None:
    msg = ec.format_cli("RATE_LIMITED")
    assert "Rate limited" in msg
