from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, cast
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle


ROOM_TYPE_COLORS: dict[str, str] = {
    "bedroom": "#4e79a7",
    "kitchen": "#f28e2b",
    "bathroom": "#76b7b2",
    "livingroom": "#59a14f",
    "attachedbathroom": "#edc948",
    "veranda": "#b07aa1",
    "garage": "#9c755f",
    "diningroom": "#e15759",
    "hallway": "#7f7f7f",
    "generic": "#bab0ab",
}

ROOM_TYPE_LABELS: dict[str, str] = {
    "bedroom": "Bedroom",
    "kitchen": "Kitchen",
    "bathroom": "Bathroom",
    "livingroom": "Living Room",
    "attachedbathroom": "Attached Bath",
    "veranda": "Veranda",
    "garage": "Garage",
    "diningroom": "Dining Room",
    "hallway": "Hallway",
    "generic": "Room",
}


def _normalize_room_type(room_type: Any) -> str:
    value = str(room_type or "generic").strip()
    return value or "generic"


def _room_color(room_type: Any) -> str:
    normalized = _normalize_room_type(room_type)
    return ROOM_TYPE_COLORS.get(normalized.lower(), ROOM_TYPE_COLORS["generic"])


def _pretty_room_label(room_type: Any) -> str:
    normalized = _normalize_room_type(room_type).lower()
    return ROOM_TYPE_LABELS.get(normalized, str(room_type or "Room"))


def _collect_bounds(
    segments: list[dict[str, Any]],
) -> tuple[float, float, float, float] | None:
    points_x: list[float] = []
    points_y: list[float] = []
    for segment in segments:
        x1 = _safe_float(segment.get("x1"))
        y1 = _safe_float(segment.get("y1"))
        x2 = _safe_float(segment.get("x2"))
        y2 = _safe_float(segment.get("y2"))
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        points_x.extend([x1, x2])
        points_y.extend([y1, y2])

    if not points_x or not points_y:
        return None
    return min(points_x), min(points_y), max(points_x), max(points_y)


def _as_point_list(vertices: Any) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if not isinstance(vertices, list):
        return points
    for vertex in vertices:
        if isinstance(vertex, (tuple, list)) and len(vertex) >= 2:
            x = _safe_float(vertex[0])
            y = _safe_float(vertex[1])
        else:
            vertex_dict = _to_dict(vertex)
            x = _safe_float(vertex_dict.get("x"))
            y = _safe_float(vertex_dict.get("y"))
        if x is None or y is None:
            continue
        points.append((x, y))
    return points


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
    """Plot a room-colorized floor plan with a 10x10 grid and save it to test/outputs/final_results."""
    payload_dict = _to_dict(payload)
    rooms = payload_dict.get("rooms", {}) or {}
    doors = payload_dict.get("doors", []) or []
    windows = payload_dict.get("windows", []) or []
    global_openings = doors + windows

    output_dir = Path(__file__).resolve().parent.parent / "outputs" / "final_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 10), facecolor="#f8fafc")
    ax.set_facecolor("#ffffff")
    ax.set_axisbelow(True)

    x_points: list[float] = []
    y_points: list[float] = []
    legend_handles: list[Any] = []
    seen_legend_labels: set[str] = set()

    def add_legend_handle(handle: Any, label: str) -> None:
        if label in seen_legend_labels:
            return
        legend_handles.append(handle)
        seen_legend_labels.add(label)

    def add_room_legend(room_type: str, color: str) -> None:
        label = _pretty_room_label(room_type)
        add_legend_handle(Patch(facecolor=color, edgecolor=color, alpha=0.28), label)

    def plot_room_polygon(points: list[tuple[float, float]], room_type: str) -> None:
        if len(points) < 3:
            return
        color = _room_color(room_type)
        ax.add_patch(
            Polygon(
                points,
                closed=True,
                facecolor=color,
                edgecolor=color,
                linewidth=1.6,
                alpha=0.18,
                zorder=1,
                joinstyle="round",
            )
        )
        add_room_legend(room_type, color)

    def plot_room_label(cx: float, cy: float, room_name: Any, room_type: str) -> None:
        color = _room_color(room_type)
        ax.text(
            cx,
            cy,
            f"{room_name}\n{_pretty_room_label(room_type)}",
            fontsize=8.5,
            fontweight="bold",
            ha="center",
            va="center",
            color="#111827",
            bbox={
                "boxstyle": "round,pad=0.28",
                "facecolor": "white",
                "edgecolor": color,
                "alpha": 0.96,
            },
            zorder=6,
        )

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
        ax.plot(
            [x1, x2],
            [y1, y2],
            color="#1f2937",
            linewidth=1.8,
            alpha=0.7,
            zorder=4,
        )
        x_points.extend([x1, x2])
        y_points.extend([y1, y2])

    add_legend_handle(Line2D([0], [0], color="#1f2937", linewidth=1.8), "Wall")

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
        color = "#2563eb" if is_window else "#dc2626"
        linestyle = "--" if is_window else "-"
        ax.plot(
            [x1, x2],
            [y1, y2],
            color=color,
            linewidth=4.5,
            linestyle=linestyle,
            alpha=0.95,
            solid_capstyle="round",
            zorder=5,
        )
        x_points.extend([x1, x2])
        y_points.extend([y1, y2])

    add_legend_handle(Line2D([0], [0], color="#dc2626", linewidth=4.5), "Door")
    add_legend_handle(
        Line2D([0], [0], color="#2563eb", linewidth=4.5, linestyle="--"), "Window"
    )

    floor_plan_obj = _to_dict(payload_dict.get("floor_plan_with_openings"))
    floor_plan_entries = floor_plan_obj.get("floor_plan", []) if floor_plan_obj else []
    if isinstance(floor_plan_entries, dict):
        floor_plan_entries = list(floor_plan_entries.values())

    for room_entry in floor_plan_entries or []:
        room = _to_dict(room_entry)
        room_name = room.get("name") or room.get("room_name") or "Room"
        room_type = _normalize_room_type(room.get("type") or room.get("room_type"))
        vertices = _as_point_list(room.get("vertices", []))
        if vertices:
            plot_room_polygon(vertices, room_type)
            xs = [point[0] for point in vertices]
            ys = [point[1] for point in vertices]
            x_points.extend(xs)
            y_points.extend(ys)
            plot_room_label(sum(xs) / len(xs), sum(ys) / len(ys), room_name, room_type)
            continue

        x = _safe_float(room.get("x"))
        y = _safe_float(room.get("y"))
        x_end = _safe_float(room.get("x_end"))
        y_end = _safe_float(room.get("y_end"))
        if x is not None and y is not None and x_end is not None and y_end is not None:
            plot_room_polygon(
                [(x, y), (x_end, y), (x_end, y_end), (x, y_end)], room_type
            )
            x_points.extend([x, x_end])
            y_points.extend([y, y_end])
            plot_room_label((x + x_end) / 2, (y + y_end) / 2, room_name, room_type)

    for room_name, room_value in rooms.items():
        room = _to_dict(room_value)
        walls = room.get("room_walls", []) or []
        openings = room.get("openings", []) or []
        room_type = _normalize_room_type(
            room.get("room_type") or room.get("type") or "generic"
        )
        room_color = _room_color(room_type)

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

        room_bounds = _collect_bounds([_to_dict(wall_value) for wall_value in walls])
        if room_bounds is not None:
            x_min_room, y_min_room, x_max_room, y_max_room = room_bounds
            width = x_max_room - x_min_room
            height = y_max_room - y_min_room
            if width > 0 and height > 0:
                ax.add_patch(
                    Rectangle(
                        (x_min_room, y_min_room),
                        width,
                        height,
                        facecolor=room_color,
                        edgecolor=room_color,
                        linewidth=1.1,
                        alpha=0.10,
                        zorder=0,
                    )
                )
                add_room_legend(room_type, room_color)

        for opening_value in openings:
            opening = _to_dict(opening_value)
            x1 = _safe_float(opening.get("x1"))
            y1 = _safe_float(opening.get("y1"))
            x2 = _safe_float(opening.get("x2"))
            y2 = _safe_float(opening.get("y2"))
            if x1 is None or y1 is None or x2 is None or y2 is None:
                continue
            opening_type = (opening.get("opening_type") or "opening").lower()
            color = "#2563eb" if "window" in opening_type else "#dc2626"
            ax.plot(
                [x1, x2],
                [y1, y2],
                color=color,
                linewidth=4.5,
                alpha=0.95,
                solid_capstyle="round",
                zorder=5,
            )
            x_points.extend([x1, x2])
            y_points.extend([y1, y2])

        if room_x and room_y:
            cx = sum(room_x) / len(room_x)
            cy = sum(room_y) / len(room_y)
            plot_room_label(cx, cy, room_name, room_type)

    if not x_points or not y_points:
        plt.close(fig)
        return None

    pad = 0.5
    ax.set_aspect("equal", adjustable="box")
    x_min, x_max = min(x_points) - pad, max(x_points) + pad
    y_min, y_max = min(y_points) - pad, max(y_points) + pad
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.margins(0.02)

    # Use a 10x10 unit grid scale
    x_grid_start = math.floor(x_min / 10) * 10
    x_grid_end = math.ceil(x_max / 10) * 10
    y_grid_start = math.floor(y_min / 10) * 10
    y_grid_end = math.ceil(y_max / 10) * 10
    ax.set_xticks(list(range(int(x_grid_start), int(x_grid_end) + 1, 10)))
    ax.set_yticks(list(range(int(y_grid_start), int(y_grid_end) + 1, 10)))
    ax.grid(which="major", color="#dbeafe", linestyle="--", linewidth=0.8, alpha=0.95)
    ax.tick_params(axis="both", labelsize=9, colors="#374151")

    for spine in ax.spines.values():
        spine.set_color("#6b7280")
        spine.set_linewidth(1.0)

    ax.set_title("Floor Plan Preview", fontsize=15, fontweight="bold", pad=12)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    if legend_handles:
        ax.legend(
            handles=legend_handles,
            loc="upper left",
            bbox_to_anchor=(1.02, 1.0),
            frameon=True,
            framealpha=0.97,
            title="Legend",
            borderaxespad=0.0,
        )

    timestamp = datetime.now().strftime("%m%d%H-%M-%S")
    output_path = output_dir / f"{timestamp}.png"
    fig.tight_layout(rect=(0, 0, 0.82, 1))
    fig.savefig(output_path, dpi=200)

    if show:
        plt.show()

    plt.close(fig)
    return str(output_path)


def plot_final_floor_plan(payload: Mapping[str, Any], show: bool = False) -> str | None:
    """Public-facing plotter for final API results."""
    return plot_floor_plan_payload(payload, show=show)


def _build_payload_from_solver_result(run_result: Any) -> dict[str, Any]:
    """Reconstruct payload format from an FpgEvaluationResult using the new union results flow."""
    if not run_result or not getattr(run_result, "solved", False):
        return {
            "status": getattr(run_result, "status", "ERROR"),
            "message": getattr(run_result, "message", ""),
            "union_walls": [],
            "rooms": {},
            "doors": [],
            "windows": [],
        }

    # New flow: use union_results
    union_results_obj = getattr(run_result, "union_results", None)
    if not union_results_obj:
        return {
            "status": run_result.status,
            "message": run_result.message,
            "union_walls": [],
            "rooms": {},
            "doors": [],
            "windows": [],
        }

    try:
        unified_floor_plan = union_results_obj.get("unified_floor_plan")
        floor_plan_with_openings = union_results_obj.get("floor_plan_with_openings")
    except (KeyError, TypeError, AttributeError):
        return {
            "status": run_result.status,
            "message": run_result.message,
            "union_walls": [],
            "rooms": {},
            "doors": [],
            "windows": [],
        }

    if not unified_floor_plan or not floor_plan_with_openings:
        return {
            "status": run_result.status,
            "message": run_result.message,
            "union_walls": [],
            "rooms": {},
            "doors": [],
            "windows": [],
        }

    # Extract walls from unified floor plan
    union_walls = unified_floor_plan.get("walls", [])

    # Extract openings and rooms from floor_plan_with_openings
    floor_plan = getattr(
        floor_plan_with_openings, "floor_plan", None
    ) or floor_plan_with_openings.get("floor_plan", [])
    openings = getattr(
        floor_plan_with_openings, "openings", None
    ) or floor_plan_with_openings.get("openings", [])

    # Build rooms dictionary from floor_plan
    rooms = {}
    for room in floor_plan or []:
        room_dict = _to_dict(room) if not isinstance(room, dict) else room
        room_name = room_dict.get("name", "unknown")
        room_type = room_dict.get("type", "generic")
        rooms[room_name] = {
            "room_name": room_name,
            "room_type": room_type,
            "room_walls": [],  # Walls already unified in union_walls
        }

    # Separate doors and windows from openings
    doors = []
    windows = []
    for opening in openings or []:
        opening_dict = _to_dict(opening) if not isinstance(opening, dict) else opening
        opening_type = opening_dict.get("opening_type", "door")
        if "window" in opening_type.lower():
            windows.append(opening_dict)
        else:
            doors.append(opening_dict)

    return {
        "status": run_result.status,
        "message": run_result.message,
        "union_walls": union_walls,
        "unified_floor_plan": unified_floor_plan,
        "floor_plan_with_openings": floor_plan_with_openings,
        "rooms": rooms,
        "doors": doors,
        "windows": windows,
    }


def plot_final_solver_result(run_result: Any, show: bool = False) -> str | None:
    """Builds final payload from solver result and renders it with final plotter."""
    payload = _build_payload_from_solver_result(run_result)
    return plot_final_floor_plan(payload, show=show)
