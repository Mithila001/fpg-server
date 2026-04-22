import json
import os
import traceback
# Import all necessary types
from app.algorithms.fpg_rooms.types.room import FpgRequirements, RoomData, ConfigData
from app.models.room_relations_constraint import RoomRelationsConstraint
from app.services.algorithm_manager_v2 import _run_single_fpg_solve
from test.dev.final_result_plotter import plot_final_solver_result

def debug_fpg_with_hints():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'requirement_example.json')

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        print(f"Successfully loaded requirements from {json_path}")

        # 1. Convert nested Rooms list to RoomData objects
        rooms_list = [RoomData(**r) for r in data.get("rooms", [])]

        # 2. Convert Config dictionary to ConfigData object
        config_obj = ConfigData(**data.get("config", {}))

        # 3. Convert Relation Constraints (if they exist)
        relations = [RoomRelationsConstraint(**rc) for rc in data.get("relation_constraints", [])]

        # 4. Create the final Requirements object
        requirements_obj = FpgRequirements(
            rooms=rooms_list,
            config=config_obj,
            relation_constraints=relations,
            initial_point_hints=data.get("initial_point_hints", [])
        )

        # 5. Pass the fully typed Object
        result = _run_single_fpg_solve(requirements=requirements_obj)
        
        plot_final_solver_result(result, show=False)

        print("FPG Run Done.")
        return result

    except FileNotFoundError:
        print(f"Error: The file {json_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_fpg_with_hints()
    
    
# python3 -m test.dev.fpg_hint_debug.fgp_hint_debug