from __future__ import annotations

from app.algorithms.floor_plan_scoring import (
    CRITICAL_GROUP,
    DEFAULT_SCORING_PROFILE,
    FloorPlanScoreManager,
    create_default_registry,
)


def test_default_profile_and_registry_are_pipeline_compatible() -> None:
    registry = create_default_registry()
    enabled_groups = [
        group for group in DEFAULT_SCORING_PROFILE.groups if group.enabled
    ]
    enabled_rules = [
        rule for rule in DEFAULT_SCORING_PROFILE.evaluators if rule.enabled
    ]

    assert enabled_groups[0].key == CRITICAL_GROUP
    assert all(registry.contains(rule.key) for rule in enabled_rules)
    assert all(
        rule.minimum_score is not None
        for rule in enabled_rules
        if rule.group_key == CRITICAL_GROUP
    )
    assert all(
        rule.minimum_score is None
        for rule in enabled_rules
        if rule.group_key != CRITICAL_GROUP
    )

    # Construction performs the package's complete profile/registry validation.
    manager = FloorPlanScoreManager(
        registry=registry,
        profile=DEFAULT_SCORING_PROFILE,
    )
    assert isinstance(manager, FloorPlanScoreManager)
