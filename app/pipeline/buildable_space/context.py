from __future__ import annotations

from dataclasses import dataclass, replace

from app.core.execution import ExecutionContext


@dataclass(frozen=True, slots=True)
class BuildableSpaceContext:
    execution_context: ExecutionContext
    reference_profile: str | None = None

    def with_reference_profile(self, profile: str) -> "BuildableSpaceContext":
        return replace(self, reference_profile=profile)
