from __future__ import annotations

from typing import Final


CARDINAL_SIDES: Final[tuple[str, ...]] = ("south", "east", "north", "west")
GEOMETRIC_TOLERANCE: Final[float] = 1e-6

BACK_DOOR_ELIGIBLE_ROOM_TYPES: Final[frozenset[str]] = frozenset({"kitchen", "hallway"})
BACK_DOOR_ROOM_TYPE_PRIORITY: Final[dict[str, int]] = {
	"kitchen": 0,
	"hallway": 1,
}

INTERNAL_DOOR_ALLOWED_ROOM_PAIRS: Final[frozenset[frozenset[str]]] = frozenset(
	{
		frozenset(("bedroom", "livingroom")),
		frozenset(("kitchen", "livingroom")),
		frozenset(("bathroom", "livingroom")),
		frozenset(("bedroom", "attachedbathroom")),
		frozenset(("veranda", "livingroom")),
	}
)

MAX_INTERNAL_DOORS_BY_ROOM_TYPE: Final[dict[str, int]] = {
	"bedroom": 2,
	"bathroom": 1,
	"livingroom": 10,
	"hallway": 10,
	"kitchen": 1,
	"attachedbathroom": 1,
	"veranda": 1,
}

WINDOW_ELIGIBLE_ROOM_TYPES: Final[frozenset[str]] = frozenset(
	{"bedroom", "livingroom", "kitchen"}
)


def normalize_room_type(room_type: str) -> str:
	return room_type.strip().lower()
