# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Provenance Tracking.

Records who/what created each memory and how.
V1 had provenance as WRITE-ONLY (stored but never read).
Innovation wires reads into trust scoring and compliance audit.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from superlocalmemory.storage.models import ProvenanceRecord

logger = logging.getLogger(__name__)


class ProvenanceTracker:
    """Track provenance of all stored facts.

    Every fact gets a provenance record at creation time.
    Provenance feeds into:
    - Trust scoring (sources with high-quality provenance get trust boost)
    - Compliance audit (GDPR right-to-know: who stored what data?)
    - Debugging (which extraction pipeline created this fact?)
    """

    def __init__(self, db) -> None:
        self._db = db

    def record(
        self,
        fact_id: str,
        profile_id: str,
        source_type: str,
        source_id: str = "",
        created_by: str = "",
    ) -> ProvenanceRecord:
        """Record provenance for a newly stored fact.

        Args:
            fact_id: The fact being tracked.
            profile_id: Active profile.
            source_type: "conversation", "import", "consolidation", "migration".
            source_id: Session ID, import batch ID, etc.
            created_by: Agent ID or user identifier.
        """
        record = ProvenanceRecord(
            profile_id=profile_id,
            fact_id=fact_id,
            source_type=source_type,
            source_id=source_id,
            created_by=created_by,
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._db.execute(
            "INSERT INTO provenance "
            "(provenance_id, profile_id, fact_id, source_type, source_id, "
            "created_by, timestamp) VALUES (?,?,?,?,?,?,?)",
            (record.provenance_id, record.profile_id, record.fact_id,
             record.source_type, record.source_id, record.created_by,
             record.timestamp),
        )
        return record

    def get_provenance(self, fact_id: str, profile_id: str) -> ProvenanceRecord | None:
        """Get provenance for a specific fact."""
        rows = self._db.execute(
            "SELECT * FROM provenance WHERE fact_id = ? AND profile_id = ?",
            (fact_id, profile_id),
        )
        if not rows:
            return None
        d = dict(rows[0])
        return ProvenanceRecord(
            provenance_id=d["provenance_id"],
            profile_id=d["profile_id"],
            fact_id=d["fact_id"],
            source_type=d["source_type"],
            source_id=d.get("source_id", ""),
            created_by=d.get("created_by", ""),
            timestamp=d["timestamp"],
        )

    def get_facts_by_source(
        self, source_type: str, profile_id: str, limit: int = 100
    ) -> list[ProvenanceRecord]:
        """Get all facts from a specific source type."""
        rows = self._db.execute(
            "SELECT * FROM provenance WHERE source_type = ? AND profile_id = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (source_type, profile_id, limit),
        )
        return [self._row_to_record(r) for r in rows]

    def get_provenance_for_profile(
        self, profile_id: str, limit: int = 100
    ) -> list[ProvenanceRecord]:
        """Get all provenance records for a profile (compliance audit)."""
        rows = self._db.execute(
            "SELECT * FROM provenance WHERE profile_id = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (profile_id, limit),
        )
        return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row) -> ProvenanceRecord:
        d = dict(row)
        return ProvenanceRecord(
            provenance_id=d["provenance_id"],
            profile_id=d["profile_id"],
            fact_id=d["fact_id"],
            source_type=d["source_type"],
            source_id=d.get("source_id", ""),
            created_by=d.get("created_by", ""),
            timestamp=d["timestamp"],
        )
