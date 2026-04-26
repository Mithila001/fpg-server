from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, cast
import math

import matplotlib.pyplot as plt

from app.algorithms.fpg_opening import generate_openings
from app.algorithms.fpg_rooms.fpg_post_process import run_final_post_process


def _to_dict(value: Any) -> dict[str, Any]:
    """Normalize pydantic models or objects into plain dictionaries."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast(dict[str, Any], model_dump())
    if hasattr(value, "__dict__"):
        return {str(key): item for key, item in value.__dict__.items()}
    return {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def plot_floor_plan_payload(
    payload: Mapping[str, Any], show: bool = False
) -> str | None:
    """Plot walls, separate doors/windows, and room labels from API payload and save image to test/outputs/final_results."""
    payload_dict = _to_dict(payload)
    rooms = payload_dict.get("rooms", {}) or {}
    doors = payload_dict.get("doors", []) or []
    windows = payload_dict.get("windows", []) or []
    global_openings = doors + windows

    output_dir = Path(__file__).resolve().parent.parent / "outputs" / "final_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))

    x_points: list[float] = []
    y_points: list[float] = []

    # Draw latest solver union walls, with fallback to legacy root-level walls
    global_walls = (
        payload_dict.get("union_walls") or payload_dict.get("walls", []) or []
    )
    for wall in global_walls:
        wall = _to_dict(wall)
        x1 = _safe_float(wall.get("x1"))
        y1 = _safe_float(wall.get("y1"))
        x2 = _safe_float(wall.get("x2"))
        y2 = _safe_float(wall.get("y2"))
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.2, alpha=0.55)
        x_points.extend([x1, x2])
        y_points.extend([y1, y2])

    # Plot doors and windows separately for clarity
    for opening in global_openings:
        opening = _to_dict(opening)
        x1 = _safe_float(opening.get("x1"))
        y1 = _safe_float(opening.get("y1"))
        x2 = _safe_float(opening.get("x2"))
        y2 = _safe_float(opening.get("y2"))
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        opening_type = (opening.get("opening_type") or "opening").lower()
        is_window = "window" in opening_type
        color = "tab:blue" if is_window else "tab:red"
        linestyle = "--" if is_window else "-"
        ax.plot(
            [x1, x2],
            [y1, y2],
            color=color,
            linewidth=4,
            linestyle=linestyle,
            alpha=0.95,
        )
        x_points.extend([x1, x2])
        y_points.extend([y1, y2])

    for room_name, room_value in rooms.items():
        room = _to_dict(room_value)
        walls = room.get("room_walls", []) or []
        openings = room.get("openings", []) or []

        room_x: list[float] = []
        room_y: list[float] = []

        for wall_value in walls:
            wall = _to_dict(wall_value)
            x1 = _safe_float(wall.get("x1"))
            y1 = _safe_float(wall.get("y1"))
            x2 = _safe_float(wall.get("x2"))
            y2 = _safe_float(wall.get("y2"))
            if x1 is None or y1 is None or x2 is None or y2 is None:
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
            if x1 is None or y1 is None or x2 is None or y2 is None:
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

    # Use a 10x10 unit grid scale
    x_grid_start = math.floor(x_min / 10) * 10
    x_grid_end = math.ceil(x_max / 10) * 10
    y_grid_start = math.floor(y_min / 10) * 10
    y_grid_end = math.ceil(y_max / 10) * 10
    ax.set_xticks(list(range(int(x_grid_start), int(x_grid_end) + 1, 10)))
    ax.set_yticks(list(range(int(y_grid_start), int(y_grid_end) + 1, 10)))
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


def plot_final_floor_plan(payload: Mapping[str, Any], show: bool = False) -> str | None:
    """Public-facing plotter for final API results."""
    return plot_floor_plan_payload(payload, show=show)


def _build_payload_from_solver_result(run_result: Any) -> dict[str, Any]:
    """Reconstruct payload format used by API from an FpgEvaluationResult."""
    if not run_result or not getattr(run_result, "solved", False):
        return {
            "status": getattr(run_result, "status", "ERROR"),
            "message": getattr(run_result, "message", ""),
            "union_walls": [],
            "rooms": {},
            "doors": [],
            "windows": [],
        }

    quick_post_process_result = getattr(run_result, "quick_post_process_result", None)
    if quick_post_process_result is not None:
        post_processed_layout = quick_post_process_result.get("rooms", [])
        wall_union_result = quick_post_process_result.get(
            "wall_union",
            {
                "walls": [],
                "room_walls": {},
            },
        )
    else:
        post_processed_layout = getattr(run_result, "solution", [])
        wall_union_result = {"walls": [], "room_walls": {}}

    opening_result = generate_openings(post_processed_layout)
    post_process_result = run_final_post_process(
        {
            "rooms": post_processed_layout,
            "openings": opening_result.get("openings", []),
            "wall_union": wall_union_result,
        }
    )

    return {
        "status": run_result.status,
        "message": run_result.message,
        "union_walls": post_process_result.get("union_walls", []),
        "rooms": post_process_result.get("rooms", {}),
        "doors": post_process_result.get("doors", []),
        "windows": post_process_result.get("windows", []),
    }


def plot_final_solver_result(run_result: Any, show: bool = False) -> str | None:
    """Builds final payload from solver result and renders it with final plotter."""
    payload = _build_payload_from_solver_result(run_result)
    return plot_final_floor_plan(payload, show=show)
