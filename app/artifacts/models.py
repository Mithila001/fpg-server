from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from app.core.execution import ExecutionContext

from .enums import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactScope,
    FeatureKey,
    WriteMode,
)

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class ArtifactWriteRequest:
    feature: FeatureKey
    artifact_kind: ArtifactKind
    artifact_format: ArtifactFormat
    artifact_scope: ArtifactScope
    semantic_name: str
    execution_context: ExecutionContext | None = None
    write_mode: WriteMode = WriteMode.CREATE
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.artifact_scope is ArtifactScope.GLOBAL:
            if self.execution_context is not None:
                raise ValueError("global artifacts cannot have an execution context")
        elif self.execution_context is None:
            raise ValueError("flow-scoped artifacts require an execution context")


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    path: Path | None
    relative_path: str | None
    artifact_format: ArtifactFormat
    artifact_kind: ArtifactKind
    enabled: bool = True
