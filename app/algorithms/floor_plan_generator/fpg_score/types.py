from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ScoreReport:
    """Scoring report for a solved floor plan."""

    valid: bool
    total_score: float
    component_scores: Dict[str, float] = field(default_factory=dict)
    hard_violations: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
