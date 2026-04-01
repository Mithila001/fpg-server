from ortools.sat.python import cp_model

from ...solver_models.room import Room
from ...utils.seed_layout import SeedLayoutContext, axis_overlap_len, get_seed_room_bounds


def build_seed_facade_alignment_penalty(
    model: cp_model.CpModel,
    rooms: list[Room],
    context: SeedLayoutContext,
    floor_plan_width: float,
    floor_plan_height: float,
    align_weight: int,
    align_threshold: int,
) -> cp_model.LinearExprT:
    if len(context.by_name) < 2:
        return 0

    rooms_by_name = {room.name: room for room in rooms}
    names = [name for name in context.by_name.keys() if name in rooms_by_name]
    if len(names) < 2:
        return 0

    max_w = max(1, int(floor_plan_width))
    max_h = max(1, int(floor_plan_height))
    terms: list[cp_model.IntVar] = []

    for i, name_a in enumerate(names):
        seed_a = context.by_name[name_a]
        ax, ay, ax_end, ay_end = get_seed_room_bounds(seed_a)
        room_a = rooms_by_name[name_a]
        assert room_a.x is not None and room_a.y is not None
        assert room_a.x_end is not None and room_a.y_end is not None

        for name_b in names[i + 1 :]:
            seed_b = context.by_name[name_b]
            bx, by, bx_end, by_end = get_seed_room_bounds(seed_b)
            room_b = rooms_by_name[name_b]
            assert room_b.x is not None and room_b.y is not None
            assert room_b.x_end is not None and room_b.y_end is not None

            y_overlap = axis_overlap_len(ay, ay_end, by, by_end)
            x_overlap = axis_overlap_len(ax, ax_end, bx, bx_end)

            if y_overlap >= 1:
                dx_left = abs(ax - bx)
                if 0 < dx_left <= align_threshold:
                    align_left = model.NewIntVar(0, max_w, f"c_x_{name_a}_{name_b}")  # type: ignore
                    model.AddAbsEquality(align_left, room_a.x - room_b.x)  # type: ignore
                    terms.append(align_left)

                dx_right = abs(ax_end - bx_end)
                if 0 < dx_right <= align_threshold:
                    align_right = model.NewIntVar(0, max_w, f"c_xe_{name_a}_{name_b}")  # type: ignore
                    model.AddAbsEquality(align_right, room_a.x_end - room_b.x_end)  # type: ignore
                    terms.append(align_right)

            if x_overlap >= 1:
                dy_bottom = abs(ay - by)
                if 0 < dy_bottom <= align_threshold:
                    align_bottom = model.NewIntVar(0, max_h, f"c_y_{name_a}_{name_b}")  # type: ignore
                    model.AddAbsEquality(align_bottom, room_a.y - room_b.y)  # type: ignore
                    terms.append(align_bottom)

                dy_top = abs(ay_end - by_end)
                if 0 < dy_top <= align_threshold:
                    align_top = model.NewIntVar(0, max_h, f"c_ye_{name_a}_{name_b}")  # type: ignore
                    model.AddAbsEquality(align_top, room_a.y_end - room_b.y_end)  # type: ignore
                    terms.append(align_top)

    if not terms:
        return 0

    weighted_terms: list[cp_model.LinearExprT] = [term * align_weight for term in terms]
    return cp_model.LinearExpr.Sum(weighted_terms)  # type: ignore
