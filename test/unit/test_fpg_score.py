from app.algorithms.fpg_rooms.fpg_score import score_layout
from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements


def _base_requirements() -> FpgRequirements:
    return FpgRequirements(
        rooms=[],
        config=ConfigData(
            min_coverage=0.5,
            max_aspect_ratio=10.0,
            min_aspect_ratio=0.1,
            floor_plan_width=10.0,
            floor_plan_height=10.0,
            envelope_enabled=False,
        ),
    )


def test_score_layout_full_flow_scores_all_sections():
    requirements = _base_requirements()
    solution = [
        {"name": "A", "type": "room", "x": 0.0, "y": 0.0, "x_end": 5.0, "y_end": 10.0},
        {"name": "B", "type": "room", "x": 5.0, "y": 0.0, "x_end": 10.0, "y_end": 10.0},
    ]

    report = score_layout(solution, None, requirements)

    assert report.valid is True
    assert report.total_score == 100.0
    assert report.component_scores["critical"] == 25.0
    assert report.component_scores["room"] == 25.0
    assert report.component_scores["functional"] == 25.0
    assert report.component_scores["extra"] == 25.0
    assert report.hard_violations == []


def test_score_layout_critical_gate_failure_zeroes_other_sections():
    requirements = _base_requirements()
    solution = [
        {"name": "L", "type": "room", "x": 0.0, "y": 0.0, "x_end": 4.0, "y_end": 10.0},
        {"name": "R", "type": "room", "x": 6.0, "y": 0.0, "x_end": 10.0, "y_end": 10.0},
        {"name": "T", "type": "room", "x": 4.0, "y": 6.0, "x_end": 6.0, "y_end": 10.0},
        {"name": "B", "type": "room", "x": 4.0, "y": 0.0, "x_end": 6.0, "y_end": 4.0},
    ]

    report = score_layout(solution, None, requirements)

    assert report.valid is False
    assert report.component_scores["critical"] < 25.0
    assert report.component_scores["room"] == 0.0
    assert report.component_scores["functional"] == 0.0
    assert report.component_scores["extra"] == 0.0
    assert report.total_score == report.component_scores["critical"]
    assert any("Enclosed air gap" in v for v in report.hard_violations)


def test_score_layout_second_gate_blocks_functional_and_extra_when_below_40():
    requirements = _base_requirements()
    solution = [
        {"name": "A", "type": "room", "x": 0.0, "y": 0.0, "x_end": 2.0, "y_end": 2.0},
    ]

    report = score_layout(solution, None, requirements)

    assert report.valid is True
    assert report.component_scores["critical"] == 25.0
    assert report.component_scores["room"] < 15.0
    assert report.component_scores["functional"] == 0.0
    assert report.component_scores["extra"] == 0.0
    assert report.total_score < 40.0


def test_each_section_score_is_capped_at_25():
    requirements = _base_requirements()
    solution = [
        {"name": "A", "type": "room", "x": 0.0, "y": 0.0, "x_end": 5.0, "y_end": 10.0},
        {"name": "B", "type": "room", "x": 5.0, "y": 0.0, "x_end": 10.0, "y_end": 10.0},
    ]

    report = score_layout(solution, None, requirements)

    assert report.component_scores["critical"] <= 25.0
    assert report.component_scores["room"] <= 25.0
    assert report.component_scores["functional"] <= 25.0
    assert report.component_scores["extra"] <= 25.0
