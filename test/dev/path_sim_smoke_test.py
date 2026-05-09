"""Smoke test for path simulation pipeline."""

import sys

sys.path.insert(0, ".")

from dataclasses import dataclass, field
from typing import List, Tuple, Any


# --- Minimal synthetic floor plan ---
@dataclass
class FakeRoom:
    name: str
    type: str
    vertices: List[Tuple[float, float]]
    area: float = 0.0
    original_index: int = 0


@dataclass
class FakeOpening:
    room_name: str
    room_type: str
    opening_type: str
    x1: float
    y1: float
    x2: float
    y2: float
    connected_room_name: str
    connected_room_type: str
    side: str = ""


@dataclass
class FakeFPO:
    floor_plan: List[Any]
    openings: List[Any]


# Layout (all cm):
#   veranda      (0–200  x 0–150)
#   livingRoom   (0–500  x 150–500)
#   hallway      (500–600 x 0–500)
#   bedroom      (600–900 x 0–300)
#   bathroom     (600–900 x 300–500)
#   kitchen      (0–500  x 500–700)
rooms = [
    FakeRoom(
        "veranda", "verandaOutdoorSpace", [(0, 0), (200, 0), (200, 150), (0, 150)]
    ),
    FakeRoom("living", "livingRoom", [(0, 150), (500, 150), (500, 500), (0, 500)]),
    FakeRoom("hallway1", "hallway", [(500, 0), (600, 0), (600, 500), (500, 500)]),
    FakeRoom("bed1", "bedroom", [(600, 0), (900, 0), (900, 300), (600, 300)]),
    FakeRoom("bath1", "bathroom", [(600, 300), (900, 300), (900, 500), (600, 500)]),
    FakeRoom("kitchen1", "kitchen", [(0, 500), (500, 500), (500, 700), (0, 700)]),
]

openings = [
    # Front door: living <-> veranda (shared wall at y=150)
    FakeOpening(
        "living",
        "livingRoom",
        "door",
        50,
        150,
        130,
        150,
        "veranda",
        "verandaOutdoorSpace",
    ),
    # Living -> hallway (shared wall at x=500)
    FakeOpening(
        "living", "livingRoom", "door", 500, 250, 500, 350, "hallway1", "hallway"
    ),
    # Hallway -> bedroom
    FakeOpening("hallway1", "hallway", "door", 600, 80, 600, 180, "bed1", "bedroom"),
    # Hallway -> bathroom
    FakeOpening("hallway1", "hallway", "door", 600, 350, 600, 430, "bath1", "bathroom"),
    # Living -> kitchen
    FakeOpening(
        "living", "livingRoom", "door", 80, 500, 200, 500, "kitchen1", "kitchen"
    ),
    # Bedroom -> bathroom
    FakeOpening("bed1", "bedroom", "door", 680, 300, 800, 300, "bath1", "bathroom"),
]

fpo = FakeFPO(floor_plan=rooms, openings=openings)

from app.algorithms.fgp_score.score_functional.path_simulations import (
    run_path_simulation,
)

result = run_path_simulation(fpo)

print("=" * 60)
print(f"total_score          : {result.total_score}")
print(f"circulation_efficiency: {result.circulation_efficiency}")
print(f"privacy_score        : {result.privacy_score}")
print(f"hallway_utility      : {result.hallway_utility}")
print(f"furniture_flexibility: {result.furniture_flexibility}")
print(f"paths simulated      : {len(result.paths)}")
print(
    f"plot_path            : {result.plot_path if result.plot_path else '(score below margin – plot skipped)'}"
)
print(f"error                : {result.error if result.error else 'none'}")
print("=" * 60)
