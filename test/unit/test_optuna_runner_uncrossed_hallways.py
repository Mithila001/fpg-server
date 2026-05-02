from __future__ import annotations

from typing import Callable
from types import SimpleNamespace

from app.algorithms.fpg_rooms.fpg_optuna import runner
from app.algorithms.types import ConfigData, FpgRequirements, RoomData
from app.algorithms.types.fpg_score import ScoreManagerResult, ScoringDiagnostics
from app.algorithms.types.solvers import FpgEvaluationResult


class _FakeTrial:
    def __init__(self) -> None:
        self.number = 0
        self.user_attrs: dict[str, object] = {}
        self.params: dict[str, float] = {}
        self.value: float | None = None

    def set_user_attr(self, key: str, value: object) -> None:
        self.user_attrs[key] = value

    def suggest_float(
        self,
        name: str,
        low: float,
        high: float,
        step: float | None = None,
    ) -> float:
        fixed_values = {
            "livingRoom1_x": 20.0,
            "livingRoom1_y": 20.0,
            "hallway1_x": 40.0,
            "hallway1_y": 40.0,
            "hallway2_x": 60.0,
            "hallway2_y": 60.0,
        }
        value = fixed_values[name]
        self.params[name] = value
        return value


class _FakeStudy:
    def __init__(self, **kwargs: object) -> None:
        self.study_name = str(kwargs.get("study_name", "fake-study"))
        self.trials: list[_FakeTrial] = []
        self.best_trial: _FakeTrial | None = None
        self.best_value: float = 0.0
        self.best_params: dict[str, float] = {}
        self._stopped = False

    def optimize(
        self,
        objective,
        n_trials: int,
        callbacks: list[Callable[[object, _FakeTrial], None]],
    ) -> None:
        trial = _FakeTrial()
        trial.value = float(objective(trial))
        self.trials.append(trial)
        self.best_trial = trial
        self.best_value = float(trial.value or 0.0)
        self.best_params = dict(trial.params)
        for callback in callbacks:
            callback(self, trial)
        self._stopped = True

    def stop(self) -> None:
        self._stopped = True


def _build_requirements() -> FpgRequirements:
    rooms = [
        RoomData(
            name="livingRoom1",
            type="livingRoom",
            min_w=20,
            min_h=20,
            max_w=30,
            max_h=30,
        ),
    ]
    config = ConfigData(
        min_coverage=0.3,
        max_aspect_ratio=2.0,
        min_aspect_ratio=0.5,
        floor_plan_width=120.0,
        floor_plan_height=120.0,
    )
    return FpgRequirements(rooms=rooms, config=config)


def test_runner_filters_uncrossed_hallway_hints(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_score_optuna_layout(
        requirements, sampled_positions, *, save_debug_plots=False
    ):
        return SimpleNamespace(
            total_score=90.0,
            usable_layout=True,
            section_scores={
                "floor_plan_zones": 30.0,
                "outer_clearance": 20.0,
                "room_relations": 40.0,
            },
            diagnostics={
                "room_relations": {
                    "uncrossed_hallways": [
                        SimpleNamespace(name="hallway2", room_type="hallway"),
                    ]
                }
            },
        )

    def fake_evaluator(
        requirements: FpgRequirements, _debug: bool
    ) -> FpgEvaluationResult:
        captured["initial_point_hints"] = list(requirements.initial_point_hints or [])
        captured["hallway_count"] = requirements.config.hallway_count
        return FpgEvaluationResult(
            solved=True,
            status="SOLVED",
            message="ok",
            fpg_score_results=ScoreManagerResult(
                critical_score=95.0,
                checks=[],
                critical_violations=[],
                diagnostics=ScoringDiagnostics(
                    executed_checks=0,
                    passed_checks=0,
                    adjacency={},
                    empty_space={},
                    inward_pocket={},
                ),
            ),
        )

    monkeypatch.setattr(runner, "score_optuna_layout", fake_score_optuna_layout)
    monkeypatch.setattr(
        runner.optuna, "create_study", lambda **kwargs: _FakeStudy(**kwargs)
    )
    monkeypatch.setattr(runner, "OPTUNA_HALLWAY_COUNT", 2, raising=False)

    result = runner.run_optuna_optimization(
        base_requirements=_build_requirements(),
        evaluator=fake_evaluator,
        n_trials=1,
        study_name="unit-test-study",
    )

    assert result.best_run is not None
    hint_names = [hint["name"] for hint in captured["initial_point_hints"]]  # type: ignore[index]
    assert hint_names == ["livingRoom1", "hallway1"]
    assert "hallway2" not in hint_names
    assert captured["hallway_count"] == 1
