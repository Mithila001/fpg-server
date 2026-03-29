from __future__ import annotations

from typing import Literal, TypedDict


class CoordinatePayload(TypedDict):
    x: float
    y: float


class RoadConnectedPayload(TypedDict, total=False):
    segment: list[CoordinatePayload]
    roadType: str


class LandBoundaryPayload(TypedDict, total=False):
    area: float
    segmentsCoordinates: list[CoordinatePayload]
    roadConnected: list[RoadConnectedPayload]


SegmentCategory = Literal["front", "back", "left", "right"]


class SegmentCategoryItem(TypedDict):
    index: int
    category: SegmentCategory


class SegmentOffsetItem(TypedDict):
    index: int
    offset: float


class UsableLandMetadata(TypedDict):
    segmentCategories: list[SegmentCategoryItem]
    segmentFinalOffsets: list[SegmentOffsetItem]


class UsableLandSpaceResult(TypedDict):
    shrunkSegmentsCoordinates: list[CoordinatePayload]
    metadata: UsableLandMetadata