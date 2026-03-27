from __future__ import annotations

from typing import TypedDict

from ortools.sat.python import cp_model


class ScaledRoomBounds(TypedDict):
    x: int
    y: int
    x_end: int
    y_end: int


class MainDoorCpSatVariables(TypedDict):
    x1: cp_model.IntVar
    y1: cp_model.IntVar
    x2: cp_model.IntVar
    y2: cp_model.IntVar
    side_selected: dict[str, cp_model.IntVar]