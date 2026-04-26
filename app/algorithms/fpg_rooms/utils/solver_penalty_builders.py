from ortools.sat.python import cp_model
from typing import Any


def build_excess_depth_penalty(
    model: Any,
    depth_expr: cp_model.LinearExprT,
    threshold: int,
    max_depth: int,
    name: str,
) -> cp_model.IntVar:
    depth = model.NewIntVar(-max_depth, max_depth, f"{name}_depth")  # type: ignore
    model.Add(depth == depth_expr)

    depth_pos = model.NewIntVar(0, max_depth, f"{name}_depth_pos")  # type: ignore
    model.AddMaxEquality(depth_pos, [depth, 0])  # type: ignore

    raw_excess = model.NewIntVar(-max_depth, max_depth, f"{name}_raw_excess")  # type: ignore
    model.Add(raw_excess == depth_pos - threshold)

    excess = model.NewIntVar(0, max_depth, f"{name}_excess")  # type: ignore
    model.AddMaxEquality(excess, [raw_excess, 0])  # type: ignore
    return excess


def build_side_depth_penalty(
    model: Any,
    depth_expr: cp_model.LinearExprT,
    name: str,
    max_depth: int,
) -> tuple[cp_model.IntVar, cp_model.IntVar]:
    depth = model.NewIntVar(-max_depth, max_depth, f"{name}_depth")  # type: ignore
    model.Add(depth == depth_expr)

    depth_pos = model.NewIntVar(0, max_depth, f"{name}_depth_pos")  # type: ignore
    model.AddMaxEquality(depth_pos, [depth, 0])  # type: ignore

    recessed = model.NewBoolVar(f"{name}_recessed")  # type: ignore
    model.Add(depth_pos >= 1).OnlyEnforceIf(recessed)
    model.Add(depth_pos == 0).OnlyEnforceIf(recessed.Not())

    too_large_raw = model.NewIntVar(-max_depth, max_depth, f"{name}_too_large_raw")  # type: ignore
    model.Add(too_large_raw == depth_pos - 20)
    too_large = model.NewIntVar(0, max_depth, f"{name}_too_large")  # type: ignore
    model.AddMaxEquality(too_large, [too_large_raw, 0])  # type: ignore

    small_raw = model.NewIntVar(-max_depth, max_depth, f"{name}_small_raw")  # type: ignore
    model.Add(small_raw == 5 - depth_pos)
    small_gap = model.NewIntVar(0, max_depth, f"{name}_small_gap")  # type: ignore
    model.AddMaxEquality(small_gap, [small_raw, 0])  # type: ignore

    too_small = model.NewIntVar(0, max_depth, f"{name}_too_small")  # type: ignore
    model.Add(too_small == small_gap).OnlyEnforceIf(recessed)
    model.Add(too_small == 0).OnlyEnforceIf(recessed.Not())

    penalty = model.NewIntVar(0, max_depth * 2, f"{name}_penalty")  # type: ignore
    model.Add(penalty == too_small + too_large)
    return penalty, recessed


def build_excess_count_penalty(
    model: Any,
    vars_to_count: list[cp_model.IntVar],
    max_allowed: int,
    name: str,
) -> cp_model.IntVar:
    if not vars_to_count:
        penalty = model.NewIntVar(0, 0, f"{name}_penalty")  # type: ignore
        model.Add(penalty == 0)
        return penalty

    count_var = model.NewIntVar(0, len(vars_to_count), f"{name}_count")  # type: ignore
    model.Add(count_var == cp_model.LinearExpr.Sum(vars_to_count))  # type: ignore

    raw_excess = model.NewIntVar(
        -len(vars_to_count), len(vars_to_count), f"{name}_raw_excess"
    )  # type: ignore
    model.Add(raw_excess == count_var - max_allowed)

    excess = model.NewIntVar(0, len(vars_to_count), f"{name}_excess")  # type: ignore
    model.AddMaxEquality(excess, [raw_excess, 0])  # type: ignore
    return excess
