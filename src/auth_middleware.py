#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Optional API Key Authentication
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Opt-in API key authentication for dashboard and API endpoints.
When ~/.claude-memory/api_key file exists, write endpoints require
X-SLM-API-Key header. Read endpoints remain open for backward compatibility.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".claude-memory"
API_KEY_FILE = MEMORY_DIR / "api_key"


def _load_api_key_hash() -> Optional[str]:
    """Load API key hash from file. Returns None if auth is not configured."""
    if not API_KEY_FILE.exists():
        return None
    try:
        key = API_KEY_FILE.read_text().strip()
        if not key:
            return None
        return hashlib.sha256(key.encode()).hexdigest()
    except Exception as e:
        logger.warning("Failed to load API key: %s", e)
        return None


def check_api_key(request_headers: dict, is_write: bool = False) -> bool:
    """
    Check if request is authorized.

    Returns True if:
    - No API key file exists (auth not configured — backward compatible)
    - Request is a read operation (reads always allowed)
    - Request has valid X-SLM-API-Key header matching the key file
    """
    key_hash = _load_api_key_hash()

    # No key file = auth not configured = allow all (backward compat)
    if key_hash is None:
        return True

    # Read operations always allowed
    if not is_write:
        return True

    # Write operations require valid key
    provided_key = request_headers.get("x-slm-api-key", "")
    if not provided_key:
        return False

    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return provided_hash == key_hash
