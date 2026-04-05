# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Engine lifecycle hooks -- pre/post operation dispatch.

Pre-hooks are synchronous and can reject operations (raise exceptions).
Post-hooks are fire-and-forget -- errors are logged, never propagated.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HookRegistry:
    """Registry for engine lifecycle hooks.

    Usage:
        registry = HookRegistry()
        registry.register_pre("store", abac_check)
        registry.register_pre("store", trust_gate_check)
        registry.register_post("store", audit_log)
        registry.register_post("store", event_bus_publish)

        # In engine.store():
        registry.run_pre("store", context)   # raises if any pre-hook fails
        # ... core operation ...
        registry.run_post("store", context)  # never raises
    """

    def __init__(self) -> None:
        self._pre: dict[str, list[Callable]] = {}
        self._post: dict[str, list[Callable]] = {}

    def register_pre(self, operation: str, hook: Callable[[dict[str, Any]], None]) -> None:
        """Register a pre-operation hook. Hook receives context dict.
        Hook can raise to reject the operation."""
        self._pre.setdefault(operation, []).append(hook)

    def register_post(self, operation: str, hook: Callable[[dict[str, Any]], None]) -> None:
        """Register a post-operation hook. Hook receives context dict.
        Errors are logged, never propagated."""
        self._post.setdefault(operation, []).append(hook)

    def run_pre(self, operation: str, context: dict[str, Any]) -> None:
        """Run all pre-hooks for an operation. Raises on first failure."""
        for hook in self._pre.get(operation, []):
            hook(context)  # Let exceptions propagate -- this is intentional

    def run_post(self, operation: str, context: dict[str, Any]) -> None:
        """Run all post-hooks for an operation. Errors logged, never raised."""
        for hook in self._post.get(operation, []):
            try:
                hook(context)
            except Exception as exc:
                logger.debug("Post-hook error (%s): %s", operation, exc)

    def clear(self) -> None:
        """Remove all hooks. Useful for testing."""
        self._pre.clear()
        self._post.clear()
