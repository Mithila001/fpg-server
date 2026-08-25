from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .exceptions import ArtifactSerializationError
from .models import JsonValue


def to_json_value(value: Any, *, _path: str = "$") -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactSerializationError(f"{_path} contains a non-finite float")
        return value
    if isinstance(value, Enum):
        return to_json_value(value.value, _path=_path)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, BaseModel):
        return to_json_value(value.model_dump(mode="json"), _path=_path)
    if is_dataclass(value) and not isinstance(value, type):
        return to_json_value(asdict(value), _path=_path)
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ArtifactSerializationError(f"{_path} has a non-string object key")
            result[key] = to_json_value(item, _path=f"{_path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [
            to_json_value(item, _path=f"{_path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, (set, frozenset)):
        return [
            to_json_value(item, _path=f"{_path}[]")
            for item in sorted(value, key=str)
        ]
    raise ArtifactSerializationError(
        f"{_path} contains unsupported value {type(value).__name__}"
    )
