from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from app.algorithms.types_new import RoomType

from ..context import ScoringContext
from ..exceptions import ScoringInputError


@dataclass(frozen=True, slots=True)
class EvaluationPoint:
    room_id: str
    room_type: RoomType
    name: str
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class EvaluationData:
    floor_width: float
    floor_length: float
    points: tuple[EvaluationPoint, ...]


def build_evaluation_data(context: ScoringContext) -> EvaluationData:
    """Convert supported project/domain shapes into evaluator-friendly data.

    The adapter supports the planned typed structures as well as mapping-based
    fixtures. It intentionally lives outside individual evaluators so each
    evaluator sees one stable internal representation.
    """

    specification = context.scoring_input.specification
    candidate = context.scoring_input.candidate
    floor_width, floor_length = _extract_floor_size(specification)
    room_metadata = _extract_room_metadata(specification)
    points = _extract_candidate_points(candidate, room_metadata)

    return EvaluationData(
        floor_width=floor_width,
        floor_length=floor_length,
        points=tuple(points),
    )


def setting_float(settings: Mapping[str, Any], key: str, default: float) -> float:
    value = settings.get(key, default)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Setting '{key}' must be finite.")
    return result


def setting_int(settings: Mapping[str, Any], key: str, default: int) -> int:
    value = int(settings.get(key, default))
    return value


def setting_mapping(
    settings: Mapping[str, Any], key: str, default: Mapping[str, Any]
) -> Mapping[str, Any]:
    value = settings.get(key, default)
    if not isinstance(value, Mapping):
        raise ValueError(f"Setting '{key}' must be a mapping.")
    return value


def require_room_type(value: Any, label: str) -> RoomType:
    if not isinstance(value, RoomType):
        raise ScoringInputError(f"{label} must be a RoomType enum member.")
    return value


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def distance(a: EvaluationPoint, b: EvaluationPoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _extract_floor_size(specification: Any) -> tuple[float, float]:
    floor = _get(specification, "floor")
    config = _get(specification, "config")

    width = _first_not_none(
        _get(floor, "width"),
        _get(specification, "floor_width"),
        _get(specification, "width"),
        _get(config, "floor_plan_width"),
    )
    length = _first_not_none(
        _get(floor, "length"),
        _get(specification, "floor_length"),
        _get(specification, "length"),
        _get(config, "floor_plan_length"),
    )

    if width is None or length is None:
        raise ValueError("Could not determine floor width and length from specification.")

    floor_width = float(width)
    floor_length = float(length)
    if not math.isfinite(floor_width) or floor_width <= 0:
        raise ValueError("Floor width must be a finite positive value.")
    if not math.isfinite(floor_length) or floor_length <= 0:
        raise ValueError("Floor length must be a finite positive value.")
    return floor_width, floor_length


def _extract_room_metadata(specification: Any) -> dict[str, tuple[RoomType, str]]:
    rooms = _get(specification, "rooms") or ()
    metadata: dict[str, tuple[str, str]] = {}
    for index, room in enumerate(_iterable(rooms)):
        room_id = str(_first_not_none(_get(room, "id"), _get(room, "name"), index))
        name = str(_first_not_none(_get(room, "name"), room_id))
        raw_type = _first_not_none(_get(room, "room_type"), _get(room, "type"))
        if raw_type is None:
            continue
        room_type = require_room_type(raw_type, f"Room '{room_id}' room_type")
        metadata[room_id] = (room_type, name)
        metadata.setdefault(name, (room_type, name))
    return metadata


def _extract_candidate_points(
    candidate: Any,
    room_metadata: Mapping[str, tuple[RoomType, str]],
) -> list[EvaluationPoint]:
    raw_points = _first_not_none(
        _get(candidate, "candidate_points"),
        _get(candidate, "points"),
        _get(candidate, "positions"),
        candidate,
    )

    if isinstance(raw_points, Mapping):
        items: Iterable[tuple[Any, Any]] = raw_points.items()
    else:
        items = enumerate(_iterable(raw_points))

    points: list[EvaluationPoint] = []
    seen_ids: set[str] = set()
    for fallback_key, value in items:
        room_id = str(
            _first_not_none(
                _get(value, "room_id"),
                _get(value, "id"),
                fallback_key,
            )
        )
        metadata = room_metadata.get(room_id)
        name = str(_first_not_none(_get(value, "name"), metadata[1] if metadata else None, room_id))
        raw_type = _first_not_none(
            _get(value, "room_type"),
            _get(value, "type"),
            metadata[0] if metadata else None,
        )
        if raw_type is None:
            raise ValueError(f"Candidate point '{room_id}' has no room type.")

        x, y = _extract_xy(value)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"Candidate point '{room_id}' has non-finite coordinates.")
        if room_id in seen_ids:
            raise ValueError(f"Candidate point '{room_id}' is duplicated.")
        seen_ids.add(room_id)

        points.append(
            EvaluationPoint(
                room_id=room_id,
                room_type=require_room_type(
                    raw_type, f"Candidate point '{room_id}' room_type"
                ),
                name=name,
                x=x,
                y=y,
            )
        )
    return points


def _extract_xy(value: Any) -> tuple[float, float]:
    position = _get(value, "position")
    if position is not None:
        return _extract_xy(position)

    x = _get(value, "x")
    y = _get(value, "y")
    if x is not None and y is not None:
        return float(x), float(y)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) >= 2:
            return float(value[0]), float(value[1])

    raise ValueError(f"Could not extract x/y coordinates from candidate value: {value!r}")


def _get(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _iterable(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return value.values()
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return value
    raise ValueError(f"Expected an iterable value, received {type(value).__name__}.")
