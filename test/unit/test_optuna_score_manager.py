from __future__ import annotations

from app.algorithms.fpg_optuna_score.optuna_score_manager import score_optuna_layout
from app.algorithms.fpg_optuna_score.score.room_relations import _build_graph
from app.algorithms.types import ConfigData, FpgRequirements, RoomData


def _build_requirements() -> FpgRequirements:
    rooms = [
        RoomData(
            name="veranda1", type="veranda", min_w=10, min_h=10, max_w=20, max_h=20
        ),
        RoomData(name="garage1", type="garage", min_w=10, min_h=10, max_w=20, max_h=20),
        RoomData(
            name="livingRoom1",
            type="livingRoom",
            min_w=20,
            min_h=20,
            max_w=30,
            max_h=30,
        ),
        RoomData(
            name="kitchen1", type="kitchen", min_w=20, min_h=20, max_w=30, max_h=30
        ),
        RoomData(
            name="diningRoom1",
            type="diningRoom",
            min_w=20,
            min_h=20,
            max_w=30,
            max_h=30,
        ),
        RoomData(
            name="hallway1", type="hallway", min_w=20, min_h=20, max_w=30, max_h=30
        ),
        RoomData(
            name="bathroom1", type="bathroom", min_w=20, min_h=20, max_w=30, max_h=30
        ),
        RoomData(
            name="bedroom1", type="bedroom", min_w=20, min_h=20, max_w=30, max_h=30
        ),
        RoomData(
            name="bedroom2", type="bedroom", min_w=20, min_h=20, max_w=30, max_h=30
        ),
        RoomData(
            name="attachedBathroom1",
            type="attachedBathroom",
            min_w=10,
            min_h=10,
            max_w=20,
            max_h=20,
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


def _build_positions() -> dict[str, tuple[float, float]]:
    return {
        "veranda1": (20.0, 20.0),
        "garage1": (100.0, 20.0),
        "livingRoom1": (60.0, 30.0),
        "kitchen1": (60.0, 60.0),
        "diningRoom1": (30.0, 90.0),
        "hallway1": (90.0, 90.0),
        "bathroom1": (45.0, 60.0),
        "bedroom1": (95.0, 60.0),
        "bedroom2": (25.0, 60.0),
        "attachedBathroom1": (98.0, 60.0),
    }


def test_score_optuna_layout_computes_all_sections() -> None:
    requirements = _build_requirements()
    result = score_optuna_layout(requirements, _build_positions())

    assert 0.0 <= result.total_score <= 90.0
    assert 0.0 <= result.section_scores["floor_plan_zones"] <= 30.0
    assert 0.0 <= result.section_scores["outer_clearance"] <= 20.0
    assert 0.0 <= result.section_scores["room_relations"] <= 40.0

    zone_rooms = result.section_results["floor_plan_zones"].details["rooms"]
    clearance_details = result.section_results["outer_clearance"].details
    relation_paths = result.section_results["room_relations"].details["path_summaries"]

    assert zone_rooms["veranda1"]["passed"] is True
    assert zone_rooms["garage1"]["passed"] is True
    assert clearance_details["evaluated_components"] == 3
    assert clearance_details["average_percentage_achieved"] == 100.0
    assert len(relation_paths) == 8
    assert any(item["reason"] == "best_instance_pair" for item in relation_paths)

    relation_details = result.diagnostics["room_relations"]
    assert "uncrossed_hallways" in relation_details
    assert isinstance(relation_details["uncrossed_hallways"], list)


def test_attached_bathroom_links_to_closest_bedroom_only() -> None:
    requirements = _build_requirements()
    graph = _build_graph(
        [
            # Use a smaller slice of points to isolate the special-case edge.
            *score_optuna_layout(requirements, _build_positions()).room_points,
        ]
    )

    assert graph.has_edge("attachedBathroom1", "bedroom1") is True
    assert graph.has_edge("attachedBathroom1", "bedroom2") is False
