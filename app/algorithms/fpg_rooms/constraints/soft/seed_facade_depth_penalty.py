from ortools.sat.python import cp_model

from ...solver_models.room import Room
from ...utils.seed_layout import SeedLayoutContext
from ...utils.solver_penalty_builders import build_excess_count_penalty, build_side_depth_penalty


def build_seed_facade_depth_penalty(
    model: cp_model.CpModel,
    rooms: list[Room],
    context: SeedLayoutContext,
    floor_plan_width: float,
    floor_plan_height: float,
    depth_weight: int,
) -> cp_model.LinearExprT:
    side_facing_names = context.side_facing_names

    terms: list[cp_model.IntVar] = []
    side_recessed: dict[str, list[cp_model.IntVar]] = {
        "front": [],
        "back": [],
        "left": [],
        "right": [],
    }

    for room in rooms:
        assert room.x is not None and room.y is not None
        assert room.x_end is not None and room.y_end is not None

        if room.name in side_facing_names["front"]:
            penalty, recessed = build_side_depth_penalty(
                model,
                depth_expr=context.front_line - room.y_end,
                name=f"b_front_{room.name}",
                max_depth=max(1, int(floor_plan_height)),
            )
            terms.append(penalty)
            side_recessed["front"].append(recessed)

        if room.name in side_facing_names["back"]:
            penalty, recessed = build_side_depth_penalty(
                model,
                depth_expr=room.y - context.back_line,
                name=f"b_back_{room.name}",
                max_depth=max(1, int(floor_plan_height)),
            )
            terms.append(penalty)
            side_recessed["back"].append(recessed)

        if room.name in side_facing_names["left"]:
            penalty, recessed = build_side_depth_penalty(
                model,
                depth_expr=room.x - context.left_line,
                name=f"b_left_{room.name}",
                max_depth=max(1, int(floor_plan_width)),
            )
            terms.append(penalty)
            side_recessed["left"].append(recessed)

        if room.name in side_facing_names["right"]:
            penalty, recessed = build_side_depth_penalty(
                model,
                depth_expr=context.right_line - room.x_end,
                name=f"b_right_{room.name}",
                max_depth=max(1, int(floor_plan_width)),
            )
            terms.append(penalty)
            side_recessed["right"].append(recessed)

    terms.append(
        build_excess_count_penalty(
            model,
            vars_to_count=side_recessed["front"],
            max_allowed=0 if len(side_facing_names["front"]) < 1 else 2,
            name="b_front_count",
        )
    )
    combined_lr = side_recessed["left"] + side_recessed["right"]
    terms.append(
        build_excess_count_penalty(
            model,
            vars_to_count=combined_lr,
            max_allowed=0 if (len(side_facing_names["left"]) + len(side_facing_names["right"])) < 2 else 1,
            name="b_left_right_count",
        )
    )
    terms.append(
        build_excess_count_penalty(
            model,
            vars_to_count=side_recessed["back"],
            max_allowed=0 if len(side_facing_names["back"]) < 1 else 1,
            name="b_back_count",
        )
    )

    weighted_terms: list[cp_model.LinearExprT] = [term * depth_weight for term in terms]
    return cp_model.LinearExpr.Sum(weighted_terms)  # type: ignore
