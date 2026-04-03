from ortools.sat.python import cp_model

from ...solver_models.room import Room


def build_layout_dead_space_penalty(
    model: cp_model.CpModel,
    rooms: list[Room],
    floor_plan_width: float,
    floor_plan_height: float,
    dead_space_weight: int,
) -> cp_model.LinearExprT:
    if not rooms:
        return 0

    x_vars = []
    y_vars = []
    x_end_vars = []
    y_end_vars = []
    area_vars = []

    for room in rooms:
        assert room.x is not None and room.y is not None
        assert room.x_end is not None and room.y_end is not None
        assert room.area is not None
        x_vars.append(room.x)
        y_vars.append(room.y)
        x_end_vars.append(room.x_end)
        y_end_vars.append(room.y_end)
        area_vars.append(room.area)

    w_int = int(floor_plan_width)
    h_int = int(floor_plan_height)

    left_edge = model.NewIntVar(0, w_int, "a_bbox_left")  # type: ignore
    right_edge = model.NewIntVar(0, w_int, "a_bbox_right")  # type: ignore
    bottom_edge = model.NewIntVar(0, h_int, "a_bbox_bottom")  # type: ignore
    top_edge = model.NewIntVar(0, h_int, "a_bbox_top")  # type: ignore

    model.AddMinEquality(left_edge, x_vars)  # type: ignore
    model.AddMaxEquality(right_edge, x_end_vars)  # type: ignore
    model.AddMinEquality(bottom_edge, y_vars)  # type: ignore
    model.AddMaxEquality(top_edge, y_end_vars)  # type: ignore

    bbox_w = model.NewIntVar(0, w_int, "a_bbox_w")  # type: ignore
    bbox_h = model.NewIntVar(0, h_int, "a_bbox_h")  # type: ignore
    model.Add(bbox_w == right_edge - left_edge)  # type: ignore
    model.Add(bbox_h == top_edge - bottom_edge)  # type: ignore

    bbox_area = model.NewIntVar(0, w_int * h_int, "a_bbox_area")  # type: ignore
    model.AddMultiplicationEquality(bbox_area, [bbox_w, bbox_h])  # type: ignore

    rooms_area_sum = model.NewIntVar(0, w_int * h_int, "a_rooms_area_sum")  # type: ignore
    model.Add(rooms_area_sum == cp_model.LinearExpr.Sum(area_vars))  # type: ignore

    dead_space = model.NewIntVar(0, w_int * h_int, "a_dead_space")  # type: ignore
    model.Add(dead_space == bbox_area - rooms_area_sum)  # type: ignore
    return dead_space * dead_space_weight
