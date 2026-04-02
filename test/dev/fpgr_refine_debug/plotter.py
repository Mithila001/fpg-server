from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from app.util.tracking import get_tracking_label


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _room_bounds(room: dict[str, Any]) -> tuple[float, float, float, float] | None:
    x = _safe_float(room.get("x"))
    y = _safe_float(room.get("y"))
    x_end = _safe_float(room.get("x_end"))
    y_end = _safe_float(room.get("y_end"))

    if None in (x, y, x_end, y_end):
        return None
    if x_end <= x or y_end <= y:
        return None
    return x, y, x_end, y_end


def _draw_plan(ax: Any, rooms: list[dict[str, Any]], title: str) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []

    for room in rooms:
        bounds = _room_bounds(room)
        if bounds is None:
            continue

        x, y, x_end, y_end = bounds
        w = x_end - x
        h = y_end - y

        rect = Rectangle(
            (x, y),
            w,
            h,
            fill=False,
            edgecolor="black",
            linewidth=1.2,
        )
        ax.add_patch(rect)

        room_name = str(room.get("name") or "room")
        ax.text(x + w / 2.0, y + h / 2.0, room_name, ha="center", va="center", fontsize=8)

        xs.extend([x, x_end])
        ys.extend([y, y_end])

    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
    ax.xaxis.set_major_locator(plt.MultipleLocator(10))
    ax.yaxis.set_major_locator(plt.MultipleLocator(10))

    return xs, ys


def plot_refine_before_after(
    before_rooms: list[dict[str, Any]],
    after_rooms: list[dict[str, Any]],
    show: bool = False,
) -> str | None:
    """Plot FPGR refine before/after layouts side by side and save image to output folder."""
    if not before_rooms and not after_rooms:
        return None

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    before_x, before_y = _draw_plan(axes[0], before_rooms, "Before Refine")
    after_x, after_y = _draw_plan(axes[1], after_rooms, "After Refine")

    all_x = before_x + after_x
    all_y = before_y + after_y

    if not all_x or not all_y:
        plt.close(fig)
        return None

    pad = 1.0
    x_min = min(all_x) - pad
    x_max = max(all_x) + pad
    y_min = min(all_y) - pad
    y_max = max(all_y) + pad

    for ax in axes:
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

    tracking_label = get_tracking_label()
    if tracking_label:
        fig.suptitle(f"FPGR Refine Debug Plot\n{tracking_label}", fontsize=12)
        fig.text(
            0.01,
            0.01,
            tracking_label,
            ha="left",
            va="bottom",
            fontsize=9,
            family="monospace",
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
        )
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    else:
        fig.suptitle("FPGR Refine Debug Plot", fontsize=12)
        fig.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"fpgr_refine_{timestamp}.png"
    fig.savefig(output_path, dpi=200)

    if show:
        plt.show()

    plt.close(fig)
    return str(output_path)
