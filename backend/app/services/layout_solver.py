from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Room:
    id: int
    width: int
    height: int
    x: Optional[int] = None
    y: Optional[int] = None

@dataclass
class Rectangle:
    x: int
    y: int
    width: int
    height: int

def solve_layout(
    rooms: List[Room], 
    boundary: Rectangle
) -> Optional[List[Room]]:
    """
    Solves the floor plan layout using a backtracking algorithm.
    """
    
    # We will sort the rooms by size, largest first. This is a common heuristic
    # for bin packing problems that often leads to a solution faster.
    rooms.sort(key=lambda r: r.width * r.height, reverse=True)
    
    solution_found, placed_rooms = _solve_layout_recursive(rooms, [boundary])
    
    if solution_found:
        return placed_rooms
    return None

def _solve_layout_recursive(
    rooms: List[Room], 
    free_rects: List[Rectangle]
) -> tuple[bool, List[Room]]:
    """
    The main recursive backtracking function.
    """
    if not rooms:
        # Base case: All rooms have been placed successfully
        return True, []

    current_room = rooms[0]
    remaining_rooms = rooms[1:]

    # Iterate through each free rectangle to try and place the current room
    # We'll also try a rotated version of the room.
    placement_options = [(current_room.width, current_room.height), (current_room.height, current_room.width)]
    
    for rect_index, free_rect in enumerate(free_rects):
        for room_width, room_height in placement_options:
            
            # Check if the room fits
            if room_width <= free_rect.width and room_height <= free_rect.height:
                
                # Place the room
                current_room.x = free_rect.x
                current_room.y = free_rect.y
                current_room.width = room_width
                current_room.height = room_height
                
                # Create new free rectangles for the remaining space
                new_free_rects = free_rects[:rect_index] + free_rects[rect_index+1:]

                # We need a more robust splitting logic here. A simple split
                # creates new rectangles based on the remaining space.
                new_rect1 = Rectangle(
                    x=free_rect.x + room_width,
                    y=free_rect.y,
                    width=free_rect.width - room_width,
                    height=room_height
                )
                
                new_rect2 = Rectangle(
                    x=free_rect.x,
                    y=free_rect.y + room_height,
                    width=free_rect.width,
                    height=free_rect.height - room_height
                )
                
                # Add only the valid new rectangles
                if new_rect1.width > 0 and new_rect1.height > 0:
                    new_free_rects.append(new_rect1)
                if new_rect2.width > 0 and new_rect2.height > 0:
                    new_free_rects.append(new_rect2)
                    
                # Recursively try to place the rest of the rooms
                solution_found, placed_rooms = _solve_layout_recursive(
                    remaining_rooms, new_free_rects
                )
                
                if solution_found:
                    return True, [current_room] + placed_rooms
            
    # If we get here, no placement worked for the current room
    current_room.x = None # Reset for backtracking
    current_room.y = None
    return False, []