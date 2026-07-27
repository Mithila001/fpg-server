from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pipeline.buildable_space import (
    ReferenceDataError,
    clear_buildable_space_reference_data_cache,
    load_buildable_space_reference_data,
)


def test_packaged_reference_data_uses_mock_profile_and_project_scale() -> None:
    data = load_buildable_space_reference_data()

    assert data.active_profile.name == "mock_residential_v1"
    assert data.active_profile.status == "mock_non_regulatory"
    assert data.project_units_per_meter == 10
    assert data.usable_land_constraints.search_resolution == 5
    assert data.usable_land_constraints.maximum_sweep_lines == 1000


def test_invalid_reference_data_is_not_cached(tmp_path: Path) -> None:
    path = tmp_path / "reference.json"
    path.write_text("{}", encoding="utf-8")
    clear_buildable_space_reference_data_cache()
    with pytest.raises(ReferenceDataError):
        load_buildable_space_reference_data(path)

    packaged = load_buildable_space_reference_data()
    payload = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "data"
            / "buildable_space_reference_data.json"
        ).read_text(encoding="utf-8")
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    clear_buildable_space_reference_data_cache()
    assert load_buildable_space_reference_data(path) == packaged
