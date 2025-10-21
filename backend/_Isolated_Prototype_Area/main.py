import math
from plotter import plot_polygons
from myUtilities import calculate_distance

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


# --- Example Usage ---
# Define the coordinates for a simple polygon
originalPolygon = [(0,1), (2,4), (6,6), (10,1)]

TA_line = ((6,6), (10,1))
zeroed_polygon = translate_to_origin(originalPolygon, TA_line)
#plot_polygons([originalPolygon, zeroed_polygon])
relative_coordinates, angle = rotate_polygon_to_x_axis(zeroed_polygon, TA_line)

print("Original Polygon:")
print(originalPolygon)
print("Rotated Polygon:")
print(relative_coordinates)

plot_polygons([originalPolygon,zeroed_polygon, relative_coordinates])
##plot_polygons([originalPolygon, zeroed_polygon])
print("Plot displayed.")
