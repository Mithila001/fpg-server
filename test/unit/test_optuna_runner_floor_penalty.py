import time

from app.algorithms.fpg_rooms.fpg_optuna.runner import run_optuna_optimization
from app.algorithms.fpg_rooms.fpg_optuna.types import FpgEvaluationResult
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements, RoomData


def test_run_optuna_optimization_penalizes_infeasible_floor_bounds():
    requirements = FpgRequirements(
        rooms=[
            RoomData(name="Bedroom", type="bedroom", min_w=20, min_h=20, max_w=25, max_h=25),
        ],
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=30,
            floor_plan_height=30,
            hallway_count=0,
        ),
        relation_constraints=[],
    )

    calls: list[int] = []

    def evaluator(_: FpgRequirements, __: bool) -> FpgEvaluationResult:
        calls.append(1)
        return FpgEvaluationResult(
            solved=True,
            solution=[],
            score_report=None,
            status="unexpected",
            message="should not be called",
        )

    result = run_optuna_optimization(
        base_requirements=requirements,
        evaluator=evaluator,
        n_trials=1,
        study_name="test_optuna_floor_penalty",
        storage=None,
    )

    assert calls == []
    assert result.best_value == 0.0
    assert result.best_run is not None
    assert result.best_run.status == "floor_bounds_infeasible"
    assert result.best_run.solved is False


def test_run_optuna_optimization_penalizes_room_floor_intersection_conflict():
    requirements = FpgRequirements(
        rooms=[
            RoomData(name="Bedroom", type="bedroom", min_w=20, min_h=20, max_w=25, max_h=25),
        ],
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=16.0,
            min_aspect_ratio=0.0,
            floor_plan_width=30,
            floor_plan_height=30,
            hallway_count=0,
        ),
        relation_constraints=[],
    )

    calls: list[int] = []

    def evaluator(_: FpgRequirements, __: bool) -> FpgEvaluationResult:
        calls.append(1)
        return FpgEvaluationResult(
            solved=True,
            solution=[],
            score_report=None,
            status="unexpected",
            message="should not be called",
        )

    result = run_optuna_optimization(
        base_requirements=requirements,
        evaluator=evaluator,
        n_trials=1,
        study_name=f"test_optuna_floor_intersection_conflict_{time.time_ns()}",
        storage=None,
        floor_dimension_bounds={
            "min_floor_width": 10,
            "min_floor_height": 10,
            "max_floor_width": 10,
            "max_floor_height": 10,
        },
    )

    assert calls == []
    assert result.best_value == 0.0
    assert result.best_run is not None
    assert result.best_run.status == "mutate_requirements_infeasible"
    assert result.best_run.solved is False
