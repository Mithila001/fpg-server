import os
from datetime import datetime
from .config import FLOOR_WIDTH, FLOOR_HEIGHT, ROOMS_DATA, PLOT_NOTE
from .generator import FloorPlanGenerator
from .plotter import save_plotter
from .utils.tracker import tracker


def main():
    NUM_GENERATIONS = 10
    # PLOT_NOTE = "OOP Refactor Test"
    # python -m _Isolated_Prototype_Area.floor_plan_generator_2.main

    session_timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
    # ensure output goes inside this package's folder (not the process CWD)
    base_dir = os.path.dirname(__file__)
    current_run_folder = os.path.join(base_dir, "../plotted images", session_timestamp)

    successful_count = 0

    for i in range(NUM_GENERATIONS):
        print(f"Generating floor plan {i + 1}...")

        # Initialize the Generator Object
        generator = FloorPlanGenerator(FLOOR_WIDTH, FLOOR_HEIGHT, ROOMS_DATA)

        # Run the generation
        success = generator.generate()

        if success:
            # Added the 'plot_title' argument below to fix the error
            save_plotter(
                generator.rooms,
                generator.solver,
                generator.width,
                generator.height,
                batchNo=i + 1,
                plot_title=f"Plan {i + 1} - {PLOT_NOTE}",
                output_subfolder=current_run_folder,
            )
            successful_count += 1
            print(f"Plan {i + 1} saved successfully.")
        else:
            print(f"Plan {i + 1} failed.")

    print(
        f"\nBatch Generation Complete! {successful_count}/{NUM_GENERATIONS} successful."
    )

    # Show error summary from tracker
    tracker.show_error_summary()


if __name__ == "__main__":
    main()
