import math
#from plotter1 import plot_polygons
from buildable_space_finder.myUtilities1 import calculate_distance, find_active_segment, get_x_intersection,flip_xy_coordinates, inverse_rotate_polygon,inverse_translate_polygon
from buildable_space_finder.plotter1 import plot_polygons

# python -m buildable_space_finder.main1

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
    """
    Splits a polygon's ordered coordinates into a left chain (bottom-to-top) 
    and a right chain (top-to-bottom), ensuring the traversal starts at the 
    bottom-most and left-most point for robustness.

    Args:
        coordinates: A list of (x, y) tuples representing the polygon vertices in order.

    Returns:
        A tuple: (left_chain, right_chain, y_min, y_max)
    """
    

    # 1) Pick bottom-most (min y); on tie pick left-most (min x)
    bottom_coord = min(coordinates, key=lambda c: (c[1], c[0]))

    # 2) Rotate original list so bottom_coord is first (preserve cyclic order)
    idx = coordinates.index(bottom_coord)
    rotated = coordinates[idx:] + coordinates[:idx]

    # 3) Ensure clockwise order. Compute signed area; if positive (CCW), reverse
    def signed_area(poly):
        a = 0.0
        n = len(poly)
        for i in range(n):
            x1,y1 = poly[i]
            x2,y2 = poly[(i+1) % n]
            a += x1*y2 - x2*y1
        return a / 2.0

    area = signed_area(rotated)
    if area > 0:  # polygon currently CCW -> make clockwise
        rev = rotated[::-1]
        # rotate reversed list to start at bottom_coord
        ridx = rev.index(bottom_coord)
        rotated_clockwise = rev[ridx:] + rev[:ridx]
    else:
        rotated_clockwise = rotated

    # 4) compute min_y and max_y from rotated_clockwise
    y_vals = [y for _, y in rotated_clockwise]
    min_y = min(y_vals)
    max_y = max(y_vals)

    # 5) split so the first coordinate with y >= max_y
    #    is included in BOTH left_chain (as the last) and right_chain (as the first)
    # find index of first coord with y >= max_y
    first_max_idx = next((i for i, (_, y) in enumerate(rotated_clockwise) if y >= max_y), None)

    if first_max_idx is None:
        # defensive fallback (shouldn't happen): everything to left_chain, right_chain empty
        left_chain = rotated_clockwise[:] 
        right_chain = []
    else:
        left_chain = rotated_clockwise[:first_max_idx] + [rotated_clockwise[first_max_idx]]
        right_chain = rotated_clockwise[first_max_idx:]
        right_chain.append(rotated_clockwise[0])  # close the loop back to start

    
    ################################################################################################

    
    return left_chain, right_chain, min_y, max_y



def sweep_line_width_profile(left_chain, right_chain, min_y, max_y, y_resolution=0.1):
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
    in the polygon based on the given width profile, ensuring full containment 
    across the entire height of the rectangle.
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
    # for y in range(N):
    #     print( cross_sections_data[y]['y'])

    # Outer loop: Sets the bottom edge of the potential rectangle (index i)
    for i in range(N):
        y_bottom = cross_sections_data[i]['y']
        
        # Initial X_Left
        max_x_left = cross_sections_data[i]['x_left']
        
        # Initial X_Right
        min_x_right = cross_sections_data[i]['x_right']
        
        # Inner loop: Sets the top edge of the potential rectangle (index j)
        for j in range(i, N):
            
            y_top = cross_sections_data[j]['y']
            top_line_data = cross_sections_data[j] # for easier access

            # 2. Update the Bounding Box for the new slice 'j'

            # If this line left x is within the current max_x_left, update max_x_left
            if top_line_data['x_left'] > max_x_left:
                max_x_left = top_line_data['x_left']

            # If this line right x is within the current min_x_right, update min_x_right
            if top_line_data['x_right'] < min_x_right:
                min_x_right = top_line_data['x_right']
            
            # 3. Calculate the actual contained width
            local_width = min_x_right - max_x_left
            
            
            # 4. Check local height constraint
            local_height = y_top - y_bottom
            if local_height < min_height:
                # Height is guaranteed to increase, so we continue to the next 'j'
                continue 
                
            # 5. Calculate the area (using the guaranteed contained width)
            area = local_width * local_height
            
            # 6. Check if this is the new maximum area
            if area > max_area:
                max_area = area
                # Store the result using the calculated local_width
                best_result['max_area'] = area
                best_result['width'] = local_width
                best_result['height'] = local_height
                best_result['y_bottom_index'] = i
                best_result['y_top_index'] = j 
                
    return best_result


def get_rectangle_coordinates(best_result, sweep_marks):
    """
    Calculates the four corner coordinates of the maximum area rectangle 
    by determining the tightest X-boundaries within the identified height range.

    Args:
        best_result: The dictionary containing the results of the max area search.
        sweep_marks: The list of profile dictionaries.
                     
    Returns:
        A list of (x, y) tuples representing the four corners of the rectangle.
    """
    
    y_bottom_index = best_result['y_bottom_index']
    y_top_index = best_result['y_top_index']
    
    # 1. Determine the exact Y-levels
    y_bottom = sweep_marks[y_bottom_index]['y']
    y_top = sweep_marks[y_top_index]['y']
    
    # 2. Re-sweep the range [y_bottom_index, y_top_index] to find the tightest X-boundaries
    
    # Initialize boundaries with the starting slice data
    max_x_left = sweep_marks[y_bottom_index]['x_left']
    min_x_right = sweep_marks[y_bottom_index]['x_right']
    
    # Iterate through the range of profile slices (from bottom index to top index, inclusive)
    for k in range(y_bottom_index, y_top_index + 1):
        slice_data = sweep_marks[k]
        
        # Max of all x_lefts defines the final rectangle's left edge
        if slice_data['x_left'] > max_x_left:
            max_x_left = slice_data['x_left']
        
        # Min of all x_rights defines the final rectangle's right edge
        if slice_data['x_right'] < min_x_right:
            min_x_right = slice_data['x_right']

    # We skip the problematic Step 2 from your original code entirely!
    
    # 3. Define the four corners using the guaranteed tight X-boundaries
    
    x_BL = max_x_left
    y_BL = y_bottom
    
    x_BR = min_x_right
    y_BR = y_bottom
    
    x_TR = min_x_right
    y_TR = y_top
    
    x_TL = max_x_left
    y_TL = y_top
    
    rectangle_coordinates_rotated = [
        (x_BL, y_BL), 
        (x_BR, y_BR), 
        (x_TR, y_TR), 
        (x_TL, y_TL)
    ]
    
    return rectangle_coordinates_rotated

# --- Hardcoded Constraints (For Dev Testing) ---
# These would be parameters in a final algorithm, but are hardcoded for this step.
MIN_WIDTH = 5.0
MIN_HEIGHT = 0.5
# --- Example Usage ---
# Define the coordinates for a simple polygon
originalPolygon = [(0, 0), (10, 0), (15, 5), (10, 15), (3, 12), (-5, 5)]

point_A = 4
point_B = point_A + 1
TA_line = (originalPolygon[point_A], originalPolygon[point_B])
#TA_line = (originalPolygon[0], originalPolygon[1])
zeroed_polygon = translate_and_reorder_polygon(originalPolygon, TA_line)
rotated_polygon, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line)

# ------ 
# left_chain_result, right_chain_result, y_min, y_max = split_polygon_chains(rotated_polygon)
# cross_section_data = sweep_line_width_profile(left_chain_result, right_chain_result, min_y=y_min, max_y=y_max, y_resolution=0.5)
# #perimeter_coords = get_cross_section_coordinates(cross_section_data) # --Dev Helper Function--
# best_rectangle = find_max_area_rectangle(cross_section_data, min_height=MIN_HEIGHT, min_width=MIN_WIDTH)
# largest_rectangle_coords = get_rectangle_coordinates(best_rectangle, cross_section_data)
# #print("largest_rectangle_coords Rectangle:", largest_rectangle_coords)
# plot_polygons([rotated_polygon,largest_rectangle_coords])
# ------


# Major Step 2: Find Largest Rectangle in Cross-Section
def major_step2(_rotated_polygon):
    left_chain_result, right_chain_result, y_min, y_max = split_polygon_chains(_rotated_polygon)
    cross_section_data = sweep_line_width_profile(left_chain_result, right_chain_result, min_y=y_min, max_y=y_max, y_resolution=0.5)
    best_rectangle = find_max_area_rectangle(cross_section_data, min_height=MIN_HEIGHT, min_width=MIN_WIDTH)
    largest_rectangle_coords = get_rectangle_coordinates(best_rectangle, cross_section_data)
    return largest_rectangle_coords




# First Round: Aligned with TA line
largest_rectangle_coords_parallel = major_step2(rotated_polygon)
# Second Round: Perpendicular to TA line
flipped_coordinates = flip_xy_coordinates(rotated_polygon)
largest_rectangle_coords_perpendicular = major_step2(flipped_coordinates)
# Un-flip the perpendicular rectangle coordinates
largest_rectangle_coords_perpendicular = flip_xy_coordinates(largest_rectangle_coords_perpendicular)

# Inverse Rotation (back to original orientation)
original_oriented_polygon = inverse_rotate_polygon(rotated_polygon, angle)
rect_parallel_oriented = inverse_rotate_polygon(largest_rectangle_coords_parallel, angle)
rect_perpendicular_oriented = inverse_rotate_polygon(largest_rectangle_coords_perpendicular, angle)

# Inverse Translation (back to original position)
final_polygon = inverse_translate_polygon(original_oriented_polygon, TA_line)
final_rect_parallel = inverse_translate_polygon(rect_parallel_oriented, TA_line)
final_rect_perpendicular = inverse_translate_polygon(rect_perpendicular_oriented, TA_line)

#plot_polygons([final_polygon,final_rect_parallel, final_rect_perpendicular])
plot_polygons([rotated_polygon,largest_rectangle_coords_parallel, largest_rectangle_coords_perpendicular])



# Original Main Function
def run_buildableSpaceFinder_algorithm(polygon_coordinates):

    zeroed_polygon = translate_and_reorder_polygon(polygon_coordinates, TA_line)
    rotated_polygon, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line)

        # First Round: Aligned with TA line
    largest_rectangle_coords_parallel = major_step2(rotated_polygon)
    # Second Round: Perpendicular to TA line
    flipped_coordinates = flip_xy_coordinates(rotated_polygon)
    largest_rectangle_coords_perpendicular = major_step2(flipped_coordinates)
    # Un-flip the perpendicular rectangle coordinates
    largest_rectangle_coords_perpendicular = flip_xy_coordinates(largest_rectangle_coords_perpendicular)

    # Inverse Rotation (back to original orientation)
    original_oriented_polygon = inverse_rotate_polygon(rotated_polygon, angle)
    rect_parallel_oriented = inverse_rotate_polygon(largest_rectangle_coords_parallel, angle)
    rect_perpendicular_oriented = inverse_rotate_polygon(largest_rectangle_coords_perpendicular, angle)

    # Inverse Translation (back to original position)
    final_polygon = inverse_translate_polygon(original_oriented_polygon, TA_line)
    final_rect_parallel = inverse_translate_polygon(rect_parallel_oriented, TA_line)
    final_rect_perpendicular = inverse_translate_polygon(rect_perpendicular_oriented, TA_line)

    return final_polygon, final_rect_parallel, final_rect_perpendicular

# -----------------------------------------------------------------------------
# ---------------------------- DEV ERROR TEST AREA ---------------------------- #
# -----------------------------------------------------------------------------


def major_step2___DEV_TEST_1(_rotated_polygon):
    left_chain_result, right_chain_result, y_min, y_max = split_polygon_chains(_rotated_polygon)
    cross_section_data = sweep_line_width_profile(left_chain_result, right_chain_result, min_y=y_min, max_y=y_max, y_resolution=0.5)
    best_rectangle = find_max_area_rectangle(cross_section_data, min_height=MIN_HEIGHT, min_width=MIN_WIDTH)
    largest_rectangle_coords = get_rectangle_coordinates(best_rectangle, cross_section_data)
    return left_chain_result, right_chain_result


# Development Test Function with Debugging Steps
def DEV__run_buildableSpaceFinder_algorithm_TEST__LeftAndRightChainTest(polygon_coordinates):

    zeroed_polygon = translate_and_reorder_polygon(polygon_coordinates, TA_line)
    rotated_polygon, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line)

        # First Round: Aligned with TA line
    left_chain_result, right_chain_result = major_step2___DEV_TEST_1(rotated_polygon)
    # Second Round: Perpendicular to TA line
    flipped_coordinates = flip_xy_coordinates(rotated_polygon)
    left_chain_result, right_chain_result = major_step2___DEV_TEST_1(flipped_coordinates)


    return left_chain_result, right_chain_result
