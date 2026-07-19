from __future__ import annotations

import math

import pytest

from app.algorithms.candidate_scoring import EvaluationStatus, ScoringContext
from app.algorithms.candidate_scoring.evaluators import (
    ExteriorClearanceEvaluator,
    RelationshipQualityEvaluator,
    SpatialDistributionEvaluator,
    ZoneSuitabilityEvaluator,
)
from app.algorithms.candidate_scoring.types import CandidateScoringInput

from .builders import build_scoring_input


def _context(scoring_input: CandidateScoringInput) -> ScoringContext:
    return ScoringContext(scoring_input=scoring_input)


def test_zone_suitability_scores_room_inside_preferred_zone_at_100() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 90, "height": 90},
            "rooms": [
                {"id": "living", "room_type": "living_room", "name": "Living"}
            ],
        },
        candidate={"living": {"x": 45, "y": 15}},
    )

    result = ZoneSuitabilityEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.COMPLETED
    assert result.score == pytest.approx(100.0)
    assert result.findings == ()
    assert result.metrics["room.living.distance_to_zone"] == pytest.approx(0.0)


def test_zone_suitability_penalizes_room_outside_preferred_zone() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 90, "height": 90},
            "rooms": [
                {"id": "living", "room_type": "living_room", "name": "Living"}
            ],
        },
        candidate={"living": {"x": 45, "y": 85}},
    )

    result = ZoneSuitabilityEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.COMPLETED
    assert result.score is not None
    assert 0.0 <= result.score < 100.0
    assert result.findings[0].code == "ROOM_OUTSIDE_PREFERRED_ZONE"
    assert result.findings[0].subject_ids == ("living",)


def test_zone_suitability_is_not_applicable_without_configured_room_types() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 90, "height": 90},
            "rooms": [
                {"id": "bedroom", "room_type": "bedroom", "name": "Bedroom"}
            ],
        },
        candidate={"bedroom": {"x": 45, "y": 45}},
    )

    result = ZoneSuitabilityEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.NOT_APPLICABLE
    assert result.score is None
    assert result.findings[0].code == "NO_ZONE_SCORABLE_ROOMS"


def test_zone_suitability_supports_custom_zone_settings() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "bedroom", "room_type": "bedroom", "name": "Bedroom"}
            ],
        },
        candidate={"bedroom": {"x": 75, "y": 75}},
    )

    result = ZoneSuitabilityEvaluator().evaluate(
        _context(scoring_input),
        {"grid_size": 2, "valid_zones": {"bedroom": ((2, 2),)}},
    )

    assert result.status is EvaluationStatus.COMPLETED
    assert result.score == pytest.approx(100.0)


def test_exterior_clearance_scores_unblocked_access_at_100() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "veranda", "room_type": "veranda", "name": "Veranda"},
                {"id": "kitchen", "room_type": "kitchen", "name": "Kitchen"},
                {"id": "bedroom", "room_type": "bedroom", "name": "Bedroom"},
            ],
        },
        candidate={
            "veranda": {"x": 50, "y": 10},
            "kitchen": {"x": 80, "y": 60},
            "bedroom": {"x": 10, "y": 50},
        },
    )

    result = ExteriorClearanceEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.COMPLETED
    assert result.score == pytest.approx(100.0)
    assert result.findings == ()
    assert result.metrics["evaluated_component_count"] == pytest.approx(2.0)


def test_exterior_clearance_applies_penalty_for_front_blocker() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "veranda", "room_type": "veranda", "name": "Veranda"},
                {"id": "blocker", "room_type": "bedroom", "name": "Bedroom"},
            ],
        },
        candidate={
            "veranda": {"x": 50, "y": 20},
            "blocker": {"x": 50, "y": 10},
        },
    )

    result = ExteriorClearanceEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.COMPLETED
    assert result.score == pytest.approx(90.0)
    assert result.findings[0].code == "EXTERIOR_CLEARANCE_BLOCKED"
    assert result.findings[0].subject_ids == ("veranda", "blocker")


def test_exterior_clearance_uses_best_available_back_access_candidate() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "kitchen", "room_type": "kitchen", "name": "Kitchen"},
                {"id": "hallway", "room_type": "hallway", "name": "Hallway"},
                {"id": "blocker", "room_type": "bedroom", "name": "Bedroom"},
            ],
        },
        candidate={
            "kitchen": {"x": 20, "y": 60},
            "hallway": {"x": 80, "y": 60},
            "blocker": {"x": 20, "y": 70},
        },
    )

    result = ExteriorClearanceEvaluator().evaluate(_context(scoring_input), {})

    # Kitchen scores 90 after one blocker; hallway scores 70 with no blocker.
    assert result.score == pytest.approx(90.0)
    assert result.metrics["component.back_access"] == pytest.approx(90.0)


def test_exterior_clearance_is_not_applicable_without_access_rooms() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "bedroom", "room_type": "bedroom", "name": "Bedroom"}
            ],
        },
        candidate={"bedroom": {"x": 50, "y": 50}},
    )

    result = ExteriorClearanceEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.NOT_APPLICABLE
    assert result.score is None
    assert result.findings[0].code == "NO_EXTERIOR_ACCESS_ROOMS"


def test_relationship_quality_scores_known_direct_relation() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "living", "room_type": "living_room", "name": "Living"},
                {"id": "kitchen", "room_type": "kitchen", "name": "Kitchen"},
            ],
        },
        candidate={
            "living": {"x": 10, "y": 10},
            "kitchen": {"x": 20, "y": 10},
        },
    )
    settings = {
        "relation_rules": (("living_room", "kitchen", 0.0),),
        "path_queries": (("living_room", "kitchen", "public"),),
        "max_cost_multiplier": 1.0,
        "pathing_weight": 0.75,
        "hallway_privacy_weight": 0.25,
    }

    result = RelationshipQualityEvaluator().evaluate(_context(scoring_input), settings)

    expected_pathing = 100.0 * (1.0 - 10.0 / math.hypot(100.0, 100.0))
    expected_total = expected_pathing * 0.75 + 100.0 * 0.25
    assert result.status is EvaluationStatus.COMPLETED
    assert result.metrics["query.0.cost"] == pytest.approx(10.0)
    assert result.metrics["pathing_score"] == pytest.approx(expected_pathing)
    assert result.score == pytest.approx(expected_total)


def test_relationship_quality_reports_missing_route() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "bedroom", "room_type": "bedroom", "name": "Bedroom"},
                {"id": "garage", "room_type": "garage", "name": "Garage"},
            ],
        },
        candidate={
            "bedroom": {"x": 10, "y": 10},
            "garage": {"x": 90, "y": 90},
        },
    )

    result = RelationshipQualityEvaluator().evaluate(
        _context(scoring_input),
        {
            "relation_rules": (),
            "path_queries": (("bedroom", "garage", "private"),),
        },
    )

    assert result.status is EvaluationStatus.COMPLETED
    assert result.metrics["pathing_score"] == pytest.approx(0.0)
    assert result.score == pytest.approx(25.0)
    assert result.findings[0].code == "RELATION_PATH_MISSING"


def test_relationship_quality_detects_mixed_hallway_flow() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "living", "room_type": "living_room", "name": "Living"},
                {"id": "bedroom", "room_type": "bedroom", "name": "Bedroom"},
                {"id": "kitchen", "room_type": "kitchen", "name": "Kitchen"},
                {"id": "hallway", "room_type": "hallway", "name": "Hallway"},
            ],
        },
        candidate={
            "living": {"x": 10, "y": 50},
            "hallway": {"x": 50, "y": 50},
            "bedroom": {"x": 90, "y": 80},
            "kitchen": {"x": 90, "y": 20},
        },
    )

    result = RelationshipQualityEvaluator().evaluate(
        _context(scoring_input),
        {
            "relation_rules": (),
            "path_queries": (
                ("living_room", "bedroom", "private"),
                ("living_room", "kitchen", "public"),
            ),
        },
    )

    assert result.status is EvaluationStatus.COMPLETED
    assert result.metrics["hallway_separation_score"] == pytest.approx(0.0)
    assert any(
        finding.code == "HALLWAY_MIXES_PUBLIC_PRIVATE_FLOW"
        for finding in result.findings
    )


def test_relationship_quality_is_not_applicable_without_active_query() -> None:
    scoring_input = CandidateScoringInput(
        specification={
            "floor": {"width": 100, "height": 100},
            "rooms": [
                {"id": "garage", "room_type": "garage", "name": "Garage"}
            ],
        },
        candidate={"garage": {"x": 20, "y": 20}},
    )

    result = RelationshipQualityEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.NOT_APPLICABLE
    assert result.score is None
    assert result.findings[0].code == "NO_ACTIVE_RELATION_QUERIES"


def test_spatial_distribution_returns_zero_for_empty_candidate() -> None:
    scoring_input = CandidateScoringInput(
        specification={"floor": {"width": 100, "height": 100}, "rooms": []},
        candidate={},
    )

    result = SpatialDistributionEvaluator().evaluate(_context(scoring_input), {})

    assert result.status is EvaluationStatus.COMPLETED
    assert result.score == pytest.approx(0.0)
    assert result.findings[0].code == "NO_CANDIDATE_POINTS"


def test_spatial_distribution_scores_regular_points_better_than_clustered_points() -> None:
    specification = {
        "floor": {"width": 100, "height": 100},
        "rooms": [
            {"id": room_id, "room_type": "bedroom", "name": room_id}
            for room_id in ("a", "b", "c", "d")
        ],
    }
    regular = CandidateScoringInput(
        specification=specification,
        candidate={
            "a": {"x": 25, "y": 25},
            "b": {"x": 75, "y": 25},
            "c": {"x": 25, "y": 75},
            "d": {"x": 75, "y": 75},
        },
    )
    clustered = CandidateScoringInput(
        specification=specification,
        candidate={
            "a": {"x": 48, "y": 48},
            "b": {"x": 52, "y": 48},
            "c": {"x": 48, "y": 52},
            "d": {"x": 52, "y": 52},
        },
    )
    evaluator = SpatialDistributionEvaluator()

    regular_result = evaluator.evaluate(_context(regular), {})
    clustered_result = evaluator.evaluate(_context(clustered), {})

    assert regular_result.score is not None
    assert clustered_result.score is not None
    assert regular_result.score > clustered_result.score
    assert regular_result.metrics["point_count"] == pytest.approx(4.0)
    assert clustered_result.metrics["gap_ratio"] > regular_result.metrics["gap_ratio"]


@pytest.mark.parametrize(
    ("evaluator", "settings", "message"),
    [
        (ZoneSuitabilityEvaluator(), {"grid_size": 0}, "grid_size must be positive"),
        (
            ExteriorClearanceEvaluator(),
            {"corridor_depth": float("inf")},
            "must be finite",
        ),
        (
            RelationshipQualityEvaluator(),
            {"pathing_weight": 0, "hallway_privacy_weight": 0},
            "positive total",
        ),
        (
            SpatialDistributionEvaluator(),
            {"grid_size": 1},
            "grid_size must be at least 2",
        ),
    ],
)
def test_evaluators_reject_invalid_settings(
    evaluator: object,
    settings: dict[str, object],
    message: str,
) -> None:
    scoring_input = build_scoring_input()

    with pytest.raises(ValueError, match=message):
        evaluator.evaluate(_context(scoring_input), settings)  # type: ignore[attr-defined]
