"""Main (two-stage pipeline demo)

Demonstrates the complete workflow:
1. Run buildable_space_finder on realistic mock land polygons
   → Plot results in ./results/land/
2. Pass buildable-space output to usable_space_in_land-finder (with setbacks)
   → Plot results in ./results/space/

Mock coordinates represent various realistic land scenarios:
- Rectangular suburban lot
- Irregular corner lot
- Narrow infill lot
- L-shaped lot
- Trapezoidal lot
"""

import os
import sys
from typing import List, Sequence, Tuple

from buildable_space_finder.main1 import run_buildableSpaceFinder_algorithm

# Import from folder with hyphen in name (not a valid Python identifier)
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "usable_space_in_land-finder")
)
from main2 import LandBuildableFinder  # type: ignore

from plotters.polygon_plotter import PolygonPlotter

Coordinate = Tuple[float, float]


# Realistic mock land coordinates representing various urban/suburban scenarios
MOCK_LANDS: Sequence[Sequence[Coordinate]] = [
    # 1. Standard Rectangular Suburban Lot (approx. 600 sqm)
    # Slightly offset from origin to simulate real-world positioning.
    [(2.1, 1.5), (22.1, 1.5), (22.1, 31.5), (2.1, 31.5)],
    # 2. Large Cul-de-sac Pie-Shaped Lot (Convex)
    # Common at the end of streets; wider at the back than the front.
    [(50.0, 0.0), (62.5, 2.0), (75.0, 35.0), (40.0, 35.0)],
    # 3. Narrow Urban Infill (Row House style)
    # Deep and thin, typical of high-density private land.
    [(10.0, 10.0), (17.5, 10.0), (17.5, 38.0), (10.0, 38.0)],
    # 4. Angled Corner Lot (Trapezoid-like)
    # Common where two roads meet at a non-90 degree angle.
    [(0.0, 0.0), (25.0, 0.0), (28.5, 22.0), (5.0, 22.0)],
    # 5. Large Acreage/Estate Lot
    # Slightly irregular 5-sided convex polygon representing a rural private plot.
    [(100.0, 100.0), (160.0, 110.0), (155.0, 180.0), (120.0, 195.0), (95.0, 150.0)],
    # 6. Wide Shallow Lot
    # Found in premium coastal or view-oriented residential areas.
    [(0.0, 0.0), (45.0, 2.5), (43.0, 22.0), (2.0, 20.0)],
]

# Setback distances for each land (uniform for simplicity)
# Order: [front, right, back, left] or per-edge if different
DEFAULT_SETBACKS = [2.0, 1.5, 2.0, 1.5]  # typical residential setbacks in meters


def run_two_stage_pipeline(show: bool = False) -> Tuple[List[str], List[str]]:
    """
    Execute the complete two-stage pipeline on all mock lands.

    Stage 1: buildable_space_finder
        - Finds largest buildable area within land boundaries
        - Saves plots to ./results/land/

    Stage 2: usable_space_in_land-finder
        - Applies setbacks to buildable space from Stage 1
        - Saves plots to ./results/space/

    Returns:
        Tuple of (land_plot_paths, space_plot_paths)
    """

    # Setup output directories
    land_output_dir = os.path.join(".", "results", "land")
    space_output_dir = os.path.join(".", "results", "space")
    os.makedirs(land_output_dir, exist_ok=True)
    os.makedirs(space_output_dir, exist_ok=True)

    land_plotter = PolygonPlotter(output_base_dir=land_output_dir)

    land_saved: List[str] = []
    space_saved: List[str] = []

    print("=" * 70)
    print("TWO-STAGE PIPELINE: Buildable Space → Usable Space")
    print("=" * 70)

    for idx, land_coords in enumerate(MOCK_LANDS, start=1):
        print(f"\n{'─' * 70}")
        print(f"Processing Land #{idx} ({len(land_coords)} vertices)")
        print(f"{'─' * 70}")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 1: Buildable Space Finder
        # ═══════════════════════════════════════════════════════════════
        print(f"\n[Stage 1] Running buildable_space_finder...")

        try:
            result = run_buildableSpaceFinder_algorithm(land_coords)
        except Exception as e:
            print(f"[Stage 1] ERROR: {e}")
            print(f"[Stage 1] Skipping land #{idx}")
            continue

        if not result or not any(result):
            print(f"[Stage 1] No buildable space found for land #{idx}")
            continue

        # result is typically (final_polygon, rect_parallel, rect_perpendicular)
        final_polygon, rect_parallel, rect_perpendicular = result

        if not final_polygon:
            print(f"[Stage 1] No final polygon returned for land #{idx}")
            continue

        # Plot Stage 1 results
        coords_to_plot = [land_coords, final_polygon]
        if rect_parallel:
            coords_to_plot.append(rect_parallel)
        if rect_perpendicular:
            coords_to_plot.append(rect_perpendicular)

        stage1_title = f"Land #{idx}: Buildable Space (Stage 1)"
        land_plotter.polygon_line_plotter_single(
            coordinates_list=coords_to_plot,
            show=show,
            title=stage1_title,
        )

        if land_plotter.last_saved_file:
            land_saved.append(land_plotter.last_saved_file)
            print(f"[Stage 1] ✓ Saved: {land_plotter.last_saved_file}")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 2: Usable Space Finder (with setbacks)
        # ═══════════════════════════════════════════════════════════════
        print(f"\n[Stage 2] Applying setbacks to buildable space...")

        # Use final_polygon from Stage 1 as input
        # Need to match setbacks list length to number of edges
        num_edges = len(final_polygon)

        # Repeat default setbacks cyclically to match edge count
        setbacks = [
            DEFAULT_SETBACKS[i % len(DEFAULT_SETBACKS)] for i in range(num_edges)
        ]

        try:
            usable_finder = LandBuildableFinder(
                vertices=final_polygon,
                offsets=setbacks,
                output_base_dir=space_output_dir,
            )

            usable_space = usable_finder.compute()

            if not usable_space:
                print(f"[Stage 2] No usable space computed for land #{idx}")
                continue

            print(f"[Stage 2] ✓ Usable space computed: {len(usable_space)} vertices")

            # Plot Stage 2 results
            space_plotter = PolygonPlotter(output_base_dir=space_output_dir)
            stage2_title = f"Land #{idx}: Usable Space (Stage 2)"

            space_plotter.polygon_line_plotter_single(
                coordinates_list=[final_polygon, usable_space],
                show=show,
                title=stage2_title,
            )

            if space_plotter.last_saved_file:
                space_saved.append(space_plotter.last_saved_file)
                print(f"[Stage 2] ✓ Saved: {space_plotter.last_saved_file}")

        except Exception as e:
            print(f"[Stage 2] ERROR: {e}")
            print(f"[Stage 2] Continuing to next land...")
            continue

    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Stage 1 (Buildable): {len(land_saved)} plot(s) saved to {land_output_dir}")
    print(
        f"Stage 2 (Usable):    {len(space_saved)} plot(s) saved to {space_output_dir}"
    )
    print("=" * 70)

    return land_saved, space_saved


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__) or os.getcwd())
    land_paths, space_paths = run_two_stage_pipeline(show=False)

    print(f"\n✓ Total images generated: {len(land_paths) + len(space_paths)}")
