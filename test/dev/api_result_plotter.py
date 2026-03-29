from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import matplotlib.pyplot as plt


def _to_dict(value: Any) -> dict[str, Any]:
    """Normalize pydantic models or objects into plain dictionaries."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return dict(value.__dict__) if hasattr(value, "__dict__") else {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def plot_floor_plan_payload(payload: Mapping[str, Any], show: bool = False) -> str | None:
    """Plot walls, openings, and room labels from API payload and save image to test/dev/output."""
    payload_dict = _to_dict(payload)
    rooms = payload_dict.get("compact_by_room", {}) or {}

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))

    x_points: list[float] = []
    y_points: list[float] = []

    # Draw global walls from Rooms Solver to ensure scheme based on root-level walls
    global_walls = payload_dict.get("walls", []) or []
    for wall in global_walls:
        wall = _to_dict(wall)
        x1 = _safe_float(wall.get("x1"))
        y1 = _safe_float(wall.get("y1"))
        x2 = _safe_float(wall.get("x2"))
        y2 = _safe_float(wall.get("y2"))
        if None in (x1, y1, x2, y2):
            continue
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.2, alpha=0.55)
        x_points.extend([x1, x2])
        y_points.extend([y1, y2])

    # Optional opening list at root if solver provides opening segments outside rooms
    global_openings = payload_dict.get("openings", []) or []
    for opening in global_openings:
        opening = _to_dict(opening)
        x1 = _safe_float(opening.get("x1"))
        y1 = _safe_float(opening.get("y1"))
        x2 = _safe_float(opening.get("x2"))
        y2 = _safe_float(opening.get("y2"))
        if None in (x1, y1, x2, y2):
            continue
        opening_type = (opening.get("opening_type") or "opening").lower()
        color = "tab:blue" if "window" in opening_type else "tab:red"
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=4, linestyle="--", alpha=0.95)
        x_points.extend([x1, x2])
        y_points.extend([y1, y2])

    for room_name, room_value in rooms.items():
        room = _to_dict(room_value)
        walls = room.get("walls", []) or []
        openings = room.get("openings", []) or []

        room_x: list[float] = []
        room_y: list[float] = []

        for wall_value in walls:
            wall = _to_dict(wall_value)
            x1 = _safe_float(wall.get("x1"))
            y1 = _safe_float(wall.get("y1"))
            x2 = _safe_float(wall.get("x2"))
            y2 = _safe_float(wall.get("y2"))
            if None in (x1, y1, x2, y2):
                continue
            ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.2, alpha=0.55)
            room_x.extend([x1, x2])
            room_y.extend([y1, y2])
            x_points.extend([x1, x2])
            y_points.extend([y1, y2])

        for opening_value in openings:
            opening = _to_dict(opening_value)
            x1 = _safe_float(opening.get("x1"))
            y1 = _safe_float(opening.get("y1"))
            x2 = _safe_float(opening.get("x2"))
            y2 = _safe_float(opening.get("y2"))
            if None in (x1, y1, x2, y2):
                continue
            opening_type = (opening.get("opening_type") or "opening").lower()
            color = "tab:blue" if "window" in opening_type else "tab:red"
            ax.plot([x1, x2], [y1, y2], color=color, linewidth=4, alpha=0.95)
            x_points.extend([x1, x2])
            y_points.extend([y1, y2])

        if room_x and room_y:
            cx = sum(room_x) / len(room_x)
            cy = sum(room_y) / len(room_y)
            ax.text(cx, cy, str(room_name), fontsize=9, ha="center", va="center")

    if not x_points or not y_points:
        plt.close(fig)
        return None

    pad = 0.5
    ax.set_aspect("equal", adjustable="box")
    x_min, x_max = min(x_points) - pad, max(x_points) + pad
    y_min, y_max = min(y_points) - pad, max(y_points) + pad
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # Use a 1x1 unit grid scale
    ax.set_xticks([x for x in range(int(x_min), int(x_max) + 2)])
    ax.set_yticks([y for y in range(int(y_min), int(y_max) + 2)])
    ax.grid(which="both", color="gray", linestyle="--", linewidth=0.5, alpha=0.5)

    ax.set_title("Floor Plan Preview")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    timestamp = datetime.now().strftime("%m%d%H-%M-%S")
    output_path = output_dir / f"{timestamp}.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)

    if show:
        plt.show()
    plt.close(fig)
    return str(output_path)

