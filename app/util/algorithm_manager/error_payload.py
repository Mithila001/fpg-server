from typing import Any

EMPTY_POST_PROCESS_LAYOUT = {
    "union_walls": [],
    "rooms": {},
    "doors": [],
    "windows": [],
}


def error_payload(message: str, status: str = "ERROR") -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "union_walls": [],
        "rooms": {},
        "doors": [],
        "windows": [],
    }
