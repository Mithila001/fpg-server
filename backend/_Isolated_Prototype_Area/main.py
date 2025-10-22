import math
from plotter import plot_polygons
from myUtilities import calculate_distance, find_active_segment, get_x_intersection

def translate_and_reorder_polygon(polygon_coordinates, TA):
    """
    Translates the polygon so the TA point closest to (0,0) is moved to (0,0),
    and reorders the resulting coordinate list to start at (0,0).

    Args:
        polygon_coordinates: A list of (x, y) tuples for the polygon.
        TA: A tuple containing the two endpoints of the line segment, ((xA, yA), (xT, yT)).

    Returns:
        A list of (x, y) tuples representing the translated and reordered polygon.
    """
    
    # 1. Determine the Pivot Point (P) and Translation Vector
    point_A = TA[0]
    point_T = TA[1]
    
    dist_A = calculate_distance(point_A)
    dist_T = calculate_distance(point_T)

    if dist_A <= dist_T:
        pivot_point = point_A
    else:
        pivot_point = point_T
    
    # Calculate the translation vector
    (Px, Py) = pivot_point
    dx = -Px 
    dy = -Py

    # 2. Find the index of the Pivot Point in the original coordinate list
    # This point will become the new starting point (index 0)
    
    pivot_index = -1
    try:
        pivot_index = polygon_coordinates.index(pivot_point)
    except ValueError:
        # This handles a case where the TA point might not be exactly in the polygon_coordinates,
        # which shouldn't happen for a polygon defined by its vertices.
        print("Warning: Pivot point not found in polygon coordinates. Using default start.")
        pivot_index = 0

    # 3. Apply the translation to all polygon coordinates and store the result
    translated_coordinates = []
    for (x, y) in polygon_coordinates:
        new_x = x + dx
        new_y = y + dy
        translated_coordinates.append((new_x, new_y))
    
    # 4. Reorder the list to start at the translated pivot point (0, 0)
    
    # Slice the list from the pivot index to the end
    first_part = translated_coordinates[pivot_index:]
    
    # Slice the list from the start up to (but not including) the pivot index
    second_part = translated_coordinates[:pivot_index]
    
    # Combine the parts: [Pivot_Point, ..., Last_Point, First_Point, ..., Point_Before_Pivot]
    reordered_coordinates = first_part + second_part
 
    return reordered_coordinates



def rotate_polygon_to_x_axis(translated_polygon, TA): # Step 2  
    
    # We must first re-run the translation logic to find the translated coordinates
    # of the TA line endpoints, which we need to calculate the angle.
    
    # 1. Unpack the original TA line points
    point_A_orig = TA[0]
    point_T_orig = TA[1]
    
    # 2. Find the vertice that was closer to (0,0) (the pivot point)
    dist_A = calculate_distance(point_A_orig) 
    dist_T = calculate_distance(point_T_orig)
    
    if dist_A <= dist_T:
        (Px, Py) = point_A_orig
    else:
        (Px, Py) = point_T_orig
        
    # 3. Calculate the translated coordinates of the T point (T_prime)
    # The pivot point P is now at (0, 0).
    # The other point T is at (xT - Px, yT - Py).
    
    if (Px, Py) == point_A_orig:
        (xT_orig, yT_orig) = point_T_orig
    else:
        (xT_orig, yT_orig) = point_A_orig
        
    dx_T = xT_orig - Px
    dy_T = yT_orig - Py
    
    # 4. Find the current angle of the translated line TA relative to the X-axis
    current_angle = math.atan2(dy_T, dx_T)
    
    # 5. Determine the rotation angle
    # To align the line with the X-axis (angle 0), we rotate by the negative of the current angle.
    rotation_angle = -current_angle
    
    # Pre-calculate sine and cosine of the rotation angle
    cos_theta = math.cos(rotation_angle)
    sin_theta = math.sin(rotation_angle)
    
    # 6. Apply the rotation to the translated polygon
    rotated_polygon = []
    for (x, y) in translated_polygon:
        
        # Apply the rotation formula around the origin (0, 0):      
        new_x = x * cos_theta - y * sin_theta
        new_y = x * sin_theta + y * cos_theta
        
        rotated_polygon.append((new_x, new_y))
        
    # 7. Return the result and the angle
    return rotated_polygon, rotation_angle


def split_polygon_chains(coordinates):
      
    # Initialize the chains
    left_chain = []
    right_chain = []
    
    # 1. Find the maximum Y-coordinate (y_max)
    # This uses a simple loop, avoiding the max() function with a lambda for simplicity.
    y_max = coordinates[0][1]
    y_min = coordinates[0][1] # Also track y_min, although not strictly needed for splitting logic
    
    for x, y in coordinates:
        if y > y_max:
            y_max = y
        if y < y_min:
            y_min = y
            
    # 2. Split the chain at the first occurrence of y_max
    
    # 'splitting_point_found' is used as a flag to switch from filling left_chain to right_chain.
    splitting_point_found = False
    
    # Variable to help with the duplicate Y-value check
    previous_y = None 
    
    # Go through all coordinates from start to finish
    for x, y in coordinates:
        
        # --- Handle Duplicate Y-values ---
        # If the current Y is the same as the previous point stored, skip the current point.
        # This prevents redundant horizontal segments from breaking the vertical chain.
        if y == previous_y:
            #right_chain.append((x, y))
            continue
            
        # --- Chain Splitting Logic ---
        if not splitting_point_found:
            # Store point in the left chain
            left_chain.append((x, y))
            
            # Check if this point is the y_max point
            if y == y_max:
                splitting_point_found = True
        else:
            # Store the rest of the points in the right chain
            right_chain.append((x, y))

        # Update the previous Y-value for the next iteration's check
        previous_y = y
        
    # 3. Final steps to ensure the right chain is complete
    
    # The left chain already contains the y_max point. 
    # The right chain is currently missing the starting point (the first vertex) 
    # to close its loop and act as a sequential chain.
    
    # We add the starting point (the first vertex) to the end of the right chain.
    # We use the first point of the ORIGINAL coordinates to ensure closure.
    right_chain.append(coordinates[0]) 

    return left_chain, right_chain, y_min, y_max



def sweep_line_width_profile(left_chain, right_chain, min_y, max_y, y_resolution=0.5):
    """
    Calculates the width of the polygon at fixed y-intervals using a sweep line.

    Args:
        left_chain: The chain of coordinates from the start point to the y_max point.
        right_chain: The chain of coordinates from the y_max point to the start point.
        min_y: The minimum Y-coordinate of the overall polygon.
        max_y: The maximum Y-coordinate of the overall polygon.
        y_resolution: The step size for the sweep line.

    Returns:
        A tuple: (height_profile, width_profile)
        - height_profile: The list of Y-coordinates (heights) where the width was calculated.
        - width_profile: The matching list of calculated widths.
    """
    cross_sections_data = []
   
    # Start the sweep line just above min_y and stop at max_y
    i = min_y + y_resolution # This part could be a issue. We need full sweep from min_y to max_y to get largest area.

    while i <= max_y:
        
        # 1. Find active segments
        
        left_segment = find_active_segment(left_chain, i)
        right_segment = find_active_segment(right_chain, i)
        
        # Safety check: Both segments must be found to calculate a valid width
        if left_segment and right_segment:
            
            # 2. Calculate Intersection Points (x_left, x_right)
            x_left = get_x_intersection(left_segment[0], left_segment[1], i)
            x_right = get_x_intersection(right_segment[0], right_segment[1], i)

            # 3. Get width
            w = x_right - x_left
            
            # Use the hardcoded MIN_WIDTH check
            if w >= MIN_WIDTH:
                # 4. Store the results for this height step
                profile_data = {
                    'y': i,
                    'x_left': x_left,
                    'x_right': x_right,
                    'width': w
                }
                cross_sections_data.append(profile_data)
        
        # Move the sweep line up by the resolution step
        i += y_resolution

    return cross_sections_data


def find_max_area_rectangle(cross_sections_data, min_height=0.5, min_width=0.5):
    """
    Finds the dimensions of the largest valid rectangle that can be inscribed 
    in the polygon based on the given width profile.

    Args:
        cross_sections_data: A list of dictionaries containing 'y', 'x_left', 'x_right', and 'width'.
        min_height: The minimum acceptable height for a rectangle.
        min_width: The minimum acceptable width for a rectangle.

    Returns:
        A dictionary containing the dimensions and profile indices of the maximum area rectangle:
        {
            'max_area': float, 
            'width': float, 
            'height': float,
            'y_bottom_index': int,
            'y_top_index': int
        }
    
    """
    
    max_area = 0.0
    best_result = {
        'max_area': 0.0,
        'width': 0.0,
        'height': 0.0,
        'y_bottom_index': -1,
        'y_top_index': -1
    }
    
    N = len(cross_sections_data)
    
    # Outer loop: Sets the bottom edge of the potential rectangle (index i)
    for i in range(N):
        y_bottom = cross_sections_data[i]['y']

        # Keep track of the minimum width found between i and the current j
        # Initialize with the width at the bottom edge.
        smallest_width = cross_sections_data[i]['width']

        # Inner loop: Sets the top edge of the potential rectangle (index j)
        # We only look at points *above* the bottom edge (j > i)
        for j in range(i + 1, N):
            y_top = cross_sections_data[j]['y']

            # 1. Update the smallest width for the current range [i, j]
            current_width = cross_sections_data[j]['width']
            if current_width < smallest_width:
                smallest_width = current_width
            
            # 2. Check local height constraint
            local_height = y_top - y_bottom
            if local_height < min_height:
                # If the height is too small, skip to the next top edge (j)
                # Since the heights are increasing, if it fails here, it will fail for all subsequent j's too,
                # but we continue to the next j to ensure we find the smallest_width correctly 
                # (although the logic relies on strictly increasing height_profile, which it should be).
                continue 
                
            # 3. Check smallest width constraint
            if smallest_width < min_width:
                # If the current smallest width is too small, skip to the next top edge (j)
                continue
                
            # 4. Calculate the area
            area = smallest_width * local_height
            
            # 5. Check if this is the new maximum area
            if area > max_area:
                max_area = area
                best_result['max_area'] = area
                best_result['width'] = smallest_width
                best_result['height'] = local_height
                best_result['y_bottom_index'] = i
                best_result['y_top_index'] = j
                
    return best_result


def get_rectangle_coordinates(best_result, sweep_marks):
    """
    Calculates the four corner coordinates of the maximum area rectangle 
    in the current (translated and rotated) coordinate system.

    Args:
        best_result: The dictionary containing the results of the max area search, 
                     including 'width', 'y_bottom_index', and 'y_top_index'.
        sweep_marks: The list of profile dictionaries (the result of sweep_line_marks_calculator).
                     
    Returns:
        A list of (x, y) tuples representing the four corners of the rectangle:
        [(x_BL, y_BL), (x_BR, y_BR), (x_TR, y_TR), (x_TL, y_TL)]
    """
    
    # 1. Extract the key data points defining the rectangle's extent
    y_bottom_index = best_result['y_bottom_index']
    y_top_index = best_result['y_top_index']
    constraining_width = best_result['width']
    
    # Get the exact Y-levels from the sweep marks list
    y_bottom = sweep_marks[y_bottom_index]['y']
    y_top = sweep_marks[y_top_index]['y']
    
    
    # 2. Find the constraining slice (the bottleneck)
    
    constraining_x_left = 0.0
    constraining_x_right = 0.0
    found_constraint = False
    
    # Iterate through the range of profile slices that define the rectangle
    # We check from the bottom index up to the top index (inclusive)
    for k in range(y_bottom_index, y_top_index + 1):
        slice_data = sweep_marks[k]
        
        # Check if the width of this slice matches the maximum allowed width for the rectangle
        # Using math.isclose for reliable float comparison
        if math.isclose(slice_data['width'], constraining_width):
            # This slice is the bottleneck. We use its x_left and x_right to define the rectangle's x-extent.
            constraining_x_left = slice_data['x_left']
            constraining_x_right = slice_data['x_right']
            found_constraint = True
            # We can break early since the first one found with the min width defines the X-extent.
            break 
            
    # Safety Check
    if not found_constraint:
        # This should not happen with correct inputs, but ensures safe code execution.
        print("Error: Could not find the slice that defines the constraining width.")
        return []
        
    # 3. Define the four corners of the rectangle (in the current rotated/translated system)
    
    # Bottom-Left (BL)
    x_BL = constraining_x_left
    y_BL = y_bottom
    
    # Bottom-Right (BR)
    x_BR = constraining_x_right
    y_BR = y_bottom
    
    # Top-Right (TR)
    x_TR = constraining_x_right
    y_TR = y_top
    
    # Top-Left (TL)
    x_TL = constraining_x_left
    y_TL = y_top
    
    rectangle_coordinates_rotated = [
        (x_BL, y_BL), 
        (x_BR, y_BR), 
        (x_TR, y_TR), 
        (x_TL, y_TL)
    ]
    
    return rectangle_coordinates_rotated

# --- Hardcoded Constraints (as requested) ---
# These would be parameters in a final algorithm, but are hardcoded for this step.
MIN_WIDTH = 1.0
MIN_HEIGHT = 0.5
# --- Example Usage ---
# Define the coordinates for a simple polygon
originalPolygon = [(-6, 0), (-3, 5), (4, 6), (7, 2), (3, -4), (-2, -3)]
TA_line = (originalPolygon[1], originalPolygon[0])
#TA_line = (originalPolygon[0], originalPolygon[1])
zeroed_polygon = translate_and_reorder_polygon(originalPolygon, TA_line)
#plot_polygons([originalPolygon, zeroed_polygon])
rotated_polygon, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line)

print("Original Polygon:", originalPolygon)
print("Zeroed Polygon:", zeroed_polygon)
print("Rotated Polygon:", rotated_polygon)
print("Rotation Angle (radians):", angle)

left_chain_result, right_chain_result, y_min, y_max = split_polygon_chains(rotated_polygon)
print("Left Chain:", left_chain_result)
print("Right Chain:", right_chain_result)
print("Y Min:", y_min)
print("Y Max:", y_max)
cross_section_data = sweep_line_width_profile(left_chain_result, right_chain_result, min_y=y_min, max_y=y_max, y_resolution=0.5)
best_rectangle = find_max_area_rectangle(cross_section_data, min_height=MIN_HEIGHT, min_width=MIN_WIDTH)
largest_rectangle_coords = get_rectangle_coordinates(best_rectangle, cross_section_data)

print("Left Chain:", left_chain_result)
print("Right Chain:", right_chain_result)
#print("Cross Section Data:", cross_section_data)
#print("Best Rectangle:", best_rectangle)
#print("Largest Rectangle Coordinates:", largest_rectangle_coords)

#plot_polygons([ originalPolygon, rotated_polygon, largest_rectangle_coords])
plot_polygons([left_chain_result,right_chain_result])
#plot_polygons([originalPolygon, zeroed_polygon])
print("Plot displayed.")
