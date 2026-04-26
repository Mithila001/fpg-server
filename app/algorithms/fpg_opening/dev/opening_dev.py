from __future__ import annotations

import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches

from app.algorithms.fpg_opening.generator import generate_openings


def run_dev_main_door_plot(
    mock_data_path: str | Path = "app/algorithms/fpg_opening/dev/mock_data.json",
    output_path: str | Path = "app/algorithms/fpg_opening/dev/main_door_plot.png",
    grid_size: float = 8.0,
) -> dict:
    """Pick a random mock result, generate main doors, and save a plot.

    The mock data matches the output of ``snap_solution_rooms_to_grid``.
    """
    mock_path = Path(mock_data_path)
    if not mock_path.exists():
        raise FileNotFoundError(f"Mock data file not found: {mock_path}")

    raw = json.loads(mock_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) == 0:
        raise ValueError("Mock data file must contain a non-empty list")

    chosen = random.choice(raw)
    rooms_solver = chosen.get("rooms_solver")
    if rooms_solver is None:
        raise ValueError("Selected entry does not contain 'rooms_solver'")

    # The generator expects list[dict[str, Any]] room data
    result = generate_openings(fpg_room_requirements=rooms_solver, tolerance=1e-6)

    # Plot the rectangles and openings
    fig, ax = plt.subplots(figsize=(8, 8))

    # determine bounds
    min_x = min(room["x"] for room in rooms_solver)
    min_y = min(room["y"] for room in rooms_solver)
    max_x = max(
        room.get("x_end", room["x"] + room.get("w", 0)) for room in rooms_solver
    )
    max_y = max(
        room.get("y_end", room["y"] + room.get("h", 0)) for room in rooms_solver
    )

    for room in rooms_solver:
        x = float(room["x"])
        y = float(room["y"])
        w = float(room.get("w", room.get("x_end", x) - x))
        h = float(room.get("h", room.get("y_end", y) - y))

        rect = patches.Rectangle(
            (x, y), w, h, linewidth=1, edgecolor="gray", facecolor="none"
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2,
            y + h / 2,
            room.get("name", ""),
            ha="center",
            va="center",
            fontsize=8,
        )

    for opening in result.get("openings", []):
        x1 = opening.get("x1")
        y1 = opening.get("y1")
        x2 = opening.get("x2")
        y2 = opening.get("y2")
        if x1 is None or y1 is None or x2 is None or y2 is None:
            continue
        opening_type = str(opening.get("opening_type", "opening"))
        color = "red" if opening_type == "mainDoor" else "blue"
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=3, solid_capstyle="round")
        ax.text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            opening_type,
            color=color,
            fontsize=8,
            ha="center",
            va="center",
        )

    ax.set_title("FPG Opening Dev: Opening Selection")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_xlim(min_x - grid_size, max_x + grid_size)
    ax.set_ylim(min_y - grid_size, max_y + grid_size)
    ax.set_aspect("equal", adjustable="box")

    from datetime import datetime

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%m%d%H-%M-%S")
    output_file = output_dir / f"main_door_plot_{timestamp}.png"

    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return {
        "mock_data_path": str(mock_path),
        "selected_index": raw.index(chosen),
        "status": result.get("status"),
        "message": result.get("message"),
        "openings": result.get("openings"),
        "warnings": result.get("warnings"),
        "plot_file": str(output_file),
    }
