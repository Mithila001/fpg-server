from __future__ import annotations

import math
from typing import Any, Mapping

from ..context import ScoringContext
from ..types import (
    EvaluationStatus,
    EvaluatorKey,
    EvaluatorResult,
    FindingSeverity,
    ScoreFinding,
)
from .base import CandidateEvaluator
from .common import build_evaluation_data, clamp_score, setting_float, setting_mapping

ZONE_SUITABILITY_KEY = EvaluatorKey("zone_suitability")

DEFAULT_VALID_ZONES: Mapping[str, tuple[tuple[int, int], ...]] = {
    "veranda": ((1, 1), (2, 1), (3, 1)),
    "garage": ((1, 1), (3, 1)),
    "kitchen": ((1, 1), (2, 1), (3, 1), (1, 2), (3, 2), (1, 3), (2, 3), (3, 3)),
    "hallway": ((1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (3, 3)),
    "living_room": ((1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2)),
    "bathroom": ((1, 1), (2, 1), (3, 1), (1, 2), (3, 2), (1, 3), (2, 3), (3, 3)),
}


class ZoneSuitabilityEvaluator(CandidateEvaluator):
    """Scores whether selected room types occupy preferred floor regions."""

    @property
    def key(self) -> EvaluatorKey:
        return ZONE_SUITABILITY_KEY

    def evaluate(
        self,
        context: ScoringContext,
        settings: Mapping[str, Any],
    ) -> EvaluatorResult:
        data = build_evaluation_data(context)
        grid_size = int(settings.get("grid_size", 3))
        if grid_size <= 0:
            raise ValueError("grid_size must be positive.")
        falloff_multiplier = setting_float(settings, "falloff_multiplier", 1.5)
        configured_zones = setting_mapping(settings, "valid_zones", DEFAULT_VALID_ZONES)
        valid_zones = {
            str(room_type): {tuple(map(int, cell)) for cell in cells}
            for room_type, cells in configured_zones.items()
        }

        scores: list[float] = []
        findings: list[ScoreFinding] = []
        metrics: dict[str, float] = {}

        for point in data.points:
            cells = valid_zones.get(point.room_type)
            if not cells:
                continue
            nx = point.x / data.floor_width
            ny = point.y / data.floor_height
            distance_to_zone = _minimum_distance_to_cells(nx, ny, cells, grid_size)
            score = clamp_score(100.0 * (1.0 - distance_to_zone * falloff_multiplier))
            scores.append(score)
            metrics[f"room.{point.room_id}.score"] = score
            metrics[f"room.{point.room_id}.distance_to_zone"] = distance_to_zone
            if score < 100.0:
                findings.append(
                    ScoreFinding(
                        code="ROOM_OUTSIDE_PREFERRED_ZONE",
                        message=(
                            f"Room '{point.name}' is outside its preferred zone "
                            f"by {distance_to_zone:.3f} normalized units."
                        ),
                        severity=FindingSeverity.WARNING,
                        subject_ids=(point.room_id,),
                    )
                )

        if not scores:
            return EvaluatorResult(
                evaluator_key=self.key,
                status=EvaluationStatus.NOT_APPLICABLE,
                score=None,
                findings=(
                    ScoreFinding(
                        code="NO_ZONE_SCORABLE_ROOMS",
                        message="No candidate rooms use configured zone rules.",
                    ),
                ),
            )

        final_score = sum(scores) / len(scores)
        metrics["scored_room_count"] = float(len(scores))
        return EvaluatorResult(
            evaluator_key=self.key,
            status=EvaluationStatus.COMPLETED,
            score=clamp_score(final_score),
            findings=tuple(findings),
            metrics=metrics,
        )


def _minimum_distance_to_cells(
    nx: float,
    ny: float,
    cells: set[tuple[int, int]],
    grid_size: int,
) -> float:
    minimum = math.inf
    for cell_x, cell_y in cells:
        xmin = (cell_x - 1) / grid_size
        xmax = cell_x / grid_size
        ymin = (cell_y - 1) / grid_size
        ymax = cell_y / grid_size
        dx = max(0.0, xmin - nx, nx - xmax)
        dy = max(0.0, ymin - ny, ny - ymax)
        minimum = min(minimum, math.hypot(dx, dy))
    return minimum
