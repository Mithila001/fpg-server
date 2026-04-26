from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from app.algorithms.fpg_rooms.fpg_graph.api import run_graph_layout
from app.algorithms.types.solvers import GraphPhysicsConfig


def _build_requirements() -> SimpleNamespace:
    rooms = [
        SimpleNamespace(
            name="livingRoom1",
            type="livingRoom",
            min_w=20,
            max_w=20,
            min_h=20,
            max_h=20,
        ),
        SimpleNamespace(
            name="kitchen1",
            type="kitchen",
            min_w=12,
            max_w=12,
            min_h=12,
            max_h=12,
        ),
    ]
    config = SimpleNamespace(
        floor_plan_width=100, floor_plan_height=120, hallway_count=0
    )
    return SimpleNamespace(rooms=rooms, relation_constraints=[], config=config)


def test_staged_sizing_restores_original_room_radii() -> None:
    requirements = _build_requirements()

    result = run_graph_layout(
        requirements=cast(Any, requirements),
        explicit_positions={"room_0": (40.0, 40.0), "room_1": (70.0, 70.0)},
        physics_config=GraphPhysicsConfig(
            use_staged_node_sizing=True,
            staged_uniform_radius=3.0,
            staged_phase1_iterations=8,
            staged_phase2_iterations=8,
        ),
    )

    radii = {node.id: node.radius for node in result.nodes}

    assert radii["room_0"] == 10.0
    assert radii["room_1"] == 6.0
    assert result.diagnostics["staged_sizing_used"] is True
    assert int(result.diagnostics["stage1_iterations_run"]) > 0
    assert int(result.diagnostics["stage2_iterations_run"]) > 0


def test_non_staged_layout_keeps_staged_diagnostics_disabled() -> None:
    requirements = _build_requirements()

    result = run_graph_layout(
        requirements=cast(Any, requirements),
        explicit_positions={"room_0": (30.0, 30.0), "room_1": (60.0, 80.0)},
        physics_config=GraphPhysicsConfig(iterations=5),
    )

    assert result.diagnostics["staged_sizing_used"] is False
    assert int(result.diagnostics["stage1_iterations_run"]) == 0
    assert int(result.diagnostics["stage2_iterations_run"]) == 0
