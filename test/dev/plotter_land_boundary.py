"""Dev utility to visualize land boundary and fitted rectangle using mock data."""

import os
import matplotlib

from app.algorithms.fp_boundary_finder import FPBoundaryFinder


# If DISPLAY is missing, we are likely in headless environment.
if "DISPLAY" not in os.environ:
    print("Warning: DISPLAY is not set; matplotlib may run in non-interactive Agg mode.")

# Attempt to select an interactive backend early.
if matplotlib.get_backend().lower() == "agg":
    for candidate in ["TkAgg", "Qt5Agg", "WXAgg", "GTK3Agg", "WebAgg"]:
        try:
            matplotlib.use(candidate, force=True)
            break
        except Exception:
            continue

# After backend selection is done, import pyplot.
import matplotlib.pyplot as plt


MOCK_LAND_DATA = {
    "area": 100000,
    "segmentsCoordinates": [
        {"x": 136.35599418843543, "y": 136.5242567940487},
        {"x": 483.0349661110454, "y": 209.93862731883672},
        {"x": 519.7421513734394, "y": 523.9889901193187},
        {"x": 136.35599418843543, "y": 381.2388252100087},
        {"x": 136.35599418843543, "y": 136.5242567940487},
    ],
    "roadConnected": [
        {
            "segment": [
                {"x": 483.0349661110454, "y": 209.93862731883672},
                {"x": 519.7421513734394, "y": 523.9889901193187},
            ],
            "roadType": "mainRoad",
        }
    ],
}


def _extract_polygon_coordinates(land_data: dict) -> list:
    raw_points = [
        (point["x"], point["y"]) for point in land_data.get("segmentsCoordinates", [])
    ]

    # Remove duplicated closing coordinate if present.
    if len(raw_points) > 1 and raw_points[0] == raw_points[-1]:
        return raw_points[:-1]
    return raw_points


def _extract_ta_line(land_data: dict) -> tuple:
    roads = land_data.get("roadConnected", [])
    if roads and roads[0].get("segment"):
        segment = roads[0]["segment"]
        if len(segment) >= 2:
            return (
                (segment[0]["x"], segment[0]["y"]),
                (segment[1]["x"], segment[1]["y"]),
            )

    raise ValueError("No valid TA segment found in mock land data.")


def run_plotter_land_boundary() -> list:
    """Run FP boundary finder on mock data and show polygon/rectangle plot."""
    polygon_coordinates = _extract_polygon_coordinates(MOCK_LAND_DATA)
    ta_line = _extract_ta_line(MOCK_LAND_DATA)

    finder = FPBoundaryFinder()
    best_rectangle = finder.fp_boundary_finder(
        polygon_coordinates=polygon_coordinates,
        TA_line=ta_line,
        min_width=100,
        min_height=100,
    )

    fig, ax = plt.subplots(figsize=(8, 8))

    poly_x = [point[0] for point in polygon_coordinates] + [polygon_coordinates[0][0]]
    poly_y = [point[1] for point in polygon_coordinates] + [polygon_coordinates[0][1]]
    ax.plot(poly_x, poly_y, color="tab:blue", linewidth=2, label="Land boundary")

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
    ax.set_title("Land Boundary and Largest Fitting Rectangle")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # If running in an environment where Agg is default (headless), try to switch to an interactive backend.
    import matplotlib

    if matplotlib.get_backend().lower() == "agg":
        for backend in ["TkAgg", "Qt5Agg", "WXAgg", "GTK3Agg", "WebAgg"]:
            try:
                matplotlib.use(backend, force=True)
                break
            except Exception:
                continue

    # Ensure output directory exists and save plot with a unique name.
    output_dir = "test/dev/land_boundary_output"
    os.makedirs(output_dir, exist_ok=True)
    file_index = 1
    while True:
        out_path = f"{output_dir}/land_boundary_output_{file_index:03d}.png"
        if not os.path.exists(out_path):
            break
        file_index += 1

    plt.savefig(out_path)
    print(f"Saved plot to {out_path}")

    return best_rectangle
