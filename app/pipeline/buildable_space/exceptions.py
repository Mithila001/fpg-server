from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from fpg_core.types import (
    BuildableSpaceErrorCode,
    BuildableSpaceStage,
)


class ReferenceDataError(Exception):
    pass


class BuildableSpacePipelineError(Exception):
    def __init__(
        self,
        stage: BuildableSpaceStage,
        code: BuildableSpaceErrorCode,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message
        self.details = MappingProxyType(dict(details or {}))
