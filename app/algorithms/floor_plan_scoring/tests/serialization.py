from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


def to_json_compatible(value: Any) -> Any:
    """Convert scoring dataclasses and enums into stable JSON-compatible data."""

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_compatible(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [to_json_compatible(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(to_json_compatible(item) for item in value)
    return value


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_json_compatible(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
