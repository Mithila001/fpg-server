import json
import os
from buildable_space_finder.main1 import run_buildableSpaceFinder_algorithm, DEV__run_buildableSpaceFinder_algorithm_TEST__LeftAndRightChainTest,run_buildableSpaceFinder_algorithm_SINGLE_RUN
from _main_utility_files.plotter_image_gen import plot_polygon_images_save

# python -m main

# Define the filename where your JSON data is stored
FILE_NAME = "land_data.json"

def process_land_coordinates():
    """
    Loads land coordinates from a JSON file, stores them in an array, 
    and then prints each individual coordinate list.
    """
    
    # 1. Check if the file exists before attempting to open it
    if not os.path.exists(FILE_NAME):
        print(f"Error: The file '{FILE_NAME}' was not found in the current directory.")
        print("Please make sure the JSON data is saved to this file.")
        return

    try:
        # Load the JSON data from the file
        with open(FILE_NAME, 'r') as file:
            data = json.load(file)
        
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{FILE_NAME}'. Check the file structure.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return

    # 2. Extract the list of coordinate lists
    all_coordinates = [land['coordinates'] for land in data.get('lands', [])]

    # 3. Create a loop to run based on the total count and print the lists
    print(f"\n--- Total land plots found: **{len(all_coordinates)}** ---")

    ## ======================================================================================
    
    for i, coordinate_list in enumerate(all_coordinates):
        # The 'i + 1' gives us the plot number starting from 1
        print(f"\n**Coordinates for Land Plot {i + 1}**:")
        final_polygon, final_rect_parallel, final_rect_perpendicular = run_buildableSpaceFinder_algorithm(coordinate_list)
        print(f"Final Polygon: {final_polygon}")
        print(f"Final Rect Parallel: {final_rect_parallel}")
        print(f"Final Rect Perpendicular: {final_rect_perpendicular}")
        coordinateList = [final_polygon, final_rect_parallel, final_rect_perpendicular]
        plot_polygon_images_save(coordinateList, plot_number=i + 1)

    # =========================== Bug FIX TESTING ===========================
    # for i, coordinate_list in enumerate(all_coordinates):
    #     # The 'i + 1' gives us the plot number starting from 1
    #     print(f"\n**Coordinates for Land Plot {i + 1}**:")
    #     leftChain, rightChain = DEV__run_buildableSpaceFinder_algorithm_TEST__LeftAndRightChainTest(coordinate_list)
    #     coordinateList = [leftChain, rightChain]
    #     plot_polygon_images_save(coordinateList, plot_number=i + 1)

if __name__ == "__main__":
    process_land_coordinates()
    #run_buildableSpaceFinder_algorithm_SINGLE_RUN()