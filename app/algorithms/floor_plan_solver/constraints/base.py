from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import ModelContext

ConstraintSettings = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PenaltyTerm:
    name: str
    expression: Any
    multiplier: int = 1

    def __post_init__(self) -> None:
        if self.multiplier <= 0:
            raise ValueError("Penalty multiplier must be positive")


class HardConstraint(Protocol):
    key: str

    def apply(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> None:
        ...


class SoftConstraint(Protocol):
    key: str

    def build_penalties(
        self,
        context: ModelContext,
        settings: ConstraintSettings,
    ) -> tuple[PenaltyTerm, ...]:
        ...
