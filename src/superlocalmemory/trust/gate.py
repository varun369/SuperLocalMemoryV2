# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Trust Gate (Pre-Operation Checks).

Enforces minimum trust thresholds before allowing write/delete operations.
Read operations always pass but are logged for audit purposes.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from superlocalmemory.trust.scorer import TrustScorer

logger = logging.getLogger(__name__)


class TrustError(PermissionError):
    """Raised when an agent fails a trust check.

    Attributes:
        agent_id: The agent that failed the check.
        trust_score: The agent's current trust score.
        threshold: The minimum required trust score.
        operation: The operation that was attempted.
    """

    def __init__(
        self,
        agent_id: str,
        trust_score: float,
        threshold: float,
        operation: str,
    ) -> None:
        self.agent_id = agent_id
        self.trust_score = trust_score
        self.threshold = threshold
        self.operation = operation
        super().__init__(
            f"Agent '{agent_id}' trust {trust_score:.3f} below "
            f"{operation} threshold {threshold:.3f}"
        )


class TrustGate:
    """Pre-operation trust checks.

    Operations are gated by minimum trust thresholds:
    - write: agent must have trust >= write_threshold (default 0.3)
    - delete: agent must have trust >= delete_threshold (default 0.5)
    - read: always passes (logged for audit trail)

    Raises TrustError if the agent's trust is too low.
    """

    def __init__(
        self,
        scorer: TrustScorer,
        write_threshold: float = 0.3,
        delete_threshold: float = 0.5,
    ) -> None:
        if write_threshold < 0 or write_threshold > 1:
            raise ValueError("write_threshold must be in [0, 1]")
        if delete_threshold < 0 or delete_threshold > 1:
            raise ValueError("delete_threshold must be in [0, 1]")

        self._scorer = scorer
        self._write_threshold = write_threshold
        self._delete_threshold = delete_threshold

    @property
    def write_threshold(self) -> float:
        return self._write_threshold

    @property
    def delete_threshold(self) -> float:
        return self._delete_threshold

    def check_write(self, agent_id: str, profile_id: str) -> None:
        """Check if agent is trusted enough to write.

        Raises:
            TrustError: If agent trust is below write_threshold.
        """
        score = self._scorer.get_agent_trust(agent_id, profile_id)
        logger.debug(
            "trust gate write: agent=%s trust=%.3f threshold=%.3f",
            agent_id, score, self._write_threshold,
        )
        if score < self._write_threshold:
            raise TrustError(
                agent_id, score, self._write_threshold, "write"
            )

    def check_delete(self, agent_id: str, profile_id: str) -> None:
        """Check if agent is trusted enough to delete.

        Delete requires higher trust than write because it is destructive.

        Raises:
            TrustError: If agent trust is below delete_threshold.
        """
        score = self._scorer.get_agent_trust(agent_id, profile_id)
        logger.debug(
            "trust gate delete: agent=%s trust=%.3f threshold=%.3f",
            agent_id, score, self._delete_threshold,
        )
        if score < self._delete_threshold:
            raise TrustError(
                agent_id, score, self._delete_threshold, "delete"
            )

    def check_read(self, agent_id: str, profile_id: str) -> None:
        """Read check — always passes. Logged for audit trail.

        Reads are never blocked because denying read access could break
        agent functionality. However, logging read access enables
        anomaly detection and compliance auditing.
        """
        score = self._scorer.get_agent_trust(agent_id, profile_id)
        logger.debug(
            "trust gate read (always pass): agent=%s trust=%.3f",
            agent_id, score,
        )
