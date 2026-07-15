from __future__ import annotations

from app.algorithms.candidate_scoring import (
    CandidateScoringInput,
    EvaluationStatus,
    ExteriorClearanceEvaluator,
    RelationshipQualityEvaluator,
    ScoringContextFactory,
    SpatialDistributionEvaluator,
    ZoneSuitabilityEvaluator,
)


def _context():
    specification = {
        "floor": {"width": 60.0, "height": 40.0},
        "rooms": [
            {"id": "veranda", "name": "Veranda", "room_type": "veranda"},
            {"id": "living", "name": "Living", "room_type": "living_room"},
            {"id": "kitchen", "name": "Kitchen", "room_type": "kitchen"},
            {"id": "dining", "name": "Dining", "room_type": "dining_room"},
            {"id": "bedroom", "name": "Bedroom", "room_type": "bedroom"},
            {"id": "bathroom", "name": "Bathroom", "room_type": "bathroom"},
            {"id": "hallway", "name": "Hallway", "room_type": "hallway"},
        ],
    }
    candidate = {
        "veranda": (10.0, 5.0),
        "living": (20.0, 12.0),
        "kitchen": (42.0, 28.0),
        "dining": (36.0, 24.0),
        "bedroom": (20.0, 30.0),
        "bathroom": (30.0, 30.0),
        "hallway": (28.0, 22.0),
    }
    return ScoringContextFactory().build(
        CandidateScoringInput(specification=specification, candidate=candidate)
    )


def test_all_concrete_evaluators_return_valid_contract_results() -> None:
    context = _context()
    evaluators = (
        ZoneSuitabilityEvaluator(),
        ExteriorClearanceEvaluator(),
        RelationshipQualityEvaluator(),
        SpatialDistributionEvaluator(),
    )

    for evaluator in evaluators:
        result = evaluator.evaluate(context, {})
        assert result.status in {
            EvaluationStatus.COMPLETED,
            EvaluationStatus.NOT_APPLICABLE,
        }
        if result.status is EvaluationStatus.COMPLETED:
            assert result.score is not None
            assert 0.0 <= result.score <= 100.0


def test_zone_evaluator_is_not_applicable_without_configured_room_types() -> None:
    context = ScoringContextFactory().build(
        CandidateScoringInput(
            specification={
                "floor": {"width": 20.0, "height": 20.0},
                "rooms": [{"id": "bed", "room_type": "bedroom"}],
            },
            candidate={"bed": (10.0, 10.0)},
        )
    )
    result = ZoneSuitabilityEvaluator().evaluate(context, {})
    assert result.status is EvaluationStatus.NOT_APPLICABLE
    assert result.score is None
