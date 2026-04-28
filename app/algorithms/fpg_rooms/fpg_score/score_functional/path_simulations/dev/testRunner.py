import json
import os
import sys
from pathlib import Path

# Since you are running from F:\...\fpg-server,
# we can use the current working directory as the root.
root_dir = Path(os.getcwd())
sys.path.append(str(root_dir))

from app.algorithms.fpg_rooms.fpg_score.score_functional.path_simulations.path_simulator import (
    evaluate_path_simulation,
)


def run_path_sim_tests():
    # 1. Precise Paths
    # We use the relative path you provided from the root
    floor_plans_path = (
        root_dir
        / "app"
        / "algorithms"
        / "fpg_post_processor"
        / "dev"
        / "mock_data"
        / "floorPlans.json"
    )
    output_base_dir = root_dir / "test" / "outputs" / "path_score" / "dev"

    os.makedirs(output_base_dir, exist_ok=True)

    # 2. Load Data
    if not floor_plans_path.exists():
        print(f"Error: Floor plans not found at {floor_plans_path}")
        # Debug helper: print current directory to see where we are looking
        print(f"Current Working Directory: {os.getcwd()}")
        return

    with open(floor_plans_path, "r") as f:
        all_floor_plans = json.load(f)

    print(f"--- Starting Path Simulation: {len(all_floor_plans)} Plans Found ---\n")

    for i, rooms in enumerate(all_floor_plans):
        print(f"Processing Floor Plan #{i + 1}...")

        # 3. Create a 'Main Door' automatically
        # Simulation requires a starting point. We'll pick the 'livingRoom'
        # or 'veranda' as the logical entrance.
        entry_room = next(
            (r for r in rooms if r["type"] in ["veranda", "livingRoom1", "livingRoom"]),
            rooms[0],
        )
        mid_x = (entry_room["x"] + entry_room["x_end"]) / 2
        mid_y = (entry_room["y"] + entry_room["y_end"]) / 2

        mock_openings = [
            {
                "opening_type": "maindoor",
                "x1": mid_x - 1,
                "y1": mid_y,
                "x2": mid_x + 1,
                "y2": mid_y,
                "room_name": entry_room["name"],
            }
        ]

        # 4. Run Evaluation
        score, diagnostics = evaluate_path_simulation(
            rooms=rooms,
            openings=mock_openings,
            enable_dev_plot=True,
            output_dir=str(output_base_dir),
        )

        # 5. Output Results
        print(f"  Score: {score:.2f}/10")
        print(f"  Path Count: {diagnostics.get('path_count')}")
        if "plot_file" in diagnostics:
            print(f"  Plot: {diagnostics['plot_file']}")
        print("-" * 50)


if __name__ == "__main__":
    run_path_sim_tests()
