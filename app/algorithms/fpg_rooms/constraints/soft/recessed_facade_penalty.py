from ortools.sat.python import cp_model

from ...solver_models.room import Room
from ...utils.seed_layout import SeedLayoutContext, axis_overlap_len, get_seed_room_bounds
from ...utils.solver_penalty_builders import build_excess_depth_penalty


def build_recessed_facade_penalty(
    model: cp_model.CpModel,
    rooms: list[Room],
    context: SeedLayoutContext,
    floor_plan_width: float,
    floor_plan_height: float,
    near_band: int,
    base_threshold: int,
    severe_threshold: int,
    base_weight: int,
    severe_weight: int,
    attach_weight: int,
    side_gap_threshold: int,
) -> cp_model.LinearExprT:
    side_near_names: dict[str, set[str]] = {
        "front": set(),
        "back": set(),
        "left": set(),
        "right": set(),
    }

    for room in context.by_name.values():
        name = str(room.get("name"))
        sx, sy, sx_end, sy_end = get_seed_room_bounds(room)

        if context.front_line - sy_end <= near_band:
            side_near_names["front"].add(name)
        if sy - context.back_line <= near_band:
            side_near_names["back"].add(name)
        if sx - context.left_line <= near_band:
            side_near_names["left"].add(name)
        if context.right_line - sx_end <= near_band:
            side_near_names["right"].add(name)

    depth_terms: list[cp_model.LinearExprT] = []
    attach_terms: list[cp_model.IntVar] = []
    max_w = max(1, int(floor_plan_width))
    max_h = max(1, int(floor_plan_height))

    rooms_by_name = {room.name: room for room in rooms}

    for room in rooms:
        assert room.x is not None and room.y is not None
        assert room.x_end is not None and room.y_end is not None

        if room.name in side_near_names["front"]:
            base = build_excess_depth_penalty(
                model,
                depth_expr=context.front_line - room.y_end,
                threshold=base_threshold,
                max_depth=max_h,
                name=f"d_front_{room.name}_base",
            )
            severe = build_excess_depth_penalty(
                model,
                depth_expr=context.front_line - room.y_end,
                threshold=severe_threshold,
                max_depth=max_h,
                name=f"d_front_{room.name}_severe",
            )
            depth_terms.append(base * base_weight)
            depth_terms.append(severe * severe_weight)

        if room.name in side_near_names["back"]:
            base = build_excess_depth_penalty(
                model,
                depth_expr=room.y - context.back_line,
                threshold=base_threshold,
                max_depth=max_h,
                name=f"d_back_{room.name}_base",
            )
            severe = build_excess_depth_penalty(
                model,
                depth_expr=room.y - context.back_line,
                threshold=severe_threshold,
                max_depth=max_h,
                name=f"d_back_{room.name}_severe",
            )
            depth_terms.append(base * base_weight)
            depth_terms.append(severe * severe_weight)

        if room.name in side_near_names["left"]:
            base = build_excess_depth_penalty(
                model,
                depth_expr=room.x - context.left_line,
                threshold=base_threshold,
                max_depth=max_w,
                name=f"d_left_{room.name}_base",
            )
            severe = build_excess_depth_penalty(
                model,
                depth_expr=room.x - context.left_line,
                threshold=severe_threshold,
                max_depth=max_w,
                name=f"d_left_{room.name}_severe",
            )
            depth_terms.append(base * base_weight)
            depth_terms.append(severe * severe_weight)

        if room.name in side_near_names["right"]:
            base = build_excess_depth_penalty(
                model,
                depth_expr=context.right_line - room.x_end,
                threshold=base_threshold,
                max_depth=max_w,
                name=f"d_right_{room.name}_base",
            )
            severe = build_excess_depth_penalty(
                model,
                depth_expr=context.right_line - room.x_end,
                threshold=severe_threshold,
                max_depth=max_w,
                name=f"d_right_{room.name}_severe",
            )
            depth_terms.append(base * base_weight)
            depth_terms.append(severe * severe_weight)

    for side, names in side_near_names.items():
        side_list = [name for name in names if name in rooms_by_name]
        for i, name_a in enumerate(side_list):
            ax, ay, ax_end, ay_end = get_seed_room_bounds(context.by_name[name_a])
            room_a = rooms_by_name[name_a]
            assert room_a.x is not None and room_a.y is not None
            assert room_a.x_end is not None and room_a.y_end is not None

            for name_b in side_list[i + 1 :]:
                bx, by, bx_end, by_end = get_seed_room_bounds(context.by_name[name_b])
                room_b = rooms_by_name[name_b]
                assert room_b.x is not None and room_b.y is not None
                assert room_b.x_end is not None and room_b.y_end is not None

                if side in ("front", "back"):
                    if axis_overlap_len(ax, ax_end, bx, bx_end) < 1:
                        continue
                    seed_gap = abs(ay_end - by_end) if side == "front" else abs(ay - by)
                    if 0 < seed_gap <= side_gap_threshold:
                        align_var = model.NewIntVar(0, max_h, f"d_attach_{side}_{name_a}_{name_b}")  # type: ignore
                        if side == "front":
                            model.AddAbsEquality(align_var, room_a.y_end - room_b.y_end)  # type: ignore
                        else:
                            model.AddAbsEquality(align_var, room_a.y - room_b.y)  # type: ignore
                        attach_terms.append(align_var)
                else:
                    if axis_overlap_len(ay, ay_end, by, by_end) < 1:
                        continue
                    seed_gap = abs(ax - bx) if side == "left" else abs(ax_end - bx_end)
                    if 0 < seed_gap <= side_gap_threshold:
                        align_var = model.NewIntVar(0, max_w, f"d_attach_{side}_{name_a}_{name_b}")  # type: ignore
                        if side == "left":
                            model.AddAbsEquality(align_var, room_a.x - room_b.x)  # type: ignore
                        else:
                            model.AddAbsEquality(align_var, room_a.x_end - room_b.x_end)  # type: ignore
                        attach_terms.append(align_var)

    if not depth_terms and not attach_terms:
        return 0

    weighted_terms: list[cp_model.LinearExprT] = []
    weighted_terms.extend(depth_terms)
    weighted_terms.extend([term * attach_weight for term in attach_terms])
    return cp_model.LinearExpr.Sum(weighted_terms)  # type: ignore
