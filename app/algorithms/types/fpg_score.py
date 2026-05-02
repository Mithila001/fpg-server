from dataclasses import dataclass
from typing import Any, List, Optional, Dict


@dataclass
class CheckResult:
    """Represents an individual validation check."""

    name: str
    passed: bool
    violations: List[str]


@dataclass
class ScoringDiagnostics:
    """Detailed geometric and process metadata."""

    executed_checks: int
    passed_checks: int
    adjacency: Dict[str, Any]
    empty_space: Dict[str, Any]
    inward_pocket: Dict[str, Any]
    critical_plot_path: Optional[str] = None


@dataclass
class ScoreManagerResult:
    """The successful return object from score_manager."""

    critical_score: float
    checks: List[CheckResult]
    critical_violations: List[str]
    diagnostics: ScoringDiagnostics
