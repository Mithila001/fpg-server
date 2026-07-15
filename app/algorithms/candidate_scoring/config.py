from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from .types import EvaluatorCategory, EvaluatorKey


@dataclass(frozen=True, slots=True)
class EvaluatorRule:
    """Manager-owned configuration for one registered evaluator."""

    key: EvaluatorKey
    category: EvaluatorCategory
    enabled: bool = True
    order: int = 0
    weight: float = 1.0
    minimum_score: float | None = None
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "settings", MappingProxyType(dict(self.settings)))


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Configuration for the complete evaluator pipeline."""

    evaluator_rules: tuple[EvaluatorRule, ...]
    fail_fast_on_critical_failure: bool = True
    not_applicable_quality_contributes: bool = False
    raise_on_evaluator_error: bool = False
