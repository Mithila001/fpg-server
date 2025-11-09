#!/usr/bin/env python3

import math
from plotter2 import plot_polygons

def initializeLandSpaceCalculations(polygon_edges):
    """
    Calculates the line-equation parameters (ax + by = C) for each 
    polygon edge, offset by its specified 'OffsetDistance'.
    """
    offset_line_parameters = []

    for edge in polygon_edges:
        sx = edge['StartVertex_x']
        sy = edge['StartVertex_y']
        ex = edge['EndVertex_x']
        ey = edge['EndVertex_y']
        offset = edge['OffsetDistance']

        # 1. Derive Edge Vector
        vec_x = ex - sx
        vec_y = ey - sy

        # 2. Calculate Outward Normal Vector (90-degree clockwise)
        normal_x = vec_y
        normal_y = -vec_x

        # 3. Normalize the Normal Vector
        magnitude = math.sqrt(normal_x**2 + normal_y**2)
        norm_nx = 0.0
        norm_ny = 0.0
        
        if magnitude > 0:
            norm_nx = normal_x / magnitude
            norm_ny = normal_y / magnitude

        # 4. Calculate 'C' for the new offset line
        c_offset = (norm_nx * sx) + (norm_ny * sy) + offset

        line_params = {
            'a': norm_nx,
            'b': norm_ny,
            'C': c_offset
        }
        
        offset_line_parameters.append(line_params)

    return offset_line_parameters


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# ---               End of the algorithm          ---
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

def create_land_edges(vertices, offset_distances):
    """
    Creates the 'land_edges' list from a list of vertices and a 
    corresponding list of offset distances for each edge.

    Args:
        vertices (list): A list of (x, y) tuples representing the
                         polygon's vertices in CCW order.
        offset_distances (list): A list of offset values, one for each
                                 edge. The first offset corresponds to
                                 the edge from vertex 0 to vertex 1.

    Returns:
        list: A list of edge dictionaries formatted for
              initializeLandSpaceCalculations.
    """
    land_edges = []
    num_vertices = len(vertices)

    if num_vertices != len(offset_distances):
        print("Error: The number of vertices must equal the number of offsets.")
        return []

    for i in range(num_vertices):
        # Get the start vertex
        start_vertex_x = vertices[i][0]
        start_vertex_y = vertices[i][1]

        # Get the end vertex, looping back to the start for the last edge
        end_vertex_index = (i + 1) % num_vertices
        end_vertex_x = vertices[end_vertex_index][0]
        end_vertex_y = vertices[end_vertex_index][1]

        # Get the offset distance for this specific edge
        offset = offset_distances[i]

        edge = {
            "StartVertex_x": start_vertex_x,
            "StartVertex_y": start_vertex_y,
            "EndVertex_x": end_vertex_x,
            "EndVertex_y": end_vertex_y,
            "OffsetDistance": offset
        }
        land_edges.append(edge)
    
    return land_edges

def find_intersection(line1, line2):
    """
    Helper function to find the (x, y) intersection point of two lines.
    Uses Cramer's rule to solve the 2x2 system:
    a1*x + b1*y = C1
    a2*x + b2*y = C2
    """
    a1 = line1['a']
    b1 = line1['b']
    C1 = line1['C']
    
    a2 = line2['a']
    b2 = line2['b']
    C2 = line2['C']

    # Calculate the determinant
    D = (a1 * b2) - (a2 * b1)

    # If D is zero, lines are parallel or the same
    if abs(D) < 1e-9:  # Using a small number to avoid floating point issues
        print("Warning: Lines are parallel and do not intersect.")
        return None

    # Calculate Dx and Dy for Cramer's rule
    Dx = (C1 * b2) - (C2 * b1)
    Dy = (a1 * C2) - (a2 * C1)

    # Calculate the intersection point
    x = Dx / D
    y = Dy / D
    
    return (x, y)

def find_intersection_vertices(offset_lines):
    """
    Takes the list of offset line parameters (ax + by = C) and calculates
    the new polygon vertices by finding the intersection of adjacent lines.

    Args:
        offset_lines (list): The list of line parameter dictionaries
                             from initializeLandSpaceCalculations.

    Returns:
        list: A list of (x, y) tuples representing the new vertices
              of the buildable space.
    """
    new_vertices = []
    num_lines = len(offset_lines)
    
    if num_lines < 2:
        print("Error: Need at least 2 lines to find intersections.")
        return []

    for i in range(num_lines):
        # Get the first line
        line1 = offset_lines[i]
        
        # Get the second line, looping back to the start for the last vertex
        line2_index = (i + 1) % num_lines
        line2 = offset_lines[line2_index]

        # Find the intersection of line_i and line_i+1
        intersection_point = find_intersection(line1, line2)
        
        if intersection_point:
            new_vertices.append(intersection_point)
            
    return new_vertices


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# ---               EXAMPLE USAGE & NEXT STEPS          ---
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
if __name__ == "__main__":
    
    # --- --- --- --- --- --- --- --- --- ---
    # --- STEP 1: Define Your Land Plot   ---
    # --- --- --- --- --- --- --- --- --- ---
    
    # A simple 100x100 square
    land_plot_vertices = [
        (4,4),
        (2,0),
        (10, 0),
        (10, 5)
    ]
    
    # Define the *inward* setback for each edge.
    # We use negative numbers for an *inward* offset.
    # -10 for the bottom, -20 for the right, -10 for the top, -20 for the left.
    setbacks = [.5, .8, .5, 10]

    print("--- STEP 1: Initial Data ---")
    print(f"Land Vertices: {land_plot_vertices}")
    print(f"Setbacks:      {setbacks}")

    # --- --- --- --- --- --- --- --- --- ---
    # --- STEP 2: Create Edge Objects     ---
    # --- --- --- --- --- --- --- --- --- ---
    
    land_edges = create_land_edges(land_plot_vertices, setbacks)
    
    print("\n--- STEP 2: Generated Land Edges (for algorithm) ---")
    for i, edge in enumerate(land_edges):
        print(f"Edge {i}: {edge}")
        
    # --- --- --- --- --- --- --- --- --- ---
    # --- STEP 3: Calculate Offset Lines  ---
    # --- --- --- --- --- --- --- --- --- ---
    
    offset_lines = initializeLandSpaceCalculations(land_edges)
    
    print("\n--- STEP 3: Calculated Offset Lines (ax + by = C) ---")
    for i, line in enumerate(offset_lines):
        # Print with formatting to make it easier to read
        print(f"Line {i}: a={line['a']:>6.2f}, b={line['b']:>6.2f}, C={line['C']:>7.2f}")

    # --- --- --- --- --- --- --- --- --- ---
    # --- STEP 4: Find New Vertices     ---
    # --- --- --- --- --- --- --- --- --- ---

    buildable_vertices = find_intersection_vertices(offset_lines)
    print("buildable_vertices: ", buildable_vertices)

    plot_polygons([land_plot_vertices, buildable_vertices])
    
    # print("\n--- STEP 4: Final Buildable Space Vertices ---")
    # for i, vertex in enumerate(buildable_vertices):
    #     # Format (x, y) to 2 decimal places
    #     print(f"Vertex {i}: (x={vertex[0]:.2f}, y={vertex[1]:.2f})")

    # --- Verification for this example ---
    # Vertex 0 (Line 3 & Line 0): Intersection of x=20 and y=10 -> (20, 10)
    # Vertex 1 (Line 0 & Line 1): Intersection of y=10 and x=80 -> (80, 10)
    # Vertex 2 (Line 1 & Line 2): Intersection of x=80 and y=90 -> (80, 90)
    # Vertex 3 (Line 2 & Line 3): Intersection of y=90 and x=20 -> (20, 90)
    # The output matches our logic.