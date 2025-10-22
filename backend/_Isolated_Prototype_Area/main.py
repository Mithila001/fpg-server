import math
from plotter import plot_polygons
from myUtilities import calculate_distance, find_active_segment, get_x_intersection

def translate_to_origin(polygon_coordinates, TA): # Step 1  
    # 1. Unpack the coordinates of the TA line
    point_A = TA[0]
    point_T = TA[1]
    
    # 2. Find the vertice that is closer to (0,0)
    dist_A = calculate_distance(point_A)
    dist_T = calculate_distance(point_T)

    if dist_A <= dist_T:
        # A is the closest point to (0,0), so A is the pivot (Px, Py)
        (Px, Py) = point_A
    else:
        # T is the closest point to (0,0), so T is the pivot (Px, Py)
        (Px, Py) = point_T
    
    # 3. Calculate the translation vector (the movement needed)
    # To move Px to 0, we need to subtract Px.
    dx = -Px 
    dy = -Py

    # 4. Apply the translation to all polygon coordinates
    translated_coordinates = []
    for (x, y) in polygon_coordinates:
        # Basic vector addition (or subtraction)
        new_x = x + dx
        new_y = y + dy
        translated_coordinates.append((new_x, new_y))

 
    return translated_coordinates

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
    relative_coordinates = []
    for (x, y) in translated_polygon:
        
        # Apply the rotation formula around the origin (0, 0):      
        new_x = x * cos_theta - y * sin_theta
        new_y = x * sin_theta + y * cos_theta
        
        relative_coordinates.append((new_x, new_y))
        
    # 7. Return the result and the angle
    return relative_coordinates, rotation_angle


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
            right_chain.append((x, y))
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
    #right_chain.append(coordinates[0]) # U dont think I need this for the current logic.

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
    
    height_profile = []
    width_profile = []
    
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
                height_profile.append(i)
                width_profile.append(w)
        
        # Move the sweep line up by the resolution step
        i += y_resolution
        
    return height_profile, width_profile

# --- Hardcoded Constraints (as requested) ---
# These would be parameters in a final algorithm, but are hardcoded for this step.
MIN_WIDTH = 1.0
MIN_HEIGHT = 0.5
# --- Example Usage ---
# Define the coordinates for a simple polygon
originalPolygon = [(-6, -4),(-3, 4), (3, 4), (6, -4), ]
TA_line = (originalPolygon[0], originalPolygon[1])
#TA_line = (originalPolygon[0], originalPolygon[1])
zeroed_polygon = translate_to_origin(originalPolygon, TA_line)
#plot_polygons([originalPolygon, zeroed_polygon])
relative_coordinates, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line)

print("Original Polygon:", originalPolygon)
print("Rotated Polygon:", relative_coordinates)
print("Rotation Angle (radians):", angle)

left_chain_result, right_chain_result, y_min, y_max = split_polygon_chains(originalPolygon)
print("Left Chain:", left_chain_result)
print("Right Chain:", right_chain_result)
heightProfile, widthProfile = sweep_line_width_profile(left_chain_result, right_chain_result, min_y=y_min, max_y=y_max, y_resolution=0.5)

print("Left Chain:", left_chain_result)
print("Right Chain:", right_chain_result)
print("Height Profile:", heightProfile)
print("Width Profile:", widthProfile)


#plot_polygons([originalPolygon, relative_coordinates])
#plot_polygons([originalPolygon, zeroed_polygon])
print("Plot displayed.")
