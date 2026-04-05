# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Rules engine for configurable auto-capture and auto-recall behavior."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RULES = {
    "auto_recall": {
        "enabled": True,
        "on_session_start": True,
        "on_every_prompt": False,
        "max_memories_injected": 10,
        "relevance_threshold": 0.3,
    },
    "auto_capture": {
        "enabled": True,
        "capture_decisions": True,
        "capture_bugs": True,
        "capture_preferences": True,
        "capture_session_summary": True,
        "min_confidence": 0.5,
    },
}


class RulesEngine:
    """Manage configurable rules for auto-capture and auto-recall."""

    def __init__(self, config: dict | None = None, config_path: Path | None = None):
        if config:
            self._rules = {**DEFAULT_RULES, **config}
        elif config_path and config_path.exists():
            data = json.loads(config_path.read_text())
            self._rules = {**DEFAULT_RULES, **data.get("rules", {})}
        else:
            self._rules = dict(DEFAULT_RULES)

    def should_capture(self, category: str, confidence: float) -> bool:
        """Check if a category should be captured based on rules."""
        capture_rules = self._rules.get("auto_capture", {})
        if not capture_rules.get("enabled", True):
            return False

        category_key = f"capture_{category}s" if not category.endswith("s") else f"capture_{category}"
        if not capture_rules.get(category_key, True):
            return False

        min_conf = capture_rules.get("min_confidence", 0.5)
        return confidence >= min_conf

    def should_recall(self, trigger: str) -> bool:
        """Check if auto-recall should fire for a trigger."""
        recall_rules = self._rules.get("auto_recall", {})
        if not recall_rules.get("enabled", True):
            return False

        if trigger == "session_start":
            return recall_rules.get("on_session_start", True)
        if trigger == "every_prompt":
            return recall_rules.get("on_every_prompt", False)

        return True

    def get_recall_config(self) -> dict:
        """Get auto-recall configuration."""
        return dict(self._rules.get("auto_recall", DEFAULT_RULES["auto_recall"]))

    def get_capture_config(self) -> dict:
        """Get auto-capture configuration."""
        return dict(self._rules.get("auto_capture", DEFAULT_RULES["auto_capture"]))

    def update_rule(self, section: str, key: str, value: Any) -> None:
        """Update a specific rule."""
        if section not in self._rules:
            self._rules[section] = {}
        self._rules[section][key] = value

    def save(self, config_path: Path) -> None:
        """Save rules to config file."""
        if config_path.exists():
            data = json.loads(config_path.read_text())
        else:
            data = {}
        data["rules"] = self._rules
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(data, indent=2))

    def to_dict(self) -> dict:
        """Export rules as dict."""
        return dict(self._rules)
