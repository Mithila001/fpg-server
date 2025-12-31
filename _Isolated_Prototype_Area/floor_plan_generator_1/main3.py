"""
Main entry point for floor plan generation.
"""
# python -m floor_plan_generator_1.main3
from ortools.sat.python import cp_model
import random
from datetime import datetime
import os

# Import configuration
from .config import FLOOR_WIDTH, FLOOR_HEIGHT, ROOMS_DATA

# Import variable creation
from .variables.room_variables import create_room_variables

# Import constraints
from .constraints.basic_constraints import add_basic_constraints
from .constraints.adjacency_constraints import add_kitchen_living_adjacency
from .constraints.floor_area_coverage import add_minimum_area_coverage
from .constraints.room_size_hierarchy_constraints import add_room_size_hierarchy

# Import plotter
from .plotter import show_plotter, save_plotter


def generate_floor_plan():
    """
    Generate a regulation-compliant floor plan.
    
    Returns:
        Dictionary with solution status and data
    """
    # 1. SETUP
    model = cp_model.CpModel()
    
    # 2. CREATE VARIABLES
    all_vars, x_intervals, y_intervals = create_room_variables(
        model, ROOMS_DATA, FLOOR_WIDTH, FLOOR_HEIGHT
    )
    
    # 3. ADD CONSTRAINTS
    # Basic constraints (non-overlap, boundaries)
    add_basic_constraints(model, all_vars, x_intervals, y_intervals)
    
    # Adjacency constraints
    touch_vars = add_kitchen_living_adjacency(model, all_vars)
    
    # Minimum area coverage constraint
    add_minimum_area_coverage(model, all_vars, FLOOR_WIDTH, FLOOR_HEIGHT, min_coverage=0.8)

    # Room size hierarchy constraints
    add_room_size_hierarchy(model, all_vars)

    # 4. SOLVE
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random.randint(0, 1000)
    status = solver.Solve(model)
    
    # 5. RETURN RESULTS
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("Solution Found!")
        
        # Print adjacency info
        print(f"Kitchen-Living adjacency:")
        for direction, bool_var in touch_vars.items():
            print(f"  {direction}: {solver.Value(bool_var)}")
        
        return {
            'success': True,
            'all_vars': all_vars,
            'solver': solver,
            'FLOOR_WIDTH': FLOOR_WIDTH,
            'FLOOR_HEIGHT': FLOOR_HEIGHT
        }
    else:
        print("No solution found. Constraints might be too tight!")
        return {
            'success': False,
            'all_vars': None,
            'solver': None,
            'FLOOR_WIDTH': FLOOR_WIDTH,
            'FLOOR_HEIGHT': FLOOR_HEIGHT
        }


def main():
    """Main execution function."""
    NUM_GENERATIONS = 10
    
    print(f"Starting batch generation of {NUM_GENERATIONS} floor plans...")
    print("-" * 60)
    
    successful_count = 0
    PLOT_NOTE = "Max Area Coverage 80% test 1"
    
    session_timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
    current_run_folder = os.path.join("plotted images", session_timestamp)

    for batch in range(NUM_GENERATIONS):
        print(f"\nGenerating floor plan {batch + 1}/{NUM_GENERATIONS}...")
        
        result = generate_floor_plan()

        # 1. Create a unique folder name for THIS execution run
        
        
        if result['success']:
            save_plotter(
                result['all_vars'],
                result['solver'],
                result['FLOOR_WIDTH'],
                result['FLOOR_HEIGHT'],
                batchNo=batch,
                plot_title=f"({batch + 1}) - {PLOT_NOTE}",
                output_subfolder=current_run_folder
            )
            successful_count += 1
            print(f"✓ Batch {batch} saved successfully!")
        else:
            print(f"✗ Batch {batch} failed.")
    
    print("\n" + "=" * 60)
    print(f"Generation Complete! {successful_count}/{NUM_GENERATIONS} successful")
    print("=" * 60)


if __name__ == "__main__":
    main()
