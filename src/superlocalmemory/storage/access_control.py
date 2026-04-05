# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Attribute-Based Access Control (ABAC).

Profile-scoped access control. Ensures memory operations
respect profile boundaries and permission rules.
Ported from V2.8 with enhancements.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Memory operation permissions."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"
    ADMIN = "admin"  # Can manage profiles, access control


class AccessLevel(str, Enum):
    """Access level tiers."""

    OWNER = "owner"        # Full access to profile
    AGENT = "agent"        # Read + write, no delete/export
    READONLY = "readonly"  # Read only
    NONE = "none"          # No access


# Permission matrix per access level
_PERMISSIONS: dict[AccessLevel, frozenset[Permission]] = {
    AccessLevel.OWNER: frozenset(Permission),
    AccessLevel.AGENT: frozenset({Permission.READ, Permission.WRITE}),
    AccessLevel.READONLY: frozenset({Permission.READ}),
    AccessLevel.NONE: frozenset(),
}


@dataclass(frozen=True)
class AccessGrant:
    """Grant of access to a profile for an agent/user."""

    subject_id: str            # Agent ID or user ID
    profile_id: str            # Which profile
    access_level: AccessLevel
    granted_by: str = ""
    granted_at: str = ""


@dataclass
class AccessController:
    """Attribute-based access control for memory operations.

    Enforces profile isolation:
    - Each agent/user has an access level per profile
    - Operations check permissions before execution
    - Default: profile creator = OWNER, others = NONE
    """

    # In-memory grant store (persisted via profiles.json or DB)
    _grants: dict[tuple[str, str], AccessGrant] = field(default_factory=dict)

    def grant_access(
        self,
        subject_id: str,
        profile_id: str,
        access_level: AccessLevel,
        granted_by: str = "system",
    ) -> AccessGrant:
        """Grant access to a profile for a subject."""
        from datetime import UTC, datetime

        grant = AccessGrant(
            subject_id=subject_id,
            profile_id=profile_id,
            access_level=access_level,
            granted_by=granted_by,
            granted_at=datetime.now(UTC).isoformat(),
        )
        self._grants[(subject_id, profile_id)] = grant
        logger.info(
            "Granted %s access to profile '%s' for '%s'",
            access_level.value,
            profile_id,
            subject_id,
        )
        return grant

    def revoke_access(self, subject_id: str, profile_id: str) -> None:
        """Revoke access to a profile."""
        key = (subject_id, profile_id)
        if key in self._grants:
            del self._grants[key]
            logger.info(
                "Revoked access to profile '%s' for '%s'",
                profile_id,
                subject_id,
            )

    def check_permission(
        self,
        subject_id: str,
        profile_id: str,
        permission: Permission,
    ) -> bool:
        """Check if subject has permission on profile.

        Default behavior: if no grant exists, deny access.
        Exception: "default" profile allows READ for all subjects.
        """
        grant = self._grants.get((subject_id, profile_id))

        if grant is None:
            # Default profile allows read for everyone
            if profile_id == "default" and permission == Permission.READ:
                return True
            return False

        allowed = _PERMISSIONS.get(grant.access_level, frozenset())
        return permission in allowed

    def require_permission(
        self,
        subject_id: str,
        profile_id: str,
        permission: Permission,
    ) -> None:
        """Raise if subject lacks permission. Use as a guard."""
        if not self.check_permission(subject_id, profile_id, permission):
            raise PermissionError(
                f"Subject '{subject_id}' lacks {permission.value} "
                f"permission on profile '{profile_id}'"
            )

    def get_access_level(
        self, subject_id: str, profile_id: str
    ) -> AccessLevel:
        """Get the access level for a subject on a profile."""
        grant = self._grants.get((subject_id, profile_id))
        return grant.access_level if grant else AccessLevel.NONE

    def list_grants(self, profile_id: str | None = None) -> list[AccessGrant]:
        """List all grants, optionally filtered by profile."""
        grants = list(self._grants.values())
        if profile_id is not None:
            grants = [g for g in grants if g.profile_id == profile_id]
        return grants

    def export_grants(self) -> list[dict]:
        """Export all grants as dicts for persistence."""
        return [
            {
                "subject_id": g.subject_id,
                "profile_id": g.profile_id,
                "access_level": g.access_level.value,
                "granted_by": g.granted_by,
                "granted_at": g.granted_at,
            }
            for g in self._grants.values()
        ]

    def import_grants(self, data: list[dict]) -> None:
        """Import grants from persisted data."""
        for item in data:
            self.grant_access(
                subject_id=item["subject_id"],
                profile_id=item["profile_id"],
                access_level=AccessLevel(item["access_level"]),
                granted_by=item.get("granted_by", "import"),
            )
