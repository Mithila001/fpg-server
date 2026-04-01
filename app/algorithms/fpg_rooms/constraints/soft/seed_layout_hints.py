from typing import Any

from ortools.sat.python import cp_model

from ...solver_models.room import Room
from ...utils.seed_layout import build_seed_layout_context


def apply_seed_layout_hints_with_wiggle(
    model: cp_model.CpModel,
    rooms: list[Room],
    seed_layout: list[dict[str, Any]],
    floor_plan_width: float,
    floor_plan_height: float,
    wiggle_room: int = 0,
) -> None:
    context = build_seed_layout_context(seed_layout)
    if context is None:
        return

    seed_by_name = context.by_name
    w_int = int(floor_plan_width)
    h_int = int(floor_plan_height)
    wiggle = max(0, int(wiggle_room))

    for room in rooms:
        seed = seed_by_name.get(room.name)
        if seed is None:
            continue

        assert room.x is not None and room.y is not None
        assert room.w is not None and room.h is not None

        sx = int(seed.get("x", 0))
        sy = int(seed.get("y", 0))

        seed_w_raw = seed.get("w")
        seed_h_raw = seed.get("h")
        if seed_w_raw is None:
            seed_x_end = int(seed.get("x_end", sx + room.min_w))
            seed_w_raw = seed_x_end - sx
        if seed_h_raw is None:
            seed_y_end = int(seed.get("y_end", sy + room.min_h))
            seed_h_raw = seed_y_end - sy

        sw = int(seed_w_raw)
        sh = int(seed_h_raw)
        sw = max(room.min_w, min(room.max_w, sw))
        sh = max(room.min_h, min(room.max_h, sh))

        model.AddHint(room.x, sx)
        model.AddHint(room.y, sy)
        model.AddHint(room.w, sw)
        model.AddHint(room.h, sh)

        if wiggle <= 0:
            continue

        x_lb = max(0, sx - wiggle)
        y_lb = max(0, sy - wiggle)
        w_lb = max(room.min_w, sw - wiggle)
        h_lb = max(room.min_h, sh - wiggle)

        x_ub = min(w_int - room.min_w, sx + wiggle)
        y_ub = min(h_int - room.min_h, sy + wiggle)
        w_ub = min(room.max_w, sw + wiggle)
        h_ub = min(room.max_h, sh + wiggle)

        model.Add(room.x >= min(x_lb, x_ub))  # type: ignore
        model.Add(room.x <= max(x_lb, x_ub))  # type: ignore
        model.Add(room.y >= min(y_lb, y_ub))  # type: ignore
        model.Add(room.y <= max(y_lb, y_ub))  # type: ignore

        model.Add(room.w >= min(w_lb, w_ub))  # type: ignore
        model.Add(room.w <= max(w_lb, w_ub))  # type: ignore
        model.Add(room.h >= min(h_lb, h_ub))  # type: ignore
        model.Add(room.h <= max(h_lb, h_ub))  # type: ignore
