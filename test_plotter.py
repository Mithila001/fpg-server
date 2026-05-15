import os
import sys

# Add the project root to sys.path
sys.path.insert(0, r"f:\OnGoinProject\House Plane Generator Projects\fpg-server")

from app.algorithms.fpg_optuna_score.score.spatial_coverage import score_spatial_coverage
from app.algorithms.fpg_optuna_score.util.scoring_common import OptunaScorePoint
from app.algorithms.types.domain import FpgRequirements, ConfigData

# Dummy config and requirements
config = ConfigData(floor_plan_width=20.0, floor_plan_height=15.0, min_coverage=0.5, max_aspect_ratio=2.0, min_aspect_ratio=0.5)
requirements = FpgRequirements(config=config, rooms=[])

# Dummy points
points = [
    OptunaScorePoint(x=5.0, y=5.0, name="Room 1", room_type="bedroom"),
    OptunaScorePoint(x=15.0, y=10.0, name="Room 2", room_type="living"),
]

score = score_spatial_coverage(requirements, points)
print("Score:", score)
