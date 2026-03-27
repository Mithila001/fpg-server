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


class InternalDoorCandidate(TypedDict):
    room_a_name: str
    room_a_type: str
    room_b_name: str
    room_b_type: str
    side: str
    x1: float
    y1: float
    x2: float
    y2: float


class InternalDoorDecisionVars(TypedDict):
    selected: list[cp_model.IntVar]