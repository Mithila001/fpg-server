from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from app.core.fpg_rooms.config_fpg import (
    OPTUNA_NODE_PLACEMENT_FRONT,
    OPTUNA_NODE_PLACEMENT_PRIVATE,
)
from app.core.fpg_rooms.config_optuna import (
    OPTUNA_ROOM_BACK_BAND_DEPTH,
    OPTUNA_ROOM_PROXIMITY_SLACK,
)


@dataclass(frozen=True, slots=True)
class RoomSamplingContext:
    room_id: str
    room_name: str
    room_type: str
    radius: float
    floor_width: float
    floor_height: float


SampledRoomPosition = dict[str, float | str]


@dataclass(frozen=True, slots=True)
class RoomSamplingPolicy:
    front_room_types: tuple[str, ...] = tuple(OPTUNA_NODE_PLACEMENT_FRONT)
    private_room_types: tuple[str, ...] = tuple(OPTUNA_NODE_PLACEMENT_PRIVATE)
    back_room_types: frozenset[str] = frozenset({"kitchen", "bathroom"})
    proximity_pairs: tuple[tuple[str, str], ...] = (
        ("livingRoom", "veranda"),
        ("kitchen", "diningRoom"),
        ("diningRoom", "kitchen"),
    )
    back_band_depth: float = OPTUNA_ROOM_BACK_BAND_DEPTH
    proximity_slack: float = OPTUNA_ROOM_PROXIMITY_SLACK

    def sort_nodes_for_sampling(self, nodes: list[Any]) -> list[Any]:
        priority_map = {
            "veranda": 0,
            "garage": 0,
            "livingRoom": 1,
            "diningRoom": 2,
            "kitchen": 3,
            "bathroom": 4,
        }

        return sorted(
            nodes,
            key=lambda node: (
                priority_map.get(getattr(node, "room_type", ""), 3),
                getattr(node, "id", ""),
            ),
        )

    def get_y_bounds(
        self,
        context: RoomSamplingContext,
        sampled_positions: Mapping[str, SampledRoomPosition],
    ) -> tuple[float, float]:
        min_y = max(0.0, float(context.radius))
        max_y = max(min_y, float(context.floor_height) - float(context.radius))

        room_type = context.room_type.strip()

        base_window: tuple[float, float] = (min_y, max_y)
        zone_window = self._zone_half_bounds(
            room_type=room_type,
            min_y=min_y,
            max_y=max_y,
        )
        if zone_window is not None:
            intersected = self._intersect_bounds(base_window, zone_window)
            if intersected is not None:
                base_window = intersected

        if room_type in self.front_room_types:
            low, high = base_window
            return self._sanitize_bounds(low, high, min_y=min_y, max_y=max_y)

        if room_type in self.back_room_types:
            back_high = max_y
            back_low = max(
                min_y, back_high - max(float(context.radius), self.back_band_depth)
            )
            anchored_bounds = self._bounds_from_related_rooms(
                context, sampled_positions
            )
            if anchored_bounds is None:
                intersected = self._intersect_bounds((back_low, back_high), base_window)
                if intersected is None:
                    low, high = base_window
                    return self._sanitize_bounds(low, high, min_y=min_y, max_y=max_y)
                low, high = intersected
                return self._sanitize_bounds(
                    low,
                    high,
                    min_y=min_y,
                    max_y=max_y,
                )

            low, high = anchored_bounds
            intersect_low = max(back_low, low)
            intersect_high = min(back_high, high)
            intersected = self._intersect_bounds(
                (intersect_low, intersect_high),
                base_window,
            )
            if intersected is not None:
                low, high = intersected
                return self._sanitize_bounds(
                    low,
                    high,
                    min_y=min_y,
                    max_y=max_y,
                )

            if intersect_low <= intersect_high:
                return self._sanitize_bounds(
                    intersect_low,
                    intersect_high,
                    min_y=min_y,
                    max_y=max_y,
                )

            # If back-band and proximity do not overlap, preserve hard back rule.
            intersected = self._intersect_bounds((back_low, back_high), base_window)
            if intersected is None:
                low, high = base_window
                return self._sanitize_bounds(low, high, min_y=min_y, max_y=max_y)
            low, high = intersected
            return self._sanitize_bounds(
                low,
                high,
                min_y=min_y,
                max_y=max_y,
            )

        anchored_bounds = self._bounds_from_related_rooms(context, sampled_positions)
        if anchored_bounds is not None:
            low, high = anchored_bounds
            intersected = self._intersect_bounds((low, high), base_window)
            if intersected is not None:
                low, high = intersected
            else:
                low, high = base_window
            return self._sanitize_bounds(low, high, min_y=min_y, max_y=max_y)

        low, high = base_window
        return self._sanitize_bounds(low, high, min_y=min_y, max_y=max_y)

    def _zone_half_bounds(
        self,
        *,
        room_type: str,
        min_y: float,
        max_y: float,
    ) -> tuple[float, float] | None:
        midpoint = (float(min_y) + float(max_y)) / 2.0

        # Front rule has precedence when room type belongs to multiple groups.
        if room_type in self.front_room_types:
            return min_y, midpoint
        if room_type in self.private_room_types:
            return midpoint, max_y
        return None

    def _intersect_bounds(
        self,
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> tuple[float, float] | None:
        low = max(float(first[0]), float(second[0]))
        high = min(float(first[1]), float(second[1]))
        if low <= high:
            return low, high
        return None

    def _sanitize_bounds(
        self,
        low: float,
        high: float,
        *,
        min_y: float,
        max_y: float,
    ) -> tuple[float, float]:
        low_val = float(low)
        high_val = float(high)

        if not math.isfinite(low_val) or not math.isfinite(high_val):
            return min_y, max_y

        low_val = max(min_y, low_val)
        high_val = min(max_y, high_val)
        if low_val <= high_val:
            return low_val, high_val

        # Deterministic clamp for inverted windows.
        return min_y, max_y

    def _bounds_from_related_rooms(
        self,
        context: RoomSamplingContext,
        sampled_positions: Mapping[str, SampledRoomPosition],
    ) -> tuple[float, float] | None:
        related_types = {b for a, b in self.proximity_pairs if a == context.room_type}
        if not related_types:
            return None

        related_rooms = [
            position
            for position in sampled_positions.values()
            if str(position.get("type", "")).strip() in related_types
        ]
        if not related_rooms:
            return None

        candidate_bounds: list[tuple[float, float]] = []
        for related in related_rooms:
            related_y = float(related.get("y", 0.0))
            related_radius = float(related.get("radius", 0.0))
            span = related_radius + context.radius + self.proximity_slack
            candidate_bounds.append((related_y - span, related_y + span))

        low = min(bound[0] for bound in candidate_bounds)
        high = max(bound[1] for bound in candidate_bounds)
        return low, high


def sort_nodes_for_sampling(nodes: list[Any]) -> list[Any]:
    return RoomSamplingPolicy().sort_nodes_for_sampling(nodes)
