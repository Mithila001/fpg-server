"""
Mock land data for development and testing.
Source: _Isolated_Prototype_Area/main.py — MOCK_LANDS
"""
from typing import Sequence

MOCK_LANDS: Sequence[dict] = [
    {
        "land_coordinates": [(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)],
        "setbacksValues": [1, 0.5, 0.5, 2],
    },
    {
        "land_coordinates": [(15.0, 1.5), (16.5, 9.0), (10.5, 12.3), (3.9, 10.2)],
        "setbacksValues": [10, 1.5, 2.0, 1.5],
    },
    {
        "land_coordinates": [(16.8, 0.9), (26.1, 12.0), (7.2, 12.0), (1.5, 9.0)],
        "setbacksValues": [1.8, 1.2, 1.8, 1.2],
    },
    {
        "land_coordinates": [(22.5, 11.1), (13.5, 18.0), (4.8, 18.0), (4.5, 0.9)],
        "setbacksValues": [2.0, 1.5, 2.0, 1.5],
    },
    {
        "land_coordinates": [(21.9, 12.0), (1.5, 12.0), (6.0, 0.9)],
        "setbacksValues": [1.5, 1.5, 1.5],
    },
    {
        "land_coordinates": [(21.0, 18.0), (9.0, 18.0), (6.0, 0.9)],
        "setbacksValues": [2.0, 1.5, 1.5],
    },
]
