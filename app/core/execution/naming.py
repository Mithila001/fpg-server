from __future__ import annotations

import re
from datetime import UTC, datetime

_INVALID = re.compile(r"[^a-z0-9_-]+")
_REPEATED_SEPARATOR = re.compile(r"[_-]{2,}")
_MAX_SLUG_LENGTH = 80


def normalize_slug(value: object, *, max_length: int = _MAX_SLUG_LENGTH) -> str:
    """Normalize one semantic name without allowing path traversal."""

    raw = str(value).strip().lower()
    if not raw or ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError("semantic names cannot be empty or contain path traversal")
    normalized = _INVALID.sub("_", raw.replace(" ", "_"))
    normalized = _REPEATED_SEPARATOR.sub("_", normalized).strip("._-")
    if not normalized:
        raise ValueError("semantic name has no filesystem-safe characters")
    return normalized[:max_length].rstrip("._-")


def timestamp_key(value: datetime) -> str:
    current = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return current.astimezone(UTC).strftime("%Y%m%dT%H%M%S.%fZ")[:-4] + "Z"


def flow_id_for(*, started_at: datetime, sequence: int = 1) -> str:
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise TypeError("sequence must be an integer")
    if sequence < 1:
        raise ValueError("sequence must be greater than zero")
    suffix = "" if sequence == 1 else f"-{sequence:02d}"
    return f"flow_{timestamp_key(started_at)}{suffix}"


def flow_directory_name(*, started_at: datetime, flow_id: str) -> str:
    expected_prefix = f"flow_{timestamp_key(started_at)}"
    if not flow_id.startswith(expected_prefix):
        raise ValueError("flow_id does not match flow_started_at")
    suffix = flow_id[len(expected_prefix) :]
    if suffix and not re.fullmatch(r"-\d{2,}", suffix):
        raise ValueError("flow_id has an invalid collision suffix")
    return f"{timestamp_key(started_at)}_flow{suffix}"
