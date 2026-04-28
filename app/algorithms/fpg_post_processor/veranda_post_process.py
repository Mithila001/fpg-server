import json


def modify_veranda_layout(floor_plan):
    # --- Step 1: Extract the specific rooms ---
    veranda = next((r for r in floor_plan if r["type"] == "veranda"), None)
    outdoor = next((r for r in floor_plan if r["type"] == "verandaOutdoorSpace"), None)

    if not veranda or not outdoor:
        print("[DEBUG] Missing veranda or verandaOutdoorSpace. No action taken.")
        return floor_plan

    # Calculate Floor Plan Width (max x_end - min x)
    min_x_total = min(r["x"] for r in floor_plan)
    max_x_total = max(r["x_end"] for r in floor_plan)
    floor_plan_width = max_x_total - min_x_total

    # Identify candidate wall and direction
    # If outdoor is to the left of veranda
    if outdoor["x_end"] == veranda["x"]:
        candidate_wall_x = veranda["x"]
        movable_direction = "left"
    # If outdoor is to the right of veranda
    elif outdoor["x"] == veranda["x_end"]:
        candidate_wall_x = veranda["x_end"]
        movable_direction = "right"
    else:
        print(
            "[DEBUG] Veranda and Outdoor space are not vertically adjacent. No action taken."
        )
        return floor_plan

    # Candidate wall point is at the back side (+y side)
    candidate_wall_y_point = veranda["y_end"]

    # --- Step 2: Identify Movable Range and Snap Points ---

    # Movable range based on the outdoor space horizontal bounds
    movable_range = (outdoor["x"], outdoor["x_end"])

    # Find all x-coordinates of any room corner that exists at the same y-level
    # as our candidate wall point
    snap_points = set()
    for room in floor_plan:
        if (
            room["y"] == candidate_wall_y_point
            or room["y_end"] == candidate_wall_y_point
        ):
            snap_points.add(room["x"])
            snap_points.add(room["x_end"])

    # Filter snap points that fall within the movable range
    valid_hops = [x for x in snap_points if movable_range[0] <= x <= movable_range[1]]

    if not valid_hops:
        print(
            f"[DEBUG] No valid snap points found at y={candidate_wall_y_point} within range {movable_range}."
        )
        return floor_plan

    # Determine the target X (we want to expand as much as possible within the range)
    if movable_direction == "left":
        target_x = min(valid_hops)
    else:
        target_x = max(valid_hops)

    # --- Step 3: Rule Validation ---

    # Rule: Should only stop on candidate wall points (already handled by valid_hops)
    if target_x == candidate_wall_x:
        print("[DEBUG] Target X is same as current X. No expansion possible.")
        return floor_plan

    # Calculate new potential width
    if movable_direction == "left":
        new_w = veranda["w"] + (candidate_wall_x - target_x)
    else:
        new_w = veranda["w"] + (target_x - candidate_wall_x)

    # Rule: Total veranda width should not be >= floor plan width
    if new_w >= floor_plan_width:
        print(
            f"[DEBUG] Expansion failed: New width {new_w} >= Floor plan width {floor_plan_width}"
        )
        return floor_plan

    # --- Step 4: Apply Modifications ---

    # Update Veranda
    if movable_direction == "left":
        veranda["x"] = target_x
    else:
        veranda["x_end"] = target_x

    veranda["w"] = new_w
    veranda["area"] = veranda["w"] * veranda["h"]

    # Adjust Outdoor Space (shrink it or move it to prevent overlap)
    if movable_direction == "left":
        outdoor["x_end"] = target_x
    else:
        outdoor["x"] = target_x

    outdoor["w"] = outdoor["x_end"] - outdoor["x"]
    outdoor["area"] = outdoor["w"] * outdoor["h"]

    print(
        f"[SUCCESS] Expanded veranda {movable_direction} to x={target_x}. New width: {veranda['w']}"
    )
    return floor_plan


# --- Example Execution ---
if __name__ == "__main__":
    data = [
        {
            "name": "bedroom1",
            "type": "bedroom",
            "x": 105,
            "y": 57,
            "w": 45,
            "h": 30,
            "x_end": 150,
            "y_end": 87,
            "area": 1350,
        },
        {
            "name": "bedroom2",
            "type": "bedroom",
            "x": 57,
            "y": 0,
            "w": 31,
            "h": 45,
            "x_end": 88,
            "y_end": 45,
            "area": 1395,
        },
        {
            "name": "bathroom1",
            "type": "bathroom",
            "x": 0,
            "y": 62,
            "w": 16,
            "h": 25,
            "x_end": 16,
            "y_end": 87,
            "area": 400,
        },
        {
            "name": "kitchen1",
            "type": "kitchen",
            "x": 88,
            "y": 7,
            "w": 27,
            "h": 40,
            "x_end": 115,
            "y_end": 47,
            "area": 1080,
        },
        {
            "name": "attachedBathroom1",
            "type": "attachedBathroom",
            "x": 39,
            "y": 0,
            "w": 18,
            "h": 27,
            "x_end": 57,
            "y_end": 27,
            "area": 486,
        },
        {
            "name": "veranda1",
            "type": "veranda",
            "x": 1,
            "y": 0,
            "w": 38,
            "h": 29,
            "x_end": 39,
            "y_end": 29,
            "area": 1102,
        },
        {
            "name": "garage1",
            "type": "garage",
            "x": 115,
            "y": 0,
            "w": 35,
            "h": 57,
            "x_end": 150,
            "y_end": 57,
            "area": 1995,
        },
        {
            "name": "diningRoom1",
            "type": "diningRoom",
            "x": 57,
            "y": 57,
            "w": 48,
            "h": 30,
            "x_end": 105,
            "y_end": 87,
            "area": 1440,
        },
        {
            "name": "livingRoom1",
            "type": "livingRoom",
            "x": 16,
            "y": 29,
            "w": 41,
            "h": 48,
            "x_end": 57,
            "y_end": 77,
            "area": 1968,
        },
        {
            "name": "hallway1",
            "type": "hallway",
            "x": 57,
            "y": 47,
            "w": 58,
            "h": 10,
            "x_end": 115,
            "y_end": 57,
            "area": 580,
        },
        {
            "name": "hallway2",
            "type": "hallway",
            "x": 16,
            "y": 77,
            "w": 41,
            "h": 10,
            "x_end": 57,
            "y_end": 87,
            "area": 410,
        },
        {
            "name": "verandaOutdoorSpace_for_veranda1",
            "type": "verandaOutdoorSpace",
            "x": 0,
            "y": 0,
            "w": 1,
            "h": 29,
            "x_end": 1,
            "y_end": 29,
            "area": 29,
        },
    ]

    modified_plan = modify_veranda_layout(data)
    # print(json.dumps(modified_plan, indent=2))
