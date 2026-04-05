# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Profile Management.

First-class profile isolation. Every memory, fact, entity, and learning
record is scoped by profile_id. Profiles are persisted in profiles.json
with atomic writes and instant switching (config-only, zero data movement).

Ported from V2.8 columnar profile isolation pattern.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from superlocalmemory.core.config import DEFAULT_PROFILES_FILE
from superlocalmemory.storage.models import Mode, Profile

logger = logging.getLogger(__name__)

_VALID_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,49}$")
_MAX_NAME_LEN = 50
_RESERVED = "default"


def _validate_name(name: str) -> None:
    """Alphanumeric + dash + underscore, 1-50 chars, starts alphanumeric."""
    if not name or len(name) > _MAX_NAME_LEN:
        raise ValueError(f"Profile name must be 1-{_MAX_NAME_LEN} chars, got {len(name)}.")
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            f"Invalid profile name '{name}'. "
            "Must start with alphanumeric, then alphanumeric / dash / underscore."
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid() -> str:
    return uuid.uuid4().hex[:16]


def _evolve(prof: Profile, **overrides: Any) -> Profile:
    """Return a new Profile with selected fields replaced (frozen dataclass)."""
    base = asdict(prof)
    base.update(overrides)
    base["mode"] = Mode(base["mode"]) if isinstance(base["mode"], str) else base["mode"]
    return Profile(**base)


class ProfileManager:
    """Thread-safe profile manager with atomic JSON persistence.

    Stores profile metadata in ``profiles.json`` inside *base_dir*.
    Profiles are isolated at the DB column level (WHERE profile_id = ?).
    Switching is instant — only the active pointer changes.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._base_dir / DEFAULT_PROFILES_FILE
        self._profiles: dict[str, Profile] = {}
        self._active_name: str = _RESERVED
        self._on_switch: Callable[[Profile], None] | None = None
        self._load()

    # -- Persistence (atomic write via tempfile + rename) ------------------

    def _load(self) -> None:
        """Load profiles.json or bootstrap with the default profile."""
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._active_name = raw.get("active", _RESERVED)
            for entry in raw.get("profiles", []):
                mode = Mode(entry["mode"]) if "mode" in entry else Mode.A
                prof = Profile(
                    profile_id=entry["profile_id"],
                    name=entry["name"],
                    description=entry.get("description", ""),
                    personality=entry.get("personality", ""),
                    mode=mode,
                    created_at=entry.get("created_at", _now()),
                    last_used=entry.get("last_used"),
                    config=entry.get("config", {}),
                )
                self._profiles[prof.name] = prof
        if _RESERVED not in self._profiles:
            self._profiles[_RESERVED] = Profile(
                profile_id=_pid(), name=_RESERVED,
                description="Default memory profile", mode=Mode.A,
                created_at=_now(),
            )
            self._save()

    def _save(self) -> None:
        """Atomic write: temp file in same dir, then rename."""
        data = json.dumps(
            {"active": self._active_name,
             "profiles": [asdict(p) for p in self._profiles.values()]},
            indent=2, ensure_ascii=False,
        )
        fd, tmp = tempfile.mkstemp(dir=str(self._base_dir), suffix=".tmp")
        try:
            Path(tmp).write_text(data, encoding="utf-8")
            Path(tmp).replace(self._path)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    # -- Event hook --------------------------------------------------------

    @property
    def on_profile_switch(self) -> Callable[[Profile], None] | None:
        return self._on_switch

    @on_profile_switch.setter
    def on_profile_switch(self, cb: Callable[[Profile], None] | None) -> None:
        self._on_switch = cb

    # -- CRUD --------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        description: str = "",
        personality: str = "",
        mode: Mode = Mode.A,
        config: dict[str, Any] | None = None,
    ) -> Profile:
        """Create a new profile. Raises ValueError on duplicate or bad name."""
        _validate_name(name)
        if name in self._profiles:
            raise ValueError(f"Profile '{name}' already exists.")
        profile = Profile(
            profile_id=_pid(), name=name, description=description,
            personality=personality, mode=mode,
            created_at=_now(), config=config or {},
        )
        self._profiles[name] = profile
        self._save()
        logger.info("Created profile '%s' (id=%s, mode=%s)", name, profile.profile_id, mode.value)
        return profile

    def get_profile(self, name: str) -> Profile | None:
        """Return profile by name, or None if not found."""
        return self._profiles.get(name)

    def get_active_profile(self) -> Profile:
        """Return the currently active profile."""
        return self._profiles.get(self._active_name) or self._profiles[_RESERVED]

    def switch_profile(self, name: str) -> Profile:
        """Instant switch — config-only, zero data movement."""
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' does not exist.")
        self._active_name = name
        updated = _evolve(self._profiles[name], last_used=_now())
        self._profiles[name] = updated
        self._save()
        logger.info("Switched to profile '%s'", name)
        if self._on_switch is not None:
            self._on_switch(updated)
        return updated

    def list_profiles(self) -> list[Profile]:
        """All profiles sorted by name (default first)."""
        profs = list(self._profiles.values())
        profs.sort(key=lambda p: (p.name != _RESERVED, p.name))
        return profs

    def delete_profile(self, name: str) -> None:
        """Delete a profile. Cannot delete 'default'. Data stays in DB."""
        if name == _RESERVED:
            raise ValueError("Cannot delete the default profile.")
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' does not exist.")
        del self._profiles[name]
        if self._active_name == name:
            self._active_name = _RESERVED
            logger.info("Active profile deleted — fell back to 'default'.")
        self._save()
        logger.info("Deleted profile '%s'. Associated data remains in DB.", name)

    def rename_profile(self, old_name: str, new_name: str) -> None:
        """Rename a profile. Cannot rename 'default'."""
        if old_name == _RESERVED:
            raise ValueError("Cannot rename the default profile.")
        _validate_name(new_name)
        if old_name not in self._profiles:
            raise KeyError(f"Profile '{old_name}' does not exist.")
        if new_name in self._profiles:
            raise ValueError(f"Profile '{new_name}' already exists.")
        old = self._profiles.pop(old_name)
        self._profiles[new_name] = _evolve(old, name=new_name)
        if self._active_name == old_name:
            self._active_name = new_name
        self._save()
        logger.info("Renamed profile '%s' -> '%s'", old_name, new_name)

    def update_profile(self, name: str, **kwargs: Any) -> Profile:
        """Update mutable fields: description, personality, mode, config."""
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' does not exist.")
        allowed = {"description", "personality", "mode", "config"}
        overrides = {k: v for k, v in kwargs.items() if k in allowed}
        updated = _evolve(self._profiles[name], **overrides)
        self._profiles[name] = updated
        self._save()
        logger.info("Updated profile '%s'", name)
        return updated

    def export_profile(self, name: str) -> dict[str, Any]:
        """Export profile metadata as a plain dict (for backup / migration)."""
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' does not exist.")
        return asdict(self._profiles[name])
