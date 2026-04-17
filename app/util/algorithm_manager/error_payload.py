from typing import Any

EMPTY_POST_PROCESS_LAYOUT = {
    "walls": [],
    "compact_by_room": {},
    "metadata": {
        "veranda": None,
        "garage_shared_horizontal_overlap_segment": None,
        "hallway_living_shared_walls": [],
        "converted_hallway_living_openings": 0,
    },
}


def error_payload(message: str, status: str = "ERROR") -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "walls": [],
        "compact_by_room": {},
        "metadata": EMPTY_POST_PROCESS_LAYOUT["metadata"],
    }
