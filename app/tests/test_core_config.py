from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest
from fastapi import FastAPI

from app.core_config import (
    CoreConfigLoadError,
    GENERATION_CONFIG_PATH,
    load_fpg_core_config,
    reload_fpg_core_config,
)


def test_packaged_core_configuration_is_complete_and_immutable() -> None:
    config = load_fpg_core_config()

    assert config.schema_version == 1
    assert config.project_units_per_meter == 10
    assert config.preprocessing.room_sizes
    assert config.floor_plan_solver.initial.name == "initial_generation"
    with pytest.raises(FrozenInstanceError):
        config.project_units_per_meter = 20  # type: ignore[misc]
    with pytest.raises(TypeError):
        config.floor_plan_solver.initial.hard_constraints[0].settings[
            "min_ratio"
        ] = 1.0  # type: ignore[index]


def test_unknown_generation_configuration_fields_are_rejected(tmp_path) -> None:
    payload = json.loads(GENERATION_CONFIG_PATH.read_text(encoding="utf-8"))
    payload["unknown"] = True
    path = tmp_path / "generation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CoreConfigLoadError):
        load_fpg_core_config(generation_path=path)


def test_failed_reload_keeps_previous_configuration(tmp_path) -> None:
    app = FastAPI()
    previous = reload_fpg_core_config(app)
    path = tmp_path / "invalid.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(CoreConfigLoadError):
        reload_fpg_core_config(app, generation_path=path)

    assert app.state.fpg_core_config is previous
