"""Shared dataclasses for the path simulation module.

No imports from outside this package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class PathResult:
    """One simulated path between two anchor points."""

    label: str
    coords: List[Tuple[float, float]]  # smoothed world coords (cm)
    color: str  # hex colour for plotting
    is_public: bool = False  # True for Entry→Kitchen / Entry→Bathroom paths


@dataclass
class PathScoreResult:
    """Output of the path-simulation scoring step (0–100 total)."""

    total_score: float

    # Sub-scores (raw, before weighting)
    circulation_efficiency: float  # 0–30
    privacy_score: float  # 0–25
    hallway_utility: float  # 0–25
    furniture_flexibility: float  # 0–20

    paths: List[PathResult] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    plot_path: str = ""
    error: str = ""
