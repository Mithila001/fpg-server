from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    name: str
    room_type: str
    radius: float
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    synthesized: bool = False


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    weight: float = 1.0
    rule_kind: str = "relation"


@dataclass
class GraphBoundary:
    width: float
    height: float


@dataclass
class GraphPhysicsConfig:
    iterations: int = 300
    time_step: float = 0.12
    damping: float = 0.88
    spring_constant: float = 0.08
    repulsion_constant: float = 3500.0
    max_speed: float = 8.0
    convergence_epsilon: float = 0.08
    stable_steps_required: int = 8


@dataclass
class GraphConvergence:
    converged: bool
    iterations_run: int
    final_max_displacement: float


@dataclass
class GraphScoreBreakdown:
    adjacency_score: float
    blocked_penalty: float
    front_bonus: float
    total_score: float
    usable_layout: bool


@dataclass
class GraphLayoutResult:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    boundary: GraphBoundary
    convergence: GraphConvergence
    score: GraphScoreBreakdown
    diagnostics: dict[str, float | int | bool] = field(default_factory=dict)
