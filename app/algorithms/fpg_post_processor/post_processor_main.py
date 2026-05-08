import json
import os

from app.algorithms.fpg_post_processor.dev.fpgpp_plotter import (
    plot_floorplan_comparison,
)
from app.algorithms.fpg_post_processor.hallway_union import hallway_union
from app.algorithms.fpg_post_processor.dev.dev_visualizer_plotter import (
    plot_and_save_results,
)
from app.algorithms.fpg_post_processor.dev.process_results_plotter import (
    save_floor_plan_plots,
)
from app.algorithms.fpg_post_processor.snap_floor_plan_to_grid import (
    snap_floor_plan_to_grid,
)
from app.algorithms.fpg_post_processor.extend_walls import extend_floor_plan_walls
from app.algorithms.fpg_post_processor.veranda_post_process import modify_veranda_layout
from app.algorithms.fpg_post_processor.wall_union import floor_plan_wall_union
from app.algorithms.types.domain import ProcessedRoomData


def _load_mock_floor_plans():
    """
    Loads floor plan data using a relative path based on this file's location.
    """
    # 1. Get the directory where post_processor_main.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Construct the relative path to the JSON file
    # This moves into 'dev', then 'mock_data', then targets 'floorPlans.json'
    file_path = os.path.join(current_dir, "dev", "mock_data", "floorPlans.json")

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return []

    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"An error occurred while loading JSON: {e}")
        return []


def process_floor_plans():
    """
    Retrieves floor plans and loops through them for processing.
    """
    all_plans = _load_mock_floor_plans()
    if not all_plans:
        return

    target_indices = [2]  # Process all plans (0-9)
    for i, plan in enumerate(all_plans):
        if i not in target_indices:
            continue
        # 1. Get the geometry from workspace
        verandaUpdatedPlan = modify_veranda_layout(plan)
        processed_floor_plan: list[ProcessedRoomData] = extend_floor_plan_walls(
            verandaUpdatedPlan, filename=f"plan_analysis_{i}.png"
        )
        snapped_results: list[ProcessedRoomData] = snap_floor_plan_to_grid(
            processed_floor_plan
        )
        floor_plan_wall_union(snapped_results)
        union_hallways_fp = hallway_union(snapped_results)
        # save_floor_plan_plots(union_hallways_fp)
        plot_floorplan_comparison(snapped_results, union_hallways_fp)
        print(f"Before {snapped_results}\n")
        print(f"After {union_hallways_fp}\n")


if __name__ == "__main__":
    process_floor_plans()
