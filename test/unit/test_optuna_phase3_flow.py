from __future__ import annotations

from types import SimpleNamespace

from app.algorithms.fpg_rooms.fpg_optuna.runner import (
    _weighted_graph_score,
    _weighted_solver_score,
    run_optuna_optimization,
)
from app.algorithms.fpg_rooms.fpg_optuna.types import FpgEvaluationResult
from app.algorithms.types import ConfigData, FpgRequirements


class _Node:
    def __init__(self, name: str, room_type: str, x: float, y: float) -> None:
        self.name = name
        self.room_type = room_type
        self.x = x
        self.y = y


class _GraphResult:
    def __init__(
        self, total_score: float, usable_layout: bool, nodes: list[_Node]
    ) -> None:
        self.score = SimpleNamespace(
            total_score=total_score, usable_layout=usable_layout
        )
        self.nodes = nodes


def _requirements() -> FpgRequirements:
    config = ConfigData(
        min_coverage=0.4,
        max_aspect_ratio=16.0,
        min_aspect_ratio=0.0,
        floor_plan_width=120,
        floor_plan_height=120,
        hallway_count=1,
    )
    return FpgRequirements(rooms=[], config=config, relation_constraints=[])


def test_weighted_scores_are_clamped() -> None:
    assert _weighted_graph_score(90.0) == 90.0
    assert _weighted_graph_score(200.0) == 90.0
    assert _weighted_graph_score(-20.0) == 0.0

    assert _weighted_solver_score(100.0) == 10.0
    assert _weighted_solver_score(250.0) == 10.0
    assert _weighted_solver_score(-5.0) == 0.0


def test_optuna_graph_unusable_skips_inner_solver(monkeypatch) -> None:
    base = _requirements()
    evaluator_calls = {"count": 0}

    def fake_graph_layout(*args, **kwargs):  # noqa: ANN002, ANN003
        return _GraphResult(total_score=50.0, usable_layout=False, nodes=[])

    def fake_evaluator(requirements, verbose):  # noqa: ANN001
        evaluator_calls["count"] += 1
        return FpgEvaluationResult(
            solved=True,
            solution=[],
            score_report=SimpleNamespace(total_score=99.0),
            status="OK",
            message="should not be used",
        )

    monkeypatch.setattr(
        "app.algorithms.fpg_rooms.fpg_optuna.runner.run_graph_layout",
        fake_graph_layout,
    )

    result = run_optuna_optimization(
        base_requirements=base,
        evaluator=fake_evaluator,
        n_trials=1,
        study_name="phase3_graph_unusable_test",
        storage=None,
    )

    assert evaluator_calls["count"] == 0
    assert result.best_value == _weighted_graph_score(50.0)


def test_optuna_uses_inner_solver_when_graph_usable(monkeypatch) -> None:
    base = _requirements()
    evaluator_calls = {"count": 0, "has_hints": False}

    def fake_graph_layout(*args, **kwargs):  # noqa: ANN002, ANN003
        return _GraphResult(
            total_score=80.0,
            usable_layout=True,
            nodes=[_Node("livingRoom1", "livingRoom", 12.4, 10.6)],
        )

    def fake_evaluator(requirements, verbose):  # noqa: ANN001
        evaluator_calls["count"] += 1
        evaluator_calls["has_hints"] = len(requirements.initial_point_hints) > 0
        return FpgEvaluationResult(
            solved=True,
            solution=[],
            score_report=SimpleNamespace(total_score=90.0),
            status="OPTIMAL",
            message="ok",
        )

    monkeypatch.setattr(
        "app.algorithms.fpg_rooms.fpg_optuna.runner.run_graph_layout",
        fake_graph_layout,
    )

    result = run_optuna_optimization(
        base_requirements=base,
        evaluator=fake_evaluator,
        n_trials=1,
        study_name="phase3_graph_usable_test",
        storage=None,
    )

    expected = _weighted_graph_score(80.0) + _weighted_solver_score(90.0)
    assert evaluator_calls["count"] == 1
    assert evaluator_calls["has_hints"] is True
    assert result.best_value == expected


def test_optuna_samples_explicit_coordinates(monkeypatch) -> None:
    base = _requirements()
    captured = {"explicit_positions": None}

    def fake_graph_layout(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["explicit_positions"] = kwargs.get("explicit_positions")
        return _GraphResult(total_score=50.0, usable_layout=False, nodes=[])

    def fake_evaluator(requirements, verbose):  # noqa: ANN001
        return FpgEvaluationResult(
            solved=False,
            solution=[],
            score_report=None,
            status="SKIPPED",
            message="not used",
        )

    monkeypatch.setattr(
        "app.algorithms.fpg_rooms.fpg_optuna.runner.run_graph_layout",
        fake_graph_layout,
    )

    run_optuna_optimization(
        base_requirements=base,
        evaluator=fake_evaluator,
        n_trials=1,
        study_name="phase3_coordinate_sampling_test",
        storage=None,
    )

    assert isinstance(captured["explicit_positions"], dict)
    assert len(captured["explicit_positions"]) >= 1
