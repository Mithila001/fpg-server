import math


def calculate_distance(p1, p2=(0, 0)):
    """Calculates the Euclidean distance between two points."""
    x1, y1 = p1
    x2, y2 = p2
    # The basic distance formula: sqrt((x2-x1)^2 + (y2-y1)^2)
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def find_active_segment(chain, y_sweep):
    """
    Finds the segment (p1, p2) in a chain that the sweep line y_sweep crosses.
    
    Args:
        chain: List of (x, y) tuples.
        y_sweep: The Y-coordinate of the sweep line.
        
    Returns:
        A tuple: (p1, p2) representing the active segment, or None if not found.
    """
    
    # Check if the chain is stored 'upwards' (y-coordinates generally increasing)
    # The left chain typically runs from min_y to max_y.
    # We check the Y relationship of the first two points to determine the direction.
    is_upwards_chain = chain[0][1] < chain[1][1]
    
    # Iterate through segments (p1, p2)
    for i in range(len(chain) - 1):
        p1 = chain[i]
        p2 = chain[i+1]
        
        y1 = p1[1]
        y2 = p2[1]

        # General check: does y_sweep fall between y1 and y2?
        y_min_seg = min(y1, y2)
        y_max_seg = max(y1, y2)
        
        # We look for the segment where y_sweep is greater than the lower point and 
        # less than or equal to the upper point. This prevents double-counting at vertices.
        if y_min_seg < y_sweep <= y_max_seg:
            
            # The specific rule you mentioned (y1 < y <= y2) means the chain is
            # stored in ascending y-order (upwards).
            if is_upwards_chain:
                # Left Chain logic: p1 is the lower point, p2 is the upper point.
                if y1 < y_sweep <= y2:
                    return p1, p2
            else:
                # Right Chain logic: p1 is the upper point, p2 is the lower point.
                # The segment still crosses if y_sweep is between the two y values.
                # Since the chain is downwards, we are looking for the segment
                # where the sweep line is between y1 (upper) and y2 (lower).
                if y2 < y_sweep <= y1:
                    return p1, p2
                    
    return None


def get_x_intersection(p1, p2, y_sweep):
    """
    Calculates the X-coordinate where the horizontal sweep line (y_sweep) 
    intersects the line segment defined by (p1, p2).
    
    Uses linear interpolation: x = x1 + (y_sweep - y1) * (x2 - x1) / (y2 - y1)
    
    Args:
        p1: The first point (x1, y1).
        p2: The second point (x2, y2).
        y_sweep: The Y-coordinate of the sweep line.
        
    Returns:
        The interpolated X-coordinate.
    """
    (x1, y1) = p1
    (x2, y2) = p2
    
    # Handle the case of a horizontal segment (y1 == y2)
    if math.isclose(y1, y2):
        # The line is on the sweep line, any x between x1 and x2 is valid.
        # We can return the x-coordinate of the point with the lower y (p1).
        return x1 
        
    # Calculate the intersection X coordinate
    # dy is the change in y across the segment
    dy = y2 - y1
    
    # ratio is the proportion of the segment's height covered by the sweep line
    ratio = (y_sweep - y1) / dy
    
    # dx is the change in x across the segment
    dx = x2 - x1
    
    x_intersect = x1 + ratio * dx
    
    return x_intersect