from __future__ import annotations

from typing import Any

from .types import NormalizedRoom


def normalize_solution_rooms(solution: list[dict[str, Any]]) -> list[NormalizedRoom]:
    """Normalize solver room records to a strict geometry payload.

    Invalid or degenerate room records are skipped so one bad room does not
    break the full post-processing output.
    """
    normalized: list[NormalizedRoom] = []

    for idx, room in enumerate(solution):
        try:
            x = float(room["x"])
            y = float(room["y"])

            w = room.get("w")
            h = room.get("h")
            x_end = room.get("x_end")
            y_end = room.get("y_end")

            if x_end is None:
                if w is None:
                    continue
                x_end = x + float(w)
            else:
                x_end = float(x_end)

            if y_end is None:
                if h is None:
                    continue
                y_end = y + float(h)
            else:
                y_end = float(y_end)

            if x_end <= x or y_end <= y:
                continue

            normalized.append(
                {
                    "name": str(room.get("name") or f"room_{idx}"),
                    "type": str(room.get("type") or ""),
                    "x": x,
                    "y": y,
                    "x_end": x_end,
                    "y_end": y_end,
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    return normalized
