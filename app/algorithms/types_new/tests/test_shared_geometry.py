from app.algorithms.types_new import Point, Polygon
from app.algorithms.types_new.floor_plan import Point as FloorPlanPoint
from app.algorithms.types_new.floor_plan import Polygon as FloorPlanPolygon


def test_floor_plan_reexports_shared_geometry_identity() -> None:
    assert FloorPlanPoint is Point
    assert FloorPlanPolygon is Polygon
