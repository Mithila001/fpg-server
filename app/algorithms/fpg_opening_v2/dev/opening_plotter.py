from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.algorithms.types.domain import FpgRequirements, ProcessedRoomData
from app.algorithms.types.openings import OpeningData


def _opening_color(opening_type: str) -> str:
    mapping = {
        "mainDoor": "tab:red",
        "internalDoor": "tab:orange",
        "backDoor": "tab:purple",
        "window": "tab:blue",
    }
    return mapping.get(opening_type, "tab:gray")


def fpg_opening_results_plotter(
    requirements: FpgRequirements | None,
    floor_plan: list[ProcessedRoomData],
    openings: list[OpeningData],
    output_dir: str | Path | None = None,
) -> str | None:
    if not floor_plan:
        return None

    project_root = Path(__file__).resolve().parents[4]
    output_path = (
        Path(output_dir)
        if output_dir is not None
        else project_root / "test" / "outputs" / "openings"
    )
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_path / f"fpg_openings_{timestamp}.png"

    fig, ax = plt.subplots(figsize=(12, 12))
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for room in floor_plan:
        xs = [point[0] for point in room.vertices]
        ys = [point[1] for point in room.vertices]
        if not xs or not ys:
            continue
        min_x = min(min_x, min(xs))
        min_y = min(min_y, min(ys))
        max_x = max(max_x, max(xs))
        max_y = max(max_y, max(ys))
        poly_x = xs + [xs[0]]
        poly_y = ys + [ys[0]]
        ax.plot(poly_x, poly_y, color="black", linewidth=1.5)
        ax.text(
            sum(xs) / len(xs),
            sum(ys) / len(ys),
            f"{room.name}\n{room.type}",
            fontsize=8,
            ha="center",
            va="center",
        )

    for opening in openings:
        ax.plot(
            [opening.x1, opening.x2],
            [opening.y1, opening.y2],
            color=_opening_color(opening.opening_type),
            linewidth=3.0,
        )

    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    margin = max(width, height) * 0.05
    ax.set_xlim(min_x - margin, max_x + margin)
    ax.set_ylim(min_y - margin, max_y + margin)
    ax.set_aspect("equal", adjustable="box")
    title = "FPG Opening V2"
    if requirements is not None:
        title = f"{title} ({requirements.config.floor_plan_width}x{requirements.config.floor_plan_height})"
    ax.set_title(title)
    ax.grid(True, linewidth=0.3, alpha=0.5)
    plt.tight_layout()
    fig.savefig(file_path, dpi=180)
    plt.close(fig)
    return str(file_path)
