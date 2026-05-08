from app.algorithms.types.domain import ProcessedRoomData


def _simplify_path(vertices):
    """Helper to remove collinear points from a single list of vertices."""
    if len(vertices) < 3:
        return vertices

    # 1. Deduplicate consecutive identical points
    unique_points = []
    for pt in vertices:
        if not unique_points or pt != unique_points[-1]:
            unique_points.append(pt)

    # 2. Handle closed loop (remove end to process, we will re-add later)
    is_closed = False
    if len(unique_points) > 1 and unique_points[0] == unique_points[-1]:
        unique_points.pop()
        is_closed = True

    cleaned = []
    n = len(unique_points)

    for i in range(n):
        prev_pt = unique_points[i - 1]
        curr_pt = unique_points[i]
        next_pt = unique_points[(i + 1) % n]

        # Check for collinearity on X or Y axis
        collinear_x = (prev_pt[0] == curr_pt[0] == next_pt[0])
        collinear_y = (prev_pt[1] == curr_pt[1] == next_pt[1])

        # Only keep the point if it represents a turn (not collinear)
        if not (collinear_x or collinear_y):
            cleaned.append(curr_pt)

    # 3. Re-close the loop if necessary
    if is_closed and cleaned:
        cleaned.append(cleaned[0])

    return cleaned

def clean_floorplan_rectilinearity(room_list : list[ProcessedRoomData]):
    """
    Takes a list of ProcessedRoomData, simplifies the vertices for each room,
    and returns the updated list.
    """
    for room in room_list:
        # Update the vertices attribute in place
        room.vertices = _simplify_path(room.vertices)
    
    return room_list