# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""User-facing strings for queue error codes."""

from __future__ import annotations

from typing import TypedDict

from superlocalmemory.core.error_envelope import ErrorCode


class ErrorEntry(TypedDict):
    code: str
    title: str
    cli_message: str
    recovery: list[str]
    exit_code: int


CATALOG: dict[str, ErrorEntry] = {
    ErrorCode.RATE_LIMITED.value: {
        "code": "RATE_LIMITED",
        "title": "Rate limited",
        "cli_message": "Too many recalls in the last second.",
        "recovery": [
            "Wait a moment and try again.",
            "For batch work, export SLM_RATE_LIMIT_PER_AGENT=50 and restart the daemon.",
        ],
        "exit_code": 3,
    },
    ErrorCode.QUEUE_FULL.value: {
        "code": "QUEUE_FULL",
        "title": "Queue is full",
        "cli_message": "The request queue cannot accept more work right now.",
        "recovery": [
            "Retry with backoff.",
            "Run: slm queue status",
        ],
        "exit_code": 5,
    },
    ErrorCode.TIMEOUT.value: {
        "code": "TIMEOUT",
        "title": "Timed out",
        "cli_message": "The recall did not finish in the allotted time.",
        "recovery": [
            "Retry.",
            "Run: slm doctor",
        ],
        "exit_code": 2,
    },
    ErrorCode.CANCELLED.value: {
        "code": "CANCELLED",
        "title": "Cancelled",
        "cli_message": "The request was cancelled before it completed.",
        "recovery": ["Re-issue the request if needed."],
        "exit_code": 6,
    },
    ErrorCode.DEAD_LETTER.value: {
        "code": "DEAD_LETTER",
        "title": "Request failed after retries",
        "cli_message": (
            "The request could not complete after the maximum number of "
            "attempts. Your query is preserved in the dead-letter queue."
        ),
        "recovery": [
            "Inspect: slm queue dlq",
            "Run: slm doctor",
        ],
        "exit_code": 4,
    },
    ErrorCode.DAEMON_DOWN.value: {
        "code": "DAEMON_DOWN",
        "title": "Daemon unreachable",
        "cli_message": "Cannot reach the SLM daemon.",
        "recovery": [
            "Start the daemon: slm daemon start",
            "Check status: slm daemon status",
        ],
        "exit_code": 7,
    },
    ErrorCode.INTERNAL.value: {
        "code": "INTERNAL",
        "title": "Internal error",
        "cli_message": "An unexpected internal error occurred.",
        "recovery": [
            "Run: slm doctor",
            "If the issue persists, file an issue with the log excerpt.",
        ],
        "exit_code": 8,
    },
}


def lookup(code: str | ErrorCode) -> ErrorEntry:
    key = code.value if isinstance(code, ErrorCode) else code
    if key not in CATALOG:
        return CATALOG[ErrorCode.INTERNAL.value]
    return CATALOG[key]


def format_cli(code: str | ErrorCode, detail: str | None = None) -> str:
    entry = lookup(code)
    lines = [f"\u2717 {entry['title']}"]
    lines.append(f"  {entry['cli_message']}")
    if detail:
        lines.append(f"  Detail: {detail}")
    if entry["recovery"]:
        lines.append("  Try:")
        for step in entry["recovery"]:
            lines.append(f"    - {step}")
    return "\n".join(lines)
