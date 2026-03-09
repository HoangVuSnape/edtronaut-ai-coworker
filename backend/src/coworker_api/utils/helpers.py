"""
Utility Helpers for Edtronaut AI Coworker.

General-purpose utilities used across layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_id() -> str:
    """Generate a new UUID v4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max_length, appending suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
