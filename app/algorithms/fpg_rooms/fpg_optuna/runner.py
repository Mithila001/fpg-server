from __future__ import annotations

import copy
import math
import time
from typing import Callable

import optuna

from app.algorithms.fpg_rooms.types.room import (
    ConfigData,
    FpgRequirements,
    RoomData,
)
from app.core.fpg_rooms.config_fpg import (
    TRIAL_EARLY_STOP_SCORE_THRESHOLD,
    TRIAL_OPTIMIZATION_TIMEOUT_SECONDS,
    ROOM_SIZE_HIERARCHY,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_DEFAULT_STUDY_NAME,
    OPTUNA_DEFAULT_TRIALS,
    OPTUNA_DIMENSION_MAX_JITTER,
    OPTUNA_DIMENSION_MIN_JITTER,
    OPTUNA_ENVELOPE_APPLY_SIDES_DEFAULT,
    OPTUNA_ENVELOPE_ENABLED_DEFAULT,
    OPTUNA_ENVELOPE_EXCLUDE_TYPES_DEFAULT,
    OPTUNA_ENVELOPE_MAX_GAP_DEFAULT,
    OPTUNA_ENVELOPE_MIN_GAP_DEFAULT,
    OPTUNA_HALLWAY_COUNT_MAX,
    OPTUNA_HALLWAY_COUNT_MIN,
    OPTUNA_MIN_COVERAGE_FLOOR,
    OPTUNA_MIN_COVERAGE_HIGH,
    OPTUNA_MIN_COVERAGE_LOW,
    OPTUNA_MIN_COVERAGE_STEP,
    OPTUNA_PARAM_KEY_HALLWAY_COUNT,
    OPTUNA_PARAM_KEY_MIN_COVERAGE,
)
from app.util.tracking import get_tracking_context

from .exceptions import TrialTimeoutError
from .types import FpgEvaluationResult, OptunaOptimizationResult
from .util import calculate_floor_bounds

EVALUATION_FN = Callable[[FpgRequirements, bool], FpgEvaluationResult]
FLOOR_DIMENSION_BOUNDS = dict[str, int]

OPTUNA_PARAM_KEY_FLOOR_PLAN_WIDTH = "floor_plan_width"
OPTUNA_PARAM_KEY_FLOOR_PLAN_HEIGHT = "floor_plan_height"


class OptunaOptimizationController:
    """Controller to manage trial optimization early stopping and timeout logic."""

    def __init__(self, timeout_seconds: int = TRIAL_OPTIMIZATION_TIMEOUT_SECONDS, score_threshold: float = TRIAL_EARLY_STOP_SCORE_THRESHOLD):
        """
        Initialize the optimization controller.

        Args:
            timeout_seconds: Maximum time allowed for all trials (seconds)
            score_threshold: Score threshold for early stopping (0-100)
        """
        self.timeout_seconds = timeout_seconds
        self.score_threshold = score_threshold
        self.start_time = time.time()
        self.best_score: float | None = None
        self.feasible_found = False

    def get_elapsed_time(self) -> float:
        """Get elapsed time since controller creation (seconds)."""
        return time.time() - self.start_time

    def check_timeout_and_raise(self) -> None:
        """Raise TrialTimeoutError if timeout exceeded."""
        elapsed = self.get_elapsed_time()
        if elapsed > self.timeout_seconds:
            raise TrialTimeoutError(elapsed_time=elapsed, timeout_seconds=self.timeout_seconds)

    def should_stop_optimization(self, score: float) -> bool:
        """
        Check if optimization should stop (early stopping condition).

        Args:
            score: The score from the current trial

        Returns:
            True if optimization should stop, False otherwise
        """
        # Update best score
        if self.best_score is None or score > self.best_score:
            self.best_score = score

        # Check if score exceeds threshold
        if score >= self.score_threshold:
            self.feasible_found = True
            return True

        # Check if timeout exceeded
        if self.get_elapsed_time() > self.timeout_seconds:
            # Don't raise here; let caller decide how to handle
            return False

        return False


def _trial_param_key(room: RoomData, index: int, suffix: str) -> str:
    return f"room_{index}_{room.type}_{suffix}"


def _clamp_int(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _find_room_index(requirements: FpgRequirements, room_type: str) -> int:
    for index, room in enumerate(requirements.rooms):
        if room.type == room_type:
            return index
    raise ValueError(f"Missing required room type: {room_type}")


def _select_room_rectangle_for_area_band(
    *,
    room_type: str,
    allowed_min_w: int,
    allowed_max_w: int,
    allowed_min_h: int,
    allowed_max_h: int,
    area_min: int,
    area_max: int,
    target_area: int,
) -> tuple[int, int]:
    best_choice: tuple[int, int, int, int] | None = None

    for width in range(allowed_min_w, allowed_max_w + 1):
        for height in range(allowed_min_h, allowed_max_h + 1):
            area = width * height
            if area < area_min or area > area_max:
                continue

            candidate = (abs(area - target_area), abs(width - height), width, height)
            if best_choice is None or candidate < best_choice:
                best_choice = candidate

    if best_choice is None:
        raise ValueError(
            "No valid rectangle found for room type "
            f"{room_type} within area band [{area_min}, {area_max}] "
            f"and bounds w=[{allowed_min_w}, {allowed_max_w}], h=[{allowed_min_h}, {allowed_max_h}]."
        )

    return best_choice[2], best_choice[3]


def _tune_living_room(
    trial: optuna.Trial,
    room: RoomData,
    index: int,
    floor_w: int,
    floor_h: int,
) -> tuple[RoomData, int]:
    tuned_room = _tune_room_dimension(
        trial=trial,
        floor_w=floor_w,
        floor_h=floor_h,
        room=room,
        index=index,
    )

    living_min_area = int(tuned_room.min_w) * int(tuned_room.min_h)
    living_max_area = int(tuned_room.max_w) * int(tuned_room.max_h)
    if living_min_area > living_max_area:
        raise ValueError(
            "LivingRoom has invalid tuned area bounds: "
            f"min_area={living_min_area}, max_area={living_max_area}."
        )

    anchor_area = trial.suggest_int(
        _trial_param_key(room, index, "anchor_area"),
        living_min_area,
        living_max_area,
    )

    return tuned_room, anchor_area


def _tune_hierarchy_room(
    trial: optuna.Trial,
    floor_w: int,
    floor_h: int,
    room: RoomData,
    index: int,
    anchor_area: int,
) -> RoomData:
    if room.type not in ROOM_SIZE_HIERARCHY:
        raise ValueError(f"Room type '{room.type}' is not configured in ROOM_SIZE_HIERARCHY")

    allowed_min_w, allowed_max_w = _resolve_room_axis_bounds(
        room_type=room.type,
        axis_name="width",
        requested_min=int(room.min_w),
        requested_max=int(room.max_w),
        floor_limit=floor_w,
    )
    allowed_min_h, allowed_max_h = _resolve_room_axis_bounds(
        room_type=room.type,
        axis_name="height",
        requested_min=int(room.min_h),
        requested_max=int(room.max_h),
        floor_limit=floor_h,
    )

    original_min_area = allowed_min_w * allowed_min_h
    original_max_area = allowed_max_w * allowed_max_h
    min_pct, max_pct = ROOM_SIZE_HIERARCHY[room.type]

    hierarchy_min_area = int(math.ceil(anchor_area * min_pct / 100.0))
    hierarchy_max_area = int(math.floor(anchor_area * max_pct / 100.0))

    area_min = max(original_min_area, hierarchy_min_area)
    area_max = min(original_max_area, hierarchy_max_area)
    if area_min > area_max:
        raise ValueError(
            "No valid hierarchy area band for room type "
            f"{room.type}: area=[{area_min}, {area_max}], anchor_area={anchor_area}, "
            f"original=[{original_min_area}, {original_max_area}], hierarchy=[{hierarchy_min_area}, {hierarchy_max_area}]."
        )

    target_area = trial.suggest_int(
        _trial_param_key(room, index, "target_area"),
        area_min,
        area_max,
    )
    chosen_w, chosen_h = _select_room_rectangle_for_area_band(
        room_type=room.type,
        allowed_min_w=allowed_min_w,
        allowed_max_w=allowed_max_w,
        allowed_min_h=allowed_min_h,
        allowed_max_h=allowed_max_h,
        area_min=area_min,
        area_max=area_max,
        target_area=target_area,
    )

    return RoomData(
        name=room.name,
        type=room.type,
        min_w=chosen_w,
        min_h=chosen_h,
        max_w=chosen_w,
        max_h=chosen_h,
    )


def _resolve_room_axis_bounds(
    *,
    room_type: str,
    axis_name: str,
    requested_min: int,
    requested_max: int,
    floor_limit: int,
) -> tuple[int, int]:
    normalized_max = max(1, int(requested_max))
    normalized_min = max(1, min(int(requested_min), normalized_max))

    allowed_min = normalized_min
    allowed_max = min(normalized_max, max(1, int(floor_limit)))

    if allowed_min > allowed_max:
        raise ValueError(
            "No valid room dimension range after intersecting base requirements with floor bounds "
            f"for {room_type} ({axis_name}: base=[{normalized_min}, {normalized_max}], "
            f"floor_limit={floor_limit})."
        )

    return allowed_min, allowed_max


def _tune_room_dimension(
    trial: optuna.Trial,
    floor_w: int,
    floor_h: int,
    room: RoomData,
    index: int,
) -> RoomData:
    allowed_min_w, allowed_max_w = _resolve_room_axis_bounds(
        room_type=room.type,
        axis_name="width",
        requested_min=int(room.min_w),
        requested_max=int(room.max_w),
        floor_limit=floor_w,
    )
    allowed_min_h, allowed_max_h = _resolve_room_axis_bounds(
        room_type=room.type,
        axis_name="height",
        requested_min=int(room.min_h),
        requested_max=int(room.max_h),
        floor_limit=floor_h,
    )

    base_min_w = allowed_min_w
    base_max_w = allowed_max_w
    base_min_h = allowed_min_h
    base_max_h = allowed_max_h

    min_w_low = max(allowed_min_w, base_min_w - OPTUNA_DIMENSION_MIN_JITTER)
    min_w_high = min(allowed_max_w, base_min_w + OPTUNA_DIMENSION_MIN_JITTER)
    min_w = trial.suggest_int(_trial_param_key(room, index, "min_w"), min_w_low, min_w_high)

    min_h_low = max(allowed_min_h, base_min_h - OPTUNA_DIMENSION_MIN_JITTER)
    min_h_high = min(allowed_max_h, base_min_h + OPTUNA_DIMENSION_MIN_JITTER)
    min_h = trial.suggest_int(_trial_param_key(room, index, "min_h"), min_h_low, min_h_high)

    max_w_low = max(min_w, allowed_min_w, base_max_w - OPTUNA_DIMENSION_MAX_JITTER)
    max_w_high = min(allowed_max_w, base_max_w + OPTUNA_DIMENSION_MAX_JITTER)
    if max_w_low > max_w_high:
        max_w_low = max_w_high
    max_w = trial.suggest_int(_trial_param_key(room, index, "max_w"), max_w_low, max_w_high)

    max_h_low = max(min_h, allowed_min_h, base_max_h - OPTUNA_DIMENSION_MAX_JITTER)
    max_h_high = min(allowed_max_h, base_max_h + OPTUNA_DIMENSION_MAX_JITTER)
    if max_h_low > max_h_high:
        max_h_low = max_h_high
    max_h = trial.suggest_int(_trial_param_key(room, index, "max_h"), max_h_low, max_h_high)

    return RoomData(
        name=room.name,
        type=room.type,
        min_w=min_w,
        min_h=min_h,
        max_w=max_w,
        max_h=max_h,
    )


def _resolve_floor_dimension_bounds(
    base_requirements: FpgRequirements,
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None,
) -> tuple[int, int, int, int]:
    base_floor_w = max(1, int(base_requirements.config.floor_plan_width))
    base_floor_h = max(1, int(base_requirements.config.floor_plan_height))

    if floor_dimension_bounds is None:
        computed_bounds = calculate_floor_bounds(base_requirements)
        if not computed_bounds.feasible:
            return base_floor_w, base_floor_h, base_floor_w, base_floor_h

        return (
            max(1, int(computed_bounds.min_floor_width)),
            max(1, int(computed_bounds.min_floor_height)),
            max(1, int(computed_bounds.max_floor_width)),
            max(1, int(computed_bounds.max_floor_height)),
        )

    min_floor_w = int(floor_dimension_bounds.get("min_floor_width", base_floor_w))
    min_floor_h = int(floor_dimension_bounds.get("min_floor_height", base_floor_h))
    max_floor_w = int(floor_dimension_bounds.get("max_floor_width", base_floor_w))
    max_floor_h = int(floor_dimension_bounds.get("max_floor_height", base_floor_h))

    min_floor_w = max(1, min_floor_w)
    min_floor_h = max(1, min_floor_h)
    max_floor_w = max(min_floor_w, max_floor_w)
    max_floor_h = max(min_floor_h, max_floor_h)

    return min_floor_w, min_floor_h, max_floor_w, max_floor_h


def mutate_requirements(
    base_requirements: FpgRequirements,
    trial: optuna.Trial,
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None = None,
) -> FpgRequirements:
    # print(f"Base Requirment in Optuna: \n {base_requirements}\n")
    min_floor_w, min_floor_h, max_floor_w, max_floor_h = _resolve_floor_dimension_bounds(
        base_requirements,
        floor_dimension_bounds,
    )

    min_aspect_ratio = 1.0
    max_aspect_ratio = 16.0 / 9.0

    floor_w = trial.suggest_int(
        OPTUNA_PARAM_KEY_FLOOR_PLAN_WIDTH,
        min_floor_w,
        max_floor_w,
    )

    # Derive valid height range for this width under hard aspect constraint:
    # 1:1 <= width/height <= 16:9  =>  width/(16/9) <= height <= width
    derived_min_h = int(math.ceil(floor_w / max_aspect_ratio))
    derived_max_h = int(math.floor(floor_w / min_aspect_ratio))

    valid_min_h = max(min_floor_h, derived_min_h)
    valid_max_h = min(max_floor_h, derived_max_h)
    if valid_min_h > valid_max_h:
        raise ValueError(
            "No valid floor height exists for selected width under 1:1..16:9 aspect ratio "
            f"(width={floor_w}, min_h={min_floor_h}, max_h={max_floor_h})."
        )

    floor_h = trial.suggest_int(
        OPTUNA_PARAM_KEY_FLOOR_PLAN_HEIGHT,
        valid_min_h,
        valid_max_h,
    )

    tuned_rooms: list[RoomData] = []

    living_room_index = _find_room_index(base_requirements, "livingRoom")
    living_room_base = base_requirements.rooms[living_room_index]
    tuned_living_room, living_anchor_area = _tune_living_room(
        trial=trial,
        room=living_room_base,
        index=living_room_index,
        floor_w=floor_w,
        floor_h=floor_h,
    )

    for idx, room in enumerate(base_requirements.rooms):
        if room.type == "livingRoom":
            tuned_rooms.append(tuned_living_room)
        elif room.type in ROOM_SIZE_HIERARCHY:
            tuned_rooms.append(
                _tune_hierarchy_room(
                    trial=trial,
                    floor_w=floor_w,
                    floor_h=floor_h,
                    room=room,
                    index=idx,
                    anchor_area=living_anchor_area,
                )
            )
        else:
            tuned_rooms.append(_tune_room_dimension(trial, floor_w, floor_h, room, idx))

    tuned_config = ConfigData(
        min_coverage=trial.suggest_float(
            OPTUNA_PARAM_KEY_MIN_COVERAGE,
            OPTUNA_MIN_COVERAGE_LOW,
            OPTUNA_MIN_COVERAGE_HIGH,
            step=OPTUNA_MIN_COVERAGE_STEP,
        ),
        hallway_count=trial.suggest_int(
            OPTUNA_PARAM_KEY_HALLWAY_COUNT,
            OPTUNA_HALLWAY_COUNT_MIN,
            OPTUNA_HALLWAY_COUNT_MAX,
        ),
        max_aspect_ratio=base_requirements.config.max_aspect_ratio,
        min_aspect_ratio=base_requirements.config.min_aspect_ratio,
        floor_plan_width=floor_w,
        floor_plan_height=floor_h,
        envelope_enabled=bool(
            getattr(
                base_requirements.config,
                "envelope_enabled",
                OPTUNA_ENVELOPE_ENABLED_DEFAULT,
            )
        ),
        envelope_min_gap=int(
            getattr(
                base_requirements.config,
                "envelope_min_gap",
                OPTUNA_ENVELOPE_MIN_GAP_DEFAULT,
            )
        ),
        envelope_max_gap=int(
            getattr(
                base_requirements.config,
                "envelope_max_gap",
                OPTUNA_ENVELOPE_MAX_GAP_DEFAULT,
            )
        ),
        envelope_exclude_types=list(
            getattr(
                base_requirements.config,
                "envelope_exclude_types",
                OPTUNA_ENVELOPE_EXCLUDE_TYPES_DEFAULT,
            )
        ),
        envelope_apply_sides=list(
            getattr(
                base_requirements.config,
                "envelope_apply_sides",
                OPTUNA_ENVELOPE_APPLY_SIDES_DEFAULT,
            )
        ),
    )

    return FpgRequirements(
        rooms=tuned_rooms,
        config=tuned_config,
        relation_constraints=copy.deepcopy(base_requirements.relation_constraints),
    )


def _relation_constraints_are_resolvable(requirements: FpgRequirements) -> tuple[bool, str]:
    available_types = {room.type for room in requirements.rooms}
    # mandatory system rooms are injected by FloorPlanGenerator.
    available_types.update({"livingRoom", "hallway"})

    for item in requirements.relation_constraints:
        room_type = getattr(item, "room_type", None)
        related_room = getattr(item, "related_room", None)

        if not room_type or room_type not in available_types:
            return False, f"Unknown room_type in relation constraints: {room_type}"

        for related_type in related_room or []:
            if related_type not in available_types:
                return False, f"Unknown related_room type in relation constraints: {related_type}"

    return True, ""


def _bounds_are_valid(requirements: FpgRequirements) -> tuple[bool, str]:
    floor_w = int(requirements.config.floor_plan_width)
    floor_h = int(requirements.config.floor_plan_height)

    if floor_w < 1 or floor_h < 1:
        return False, "floor_plan_width and floor_plan_height must be positive"

    for room in requirements.rooms:
        if room.min_w < 1 or room.min_h < 1:
            return False, f"Invalid min dimensions for {room.type}"
        if room.min_w > room.max_w or room.min_h > room.max_h:
            return False, f"Invalid min/max ordering for {room.type}"
        if room.max_w > floor_w or room.max_h > floor_h:
            return False, f"Room max dimension exceeds floor bounds for {room.type}"

    coverage = float(requirements.config.min_coverage)
    if coverage <= 0.0 or coverage > 1.0:
        return False, "min_coverage must be in (0, 1]"

    return True, ""


def _precheck(requirements: FpgRequirements) -> tuple[bool, str]:
    valid, reason = _bounds_are_valid(requirements)
    if not valid:
        return False, reason

    valid, reason = _relation_constraints_are_resolvable(requirements)
    if not valid:
        return False, reason

    return True, ""


def _requirements_from_best_params(
    base_requirements: FpgRequirements,
    best_params: dict[str, float | int],
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None = None,
) -> FpgRequirements:
    min_floor_w, min_floor_h, max_floor_w, max_floor_h = _resolve_floor_dimension_bounds(
        base_requirements,
        floor_dimension_bounds,
    )

    floor_w = int(best_params.get(OPTUNA_PARAM_KEY_FLOOR_PLAN_WIDTH, min_floor_w))
    floor_h = int(best_params.get(OPTUNA_PARAM_KEY_FLOOR_PLAN_HEIGHT, min_floor_h))
    floor_w = max(min_floor_w, min(max_floor_w, floor_w))
    floor_h = max(min_floor_h, min(max_floor_h, floor_h))

    tuned_rooms: list[RoomData] = []
    living_room_index = _find_room_index(base_requirements, "livingRoom")
    living_room_base = base_requirements.rooms[living_room_index]

    allowed_min_w, allowed_max_w = _resolve_room_axis_bounds(
        room_type=living_room_base.type,
        axis_name="width",
        requested_min=int(living_room_base.min_w),
        requested_max=int(living_room_base.max_w),
        floor_limit=floor_w,
    )
    allowed_min_h, allowed_max_h = _resolve_room_axis_bounds(
        room_type=living_room_base.type,
        axis_name="height",
        requested_min=int(living_room_base.min_h),
        requested_max=int(living_room_base.max_h),
        floor_limit=floor_h,
    )

    base_min_w = allowed_min_w
    base_max_w = allowed_max_w
    base_min_h = allowed_min_h
    base_max_h = allowed_max_h

    living_min_w = int(best_params.get(_trial_param_key(living_room_base, living_room_index, "min_w"), base_min_w))
    living_min_h = int(best_params.get(_trial_param_key(living_room_base, living_room_index, "min_h"), base_min_h))
    living_max_w = int(best_params.get(_trial_param_key(living_room_base, living_room_index, "max_w"), base_max_w))
    living_max_h = int(best_params.get(_trial_param_key(living_room_base, living_room_index, "max_h"), base_max_h))

    living_min_w = _clamp_int(living_min_w, allowed_min_w, allowed_max_w)
    living_min_h = _clamp_int(living_min_h, allowed_min_h, allowed_max_h)
    living_max_w = _clamp_int(living_max_w, living_min_w, allowed_max_w)
    living_max_h = _clamp_int(living_max_h, living_min_h, allowed_max_h)

    tuned_living_room = RoomData(
        name=living_room_base.name,
        type=living_room_base.type,
        min_w=living_min_w,
        min_h=living_min_h,
        max_w=living_max_w,
        max_h=living_max_h,
    )

    living_min_area = tuned_living_room.min_w * tuned_living_room.min_h
    living_max_area = tuned_living_room.max_w * tuned_living_room.max_h
    living_anchor_area = int(
        best_params.get(
            _trial_param_key(living_room_base, living_room_index, "anchor_area"),
            living_min_area,
        )
    )
    living_anchor_area = _clamp_int(living_anchor_area, living_min_area, living_max_area)

    for idx, room in enumerate(base_requirements.rooms):
        if room.type == "livingRoom":
            tuned_rooms.append(tuned_living_room)
            continue

        if room.type in ROOM_SIZE_HIERARCHY:
            allowed_min_w, allowed_max_w = _resolve_room_axis_bounds(
                room_type=room.type,
                axis_name="width",
                requested_min=int(room.min_w),
                requested_max=int(room.max_w),
                floor_limit=floor_w,
            )
            allowed_min_h, allowed_max_h = _resolve_room_axis_bounds(
                room_type=room.type,
                axis_name="height",
                requested_min=int(room.min_h),
                requested_max=int(room.max_h),
                floor_limit=floor_h,
            )

            original_min_area = allowed_min_w * allowed_min_h
            original_max_area = allowed_max_w * allowed_max_h
            min_pct, max_pct = ROOM_SIZE_HIERARCHY[room.type]
            hierarchy_min_area = int(math.ceil(living_anchor_area * min_pct / 100.0))
            hierarchy_max_area = int(math.floor(living_anchor_area * max_pct / 100.0))

            area_min = max(original_min_area, hierarchy_min_area)
            area_max = min(original_max_area, hierarchy_max_area)
            if area_min > area_max:
                raise ValueError(
                    "No valid hierarchy area band for room type "
                    f"{room.type}: area=[{area_min}, {area_max}], anchor_area={living_anchor_area}, "
                    f"original=[{original_min_area}, {original_max_area}], hierarchy=[{hierarchy_min_area}, {hierarchy_max_area}]."
                )

            target_area = int(
                best_params.get(
                    _trial_param_key(room, idx, "target_area"),
                    area_min,
                )
            )
            target_area = _clamp_int(target_area, area_min, area_max)
            chosen_w, chosen_h = _select_room_rectangle_for_area_band(
                room_type=room.type,
                allowed_min_w=allowed_min_w,
                allowed_max_w=allowed_max_w,
                allowed_min_h=allowed_min_h,
                allowed_max_h=allowed_max_h,
                area_min=area_min,
                area_max=area_max,
                target_area=target_area,
            )

            tuned_rooms.append(
                RoomData(
                    name=room.name,
                    type=room.type,
                    min_w=chosen_w,
                    min_h=chosen_h,
                    max_w=chosen_w,
                    max_h=chosen_h,
                )
            )
            continue

        allowed_min_w, allowed_max_w = _resolve_room_axis_bounds(
            room_type=room.type,
            axis_name="width",
            requested_min=int(room.min_w),
            requested_max=int(room.max_w),
            floor_limit=floor_w,
        )
        allowed_min_h, allowed_max_h = _resolve_room_axis_bounds(
            room_type=room.type,
            axis_name="height",
            requested_min=int(room.min_h),
            requested_max=int(room.max_h),
            floor_limit=floor_h,
        )

        base_min_w = allowed_min_w
        base_max_w = allowed_max_w
        base_min_h = allowed_min_h
        base_max_h = allowed_max_h

        min_w = int(best_params.get(_trial_param_key(room, idx, "min_w"), base_min_w))
        min_h = int(best_params.get(_trial_param_key(room, idx, "min_h"), base_min_h))
        max_w = int(best_params.get(_trial_param_key(room, idx, "max_w"), base_max_w))
        max_h = int(best_params.get(_trial_param_key(room, idx, "max_h"), base_max_h))

        min_w = _clamp_int(min_w, allowed_min_w, allowed_max_w)
        min_h = _clamp_int(min_h, allowed_min_h, allowed_max_h)
        max_w = _clamp_int(max_w, min_w, allowed_max_w)
        max_h = _clamp_int(max_h, min_h, allowed_max_h)

        tuned_rooms.append(
            RoomData(
                name=room.name,
                type=room.type,
                min_w=min_w,
                min_h=min_h,
                max_w=max_w,
                max_h=max_h,
            )
        )

    coverage = float(
        best_params.get(
            OPTUNA_PARAM_KEY_MIN_COVERAGE,
            float(base_requirements.config.min_coverage),
        )
    )
    coverage = min(1.0, max(OPTUNA_MIN_COVERAGE_FLOOR, coverage))
    base_hallway_count = int(getattr(base_requirements.config, "hallway_count", 1))
    hallway_count = int(best_params.get(OPTUNA_PARAM_KEY_HALLWAY_COUNT, base_hallway_count))
    hallway_count = max(OPTUNA_HALLWAY_COUNT_MIN, min(OPTUNA_HALLWAY_COUNT_MAX, hallway_count))

    tuned_config = ConfigData(
        min_coverage=coverage,
        hallway_count=hallway_count,
        max_aspect_ratio=base_requirements.config.max_aspect_ratio,
        min_aspect_ratio=base_requirements.config.min_aspect_ratio,
        floor_plan_width=floor_w,
        floor_plan_height=floor_h,
        envelope_enabled=bool(
            getattr(
                base_requirements.config,
                "envelope_enabled",
                OPTUNA_ENVELOPE_ENABLED_DEFAULT,
            )
        ),
        envelope_min_gap=int(
            getattr(
                base_requirements.config,
                "envelope_min_gap",
                OPTUNA_ENVELOPE_MIN_GAP_DEFAULT,
            )
        ),
        envelope_max_gap=int(
            getattr(
                base_requirements.config,
                "envelope_max_gap",
                OPTUNA_ENVELOPE_MAX_GAP_DEFAULT,
            )
        ),
        envelope_exclude_types=list(
            getattr(
                base_requirements.config,
                "envelope_exclude_types",
                OPTUNA_ENVELOPE_EXCLUDE_TYPES_DEFAULT,
            )
        ),
        envelope_apply_sides=list(
            getattr(
                base_requirements.config,
                "envelope_apply_sides",
                OPTUNA_ENVELOPE_APPLY_SIDES_DEFAULT,
            )
        ),
    )

    return FpgRequirements(
        rooms=tuned_rooms,
        config=tuned_config,
        relation_constraints=copy.deepcopy(base_requirements.relation_constraints),
    )


def run_optuna_optimization(
    base_requirements: FpgRequirements,
    evaluator: EVALUATION_FN,
    n_trials: int = OPTUNA_DEFAULT_TRIALS,
    study_name: str = OPTUNA_DEFAULT_STUDY_NAME,
    storage: str | None = None,
    floor_dimension_bounds: FLOOR_DIMENSION_BOUNDS | None = None,
) -> OptunaOptimizationResult:
    """Run Optuna optimization for floor-plan requirements."""

    best_run_by_trial: dict[int, FpgEvaluationResult] = {}
    controller = OptunaOptimizationController()

    optuna.logging.set_verbosity(optuna.logging.WARN)

    def objective(trial: optuna.Trial) -> float:
        # Check timeout before starting trial evaluation
        controller.check_timeout_and_raise()

        tracking_context = get_tracking_context()
        if tracking_context is not None:
            tracking_context.next_trial_id()
        try:
            try:
                trial_requirements = mutate_requirements(
                    base_requirements,
                    trial,
                    floor_dimension_bounds=floor_dimension_bounds,
                )
            except ValueError as exc:
                trial.set_user_attr("status", "mutate_requirements_infeasible")
                trial.set_user_attr("reason", str(exc))
                trial.set_user_attr("valid", False)
                return 0.0
            # print(f"\nOptuna Trial = {trial_requirements}\n")

            bounds_result = calculate_floor_bounds(trial_requirements)
            if not bounds_result.feasible:
                trial.set_user_attr("status", "floor_bounds_infeasible")
                trial.set_user_attr("reason", bounds_result.reason)
                trial.set_user_attr("valid", False)
                print(f"\n-- Invalid Bounds: {bounds_result}\n")
                return 0.0

            print(f"\n-- Bounds: {bounds_result}\n")
            print("\nStarts")
            ok, reason = _precheck(trial_requirements)
            if not ok:
                
                trial.set_user_attr("status", "precheck_failed")
                trial.set_user_attr("reason", reason)
                trial.set_user_attr("valid", False)
                print("\n# Pre Check Failed")
                return 0.0
            # --- Optuna logging block end ---
            
            
            print("\n\n#sym:trial_requirements")
            print("  config:")
            print(f"    floor_plan_width: {trial_requirements.config.floor_plan_width}")
            print(f"    floor_plan_height: {trial_requirements.config.floor_plan_height}")
            print(f"    min_coverage: {trial_requirements.config.min_coverage}")
            print(f"    hallway_count: {trial_requirements.config.hallway_count}")
            print(f"    min_aspect_ratio: {trial_requirements.config.min_aspect_ratio}")
            print(f"    max_aspect_ratio: {trial_requirements.config.max_aspect_ratio}")
            print(f"    envelope_enabled: {trial_requirements.config.envelope_enabled}")
            print(f"    envelope_min_gap: {trial_requirements.config.envelope_min_gap}")
            print(f"    envelope_max_gap: {trial_requirements.config.envelope_max_gap}")
            print(f"    envelope_exclude_types: {trial_requirements.config.envelope_exclude_types}")
            print(f"    envelope_apply_sides: {trial_requirements.config.envelope_apply_sides}")
            print("  rooms:")
            for idx, room in enumerate(trial_requirements.rooms):
                print(
                    f"    [{idx}] {room.type} "
                    f"(name={room.name}) "
                    f"min=({room.min_w}x{room.min_h}) "
                    f"max=({room.max_w}x{room.max_h})"
                )
            #print(f"  relation_constraints: {trial_requirements.relation_constraints}")
            print("-- end trial_requirements --\n\n")
            
            result = evaluator(trial_requirements, False)



            best_run_by_trial[trial.number] = result

            trial.set_user_attr("status", result.status)
            trial.set_user_attr("message", result.message)
            trial.set_user_attr("solved", result.solved)
            
            if not result.solved or result.score_report is None:
                trial.set_user_attr("valid", False)
                print("\n# Infeasible Result")
                return 0.0

            trial.set_user_attr("valid", result.score_report.valid)
            if not result.score_report.valid:
                trial.set_user_attr("hard_violations", result.score_report.hard_violations)
                print("\n# Invalid Score Report")
                return 0.0
            print("\nSolved + Score Passed")
            return float(result.score_report.total_score)
        finally:
            if tracking_context is not None:
                tracking_context.clear_trial_id()

    def optimization_callback(study: optuna.Study, trial: optuna.Trial) -> None:
        """Callback to check early stopping and timeout conditions after each trial."""
        if trial.value is None:
            return

        score = float(trial.value)

        # Check if score threshold reached (early stop condition)
        if controller.should_stop_optimization(score):
            study.stop()
            return

        # Check timeout
        try:
            controller.check_timeout_and_raise()
        except TrialTimeoutError:
            study.stop()
            raise

    sampler = optuna.samplers.TPESampler()

    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
    )

    study.optimize(objective, n_trials=n_trials, callbacks=[optimization_callback])

    failed_trials = 0
    for trial in study.trials[-n_trials:]:
        if float(trial.value or 0.0) <= 0.0:
            failed_trials += 1

    best_run = best_run_by_trial.get(study.best_trial.number)
    if best_run is None:
        best_trial_status = str(study.best_trial.user_attrs.get("status", ""))
        if best_trial_status in {"floor_bounds_infeasible", "precheck_failed", "mutate_requirements_infeasible"}:
            best_reason = str(study.best_trial.user_attrs.get("reason", best_trial_status))
            best_run = FpgEvaluationResult(
                solved=False,
                solution=[],
                score_report=None,
                status=best_trial_status,
                message=best_reason,
            )

    best_requirements: FpgRequirements | None = None
    if best_run is None:
        # The best trial can come from a previous run when load_if_exists=True.
        # Rebuild and evaluate it so callers always get coordinates.
        try:
            best_requirements = _requirements_from_best_params(
                base_requirements,
                dict(study.best_params),
                floor_dimension_bounds=floor_dimension_bounds,
            )
        except ValueError as exc:
            best_run = FpgEvaluationResult(
                solved=False,
                solution=[],
                score_report=None,
                status="mutate_requirements_infeasible",
                message=str(exc),
            )
            best_requirements = None

    if best_run is None and best_requirements is not None:
        ok, reason = _precheck(best_requirements)
        if ok:
            best_run = evaluator(best_requirements, False)
        else:
            best_run = FpgEvaluationResult(
                solved=False,
                solution=[],
                score_report=None,
                status="precheck_failed",
                message=reason,
            )

    return OptunaOptimizationResult(
        study_name=study.study_name,
        best_value=float(study.best_value),
        best_trial_number=int(study.best_trial.number),
        best_params=dict(study.best_params),
        completed_trials=len(study.trials),
        failed_trials=failed_trials,
        best_run=best_run,
    )
