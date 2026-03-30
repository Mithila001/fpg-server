from __future__ import annotations

import os
from time import perf_counter
from typing import Any

from app.algorithms.fp_boundary_finder import FPBoundaryFinder
from app.algorithms.usable_land_space_finder import find_usable_land_space
from app.util.logger import SystemLogger


def _error_payload(message: str, status: str = "ERROR") -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "buildable_rectangle": None,
        "shrunk_boundary": None,
        "metadata": None,
    }


def _extract_polygon_coordinates(land_data: dict[str, Any]) -> list[tuple[float, float]]:
    raw_points = [
        (point["x"], point["y"])
        for point in land_data.get("segmentsCoordinates", [])
        if "x" in point and "y" in point
    ]

    if len(raw_points) < 3:
        raise ValueError("At least 3 land boundary points are required.")

    # Remove duplicated closing coordinate if present.
    if len(raw_points) > 1 and raw_points[0] == raw_points[-1]:
        raw_points = raw_points[:-1]

    if len(raw_points) < 3:
        raise ValueError("Boundary points are invalid after normalization.")

    return raw_points


def _extract_ta_line(land_data: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    roads = land_data.get("roadConnected", [])
    for road in roads:
        segment = road.get("segment", [])
        if len(segment) >= 2:
            return (
                (segment[0]["x"], segment[0]["y"]),
                (segment[1]["x"], segment[1]["y"]),
            )

    raise ValueError("No valid TA segment found in land data.")


def _rectangle_payload(best_rectangle: list[tuple[float, float]]) -> dict[str, Any] | None:
    if not best_rectangle:
        return None

    xs = [point[0] for point in best_rectangle]
    ys = [point[1] for point in best_rectangle]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    if width <= 0 or height <= 0:
        return None

    return {
        "vertices": [{"x": point[0], "y": point[1]} for point in best_rectangle],
        "width": width,
        "height": height,
        "area": width * height,
    }


def plot_buildable_space(
    raw_polygon_coordinates: list[tuple[float, float]],
    shrunk_polygon_coordinates: list[tuple[float, float]],
    ta_line: tuple[tuple[float, float], tuple[float, float]],
    best_rectangle: list[tuple[float, float]],
) -> str | None:
    """Plot raw/shrunk boundaries and rectangle for dev-side debugging."""
    try:
        import matplotlib

        if "DISPLAY" not in os.environ and matplotlib.get_backend().lower() == "agg":
            for candidate in ["TkAgg", "Qt5Agg", "WXAgg", "GTK3Agg", "WebAgg"]:
                try:
                    matplotlib.use(candidate, force=True)
                    break
                except Exception:
                    continue

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 8))

        raw_x = [point[0] for point in raw_polygon_coordinates] + [raw_polygon_coordinates[0][0]]
        raw_y = [point[1] for point in raw_polygon_coordinates] + [raw_polygon_coordinates[0][1]]
        ax.plot(raw_x, raw_y, color="tab:blue", linewidth=2, label="Raw land boundary")

        shrunk_x = [point[0] for point in shrunk_polygon_coordinates] + [
            shrunk_polygon_coordinates[0][0]
        ]
        shrunk_y = [point[1] for point in shrunk_polygon_coordinates] + [
            shrunk_polygon_coordinates[0][1]
        ]
        ax.plot(
            shrunk_x,
            shrunk_y,
            color="tab:orange",
            linewidth=2,
            linestyle="-",
            label="Shrunk boundary",
        )

        ta_x = [ta_line[0][0], ta_line[1][0]]
        ta_y = [ta_line[0][1], ta_line[1][1]]
        ax.plot(ta_x, ta_y, color="gold", linewidth=2, linestyle="-.", label="TA line")

        if best_rectangle:
            rect_x = [point[0] for point in best_rectangle] + [best_rectangle[0][0]]
            rect_y = [point[1] for point in best_rectangle] + [best_rectangle[0][1]]
            ax.plot(
                rect_x,
                rect_y,
                color="tab:red",
                linewidth=2,
                linestyle="--",
                label="Largest fitting rectangle",
            )

        ax.set_aspect("equal", adjustable="box")
        ax.set_title("Raw Boundary, Shrunk Boundary, and Largest Fitting Rectangle")
        ax.legend()
        ax.grid(True, alpha=0.3)

        output_dir = "test/dev/land_boundary_output"
        os.makedirs(output_dir, exist_ok=True)

        file_index = 1
        while True:
            out_path = f"{output_dir}/land_boundary_output_{file_index:03d}.png"
            if not os.path.exists(out_path):
                break
            file_index += 1

        plt.savefig(out_path)
        plt.close(fig)
        return out_path
    except Exception as exc:
        SystemLogger.warning(
            sector=5,
            message="Buildable-space plotting skipped",
            data={"error": str(exc)},
            filename="buildable_space_manager.py",
        )
        return None


def run_buildable_space_pipeline(
    land_data: dict[str, Any],
    min_width: float = 100,
    min_height: float = 100,
    should_plot: bool = False,
) -> dict[str, Any]:
    """Compute buildable space from API land payload and return normalized response payload."""
    start_time = perf_counter()

    SystemLogger.info(
        sector=1,
        message="Buildable-space pipeline started",
        data={
            "segment_count": len(land_data.get("segmentsCoordinates", [])),
            "road_count": len(land_data.get("roadConnected", [])),
            "min_width": min_width,
            "min_height": min_height,
            "should_plot": should_plot,
        },
        filename="buildable_space_manager.py",
    )

    try:
        raw_polygon_coordinates = _extract_polygon_coordinates(land_data)
        ta_line = _extract_ta_line(land_data)

        usable_land_result = find_usable_land_space(land_data)
        shrunk_polygon_coordinates = [
            (point["x"], point["y"])
            for point in usable_land_result.get("shrunkSegmentsCoordinates", [])
        ]

        finder = FPBoundaryFinder()
        best_rectangle = finder.fp_boundary_finder(
            polygon_coordinates=shrunk_polygon_coordinates,
            TA_line=ta_line,
            min_width=min_width,
            min_height=min_height,
        )

        rectangle = _rectangle_payload(best_rectangle)
        if rectangle is None:
            status = "OK"
            message = "Buildable space computed, but no feasible rectangle met constraints."
        else:
            status = "OK"
            message = "Buildable space computed successfully."

        if should_plot:
            plot_buildable_space(
                raw_polygon_coordinates=raw_polygon_coordinates,
                shrunk_polygon_coordinates=shrunk_polygon_coordinates,
                ta_line=ta_line,
                best_rectangle=best_rectangle,
            )

        payload = {
            "status": status,
            "message": message,
            "buildable_rectangle": rectangle,
            "shrunk_boundary": usable_land_result.get("shrunkSegmentsCoordinates", []),
            "metadata": usable_land_result.get("metadata"),
        }

        duration_ms = (perf_counter() - start_time) * 1000
        SystemLogger.info(
            sector=1,
            message="Buildable-space pipeline completed",
            data={
                "duration_ms": round(duration_ms, 2),
                "has_rectangle": rectangle is not None,
            },
            filename="buildable_space_manager.py",
        )
        return payload

    except ValueError as exc:
        duration_ms = (perf_counter() - start_time) * 1000
        SystemLogger.error(
            sector=1,
            message="Buildable-space pipeline validation error",
            data={"error": str(exc), "duration_ms": round(duration_ms, 2)},
            filename="buildable_space_manager.py",
        )
        return _error_payload(str(exc))
    except Exception as exc:
        duration_ms = (perf_counter() - start_time) * 1000
        SystemLogger.error(
            sector=1,
            message="Buildable-space pipeline unexpected error",
            data={"error": str(exc), "duration_ms": round(duration_ms, 2)},
            filename="buildable_space_manager.py",
        )
        return _error_payload("Unexpected error while computing buildable space.")
