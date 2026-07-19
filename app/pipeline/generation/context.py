from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app.algorithms.floor_plan_preprocessing import (
    PreprocessingReferenceData,
    ReferenceDataError,
    RoomRelationReference,
    RoomSizeReference,
)
from app.algorithms.floor_plan_scoring import FloorPlanScoringResult
from app.algorithms.types_new import FloorPlan, RoomType


class GenerationStage(str, Enum):
    PREPROCESSING = "preprocessing"
    CANDIDATE_SEARCH = "candidate_search"
    SOLVER = "solver"
    POST_PROCESSING = "post_processing"
    OPENINGS = "openings"
    SCORING = "scoring"


@dataclass(frozen=True, slots=True)
class RequestedGenerationRoom:
    room_type: RoomType | str
    id: str | None = None
    name: str | None = None
    requested_size: str | None = "regular"
    required: bool = True


@dataclass(frozen=True, slots=True)
class GenerationPipelineRequest:
    request_id: str
    max_width: float
    max_height: float
    aspect_ratio: float | str
    rooms: tuple[RequestedGenerationRoom, ...]


@dataclass(frozen=True, slots=True)
class GenerationPipelineSettings:
    candidate_trial_count: int = 20
    candidate_grid_resolution: float = 1.0
    candidate_random_seed: int | None = None


@dataclass(frozen=True, slots=True)
class GenerationPipelineResult:
    floor_plan: FloorPlan
    scoring: FloorPlanScoringResult


class GenerationPipelineError(Exception):
    def __init__(
        self,
        stage: GenerationStage,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message
        self.details = MappingProxyType(dict(details or {}))


REFERENCE_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "generation_reference_data.json"
)


def load_generation_reference_data(
    path: Path = REFERENCE_DATA_PATH,
) -> PreprocessingReferenceData:
    """Load the pipeline's packaged, source-neutral preprocessing references."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        room_sizes = tuple(
            RoomSizeReference(**item) for item in payload["room_sizes"]
        )
        room_relations = tuple(
            RoomRelationReference(
                **{
                    **item,
                    "target_room_types": tuple(item["target_room_types"]),
                }
            )
            for item in payload.get("room_relations", ())
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ReferenceDataError(
            f"Could not load generation reference data from '{path}': {exc}"
        ) from exc

    return PreprocessingReferenceData(
        room_sizes=room_sizes,
        room_relations=room_relations,
    )
