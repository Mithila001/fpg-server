import os
from datetime import datetime
from .config import FLOOR_WIDTH, FLOOR_HEIGHT, ROOMS_DATA
from .generator import FloorPlanGenerator
from .plotter import save_plotter

def main():
    NUM_GENERATIONS = 10
    PLOT_NOTE = "OOP Refactor Test" # This is the missing piece
    
    session_timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
    current_run_folder = os.path.join("plotted images", session_timestamp)

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
                output_subfolder=current_run_folder
            )
            successful_count += 1
            print(f"✓ Plan {i + 1} saved successfully.")
        else:
            print(f"✗ Plan {i + 1} failed.")

    print(f"\nBatch Generation Complete! {successful_count}/{NUM_GENERATIONS} successful.")

if __name__ == "__main__":
    main()