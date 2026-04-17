from app.algorithms.fpg_rooms.types.room import ConfigData, FpgRequirements
from app.core.fpg_rooms.config_fpg import (
    DEFAULT_ASPECT_RATIO_MAX,
    DEFAULT_ASPECT_RATIO_MIN,
    DEFAULT_HALLWAY_COUNT,
    ENVELOPE_APPLY_SIDES,
    ENVELOPE_ENABLED,
    ENVELOPE_EXCLUDE_TYPES,
    ENVELOPE_MAX_GAP,
    ENVELOPE_MIN_GAP,
    MIN_COVERAGE,
)
from app.schemas.db.room_setup_template import RoomSetupTemplateBase
from app.util.constraint_pruner import prune_room_relations_constraints_by_template
from app.util.room_requirements import normalize_db_data_requirements
from app.util.algorithm_manager.build_rooms_from_template import build_rooms_from_template
from app.util.algorithm_manager.load_server_side_data import load_server_side_data


def build_requirements(
    floor_width: float,
    floor_height: float,
    room_template: RoomSetupTemplateBase,
) -> FpgRequirements:
    """Build FpgRequirements from template, loading and pruning server-side constraints.

    This function now handles all data loading and constraint pruning internally.
    Raises exceptions if any step fails (no silent defaults).
    """
    print("\n _build_requirements()")

    try:
        _, size_constraints, relation_constraints = load_server_side_data()
    except Exception as exc:
        raise Exception(f"Failed to load server-side constraints: {exc}") from exc

    try:
        relation_constraints, prune_error = (
            prune_room_relations_constraints_by_template(
                room_template=room_template,
                room_relations_constraints=relation_constraints,
            )
        )
        if prune_error:
            raise Exception(f"Failed to prune relation constraints: {prune_error}")
    except Exception as exc:
        raise Exception(f"Failed to prune room relations constraints: {exc}") from exc

    rooms = build_rooms_from_template(room_template)
    normalized_rooms = normalize_db_data_requirements(rooms, size_constraints)

    config = ConfigData(
        min_coverage=MIN_COVERAGE,
        max_aspect_ratio=DEFAULT_ASPECT_RATIO_MAX,
        min_aspect_ratio=DEFAULT_ASPECT_RATIO_MIN,
        floor_plan_width=floor_width,
        floor_plan_height=floor_height,
        hallway_count=DEFAULT_HALLWAY_COUNT,
        envelope_enabled=ENVELOPE_ENABLED,
        envelope_min_gap=ENVELOPE_MIN_GAP,
        envelope_max_gap=ENVELOPE_MAX_GAP,
        envelope_exclude_types=ENVELOPE_EXCLUDE_TYPES,
        envelope_apply_sides=ENVELOPE_APPLY_SIDES,
    )

    return FpgRequirements(
        rooms=normalized_rooms,
        config=config,
        relation_constraints=list(relation_constraints),
    )
