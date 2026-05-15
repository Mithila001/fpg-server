from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from app.algorithms.types.domain import ProcessedRoomData
from app.core.fpg_opening_config import normalize_room_type

MIN_HALLWAY_OVERLAPPING_LENGTH = 10.0


@dataclass(frozen=True)
class _HallwayEntry:
	index: int
	room: ProcessedRoomData
	polygon: Polygon | None


def _room_polygon(room: ProcessedRoomData) -> Polygon | None:
	if len(room.vertices) < 3:
		return None
	try:
		polygon = Polygon(room.vertices)
	except ValueError:
		return None
	if polygon.is_empty:
		return None
	if not polygon.is_valid:
		polygon = polygon.buffer(0)
		if polygon.is_empty or not polygon.is_valid:
			return None
	return polygon


def _shared_wall_length(poly_a: Polygon, poly_b: Polygon) -> float:
	intersection = poly_a.boundary.intersection(poly_b.boundary)
	if intersection.is_empty:
		return 0.0
	return float(intersection.length)


def _extract_polygon(geometry) -> Polygon | None:
	if isinstance(geometry, Polygon):
		return geometry
	if isinstance(geometry, MultiPolygon):
		polygons = list(geometry.geoms)
	elif hasattr(geometry, "geoms"):
		polygons = [geom for geom in geometry.geoms if isinstance(geom, Polygon)]
	else:
		polygons = []
	if not polygons:
		return None
	return max(polygons, key=lambda poly: poly.area)


def _polygon_vertices(polygon: Polygon) -> list[tuple[float, float]]:
	return [(float(x), float(y)) for (x, y) in polygon.exterior.coords]


class _DisjointSet:
	def __init__(self, items: Iterable[int]) -> None:
		self._parent = {item: item for item in items}

	def find(self, item: int) -> int:
		parent = self._parent[item]
		if parent != item:
			self._parent[item] = self.find(parent)
		return self._parent[item]

	def union(self, a: int, b: int) -> None:
		root_a = self.find(a)
		root_b = self.find(b)
		if root_a != root_b:
			self._parent[root_b] = root_a


def hallway_union(
	floor_plan: list[ProcessedRoomData],
	*,
	min_overlap_length: float = MIN_HALLWAY_OVERLAPPING_LENGTH,
	tolerance: float = 1e-6,
) -> list[ProcessedRoomData]:
	"""Merge hallway rooms that share a long-enough overlapping wall."""
	if not floor_plan:
		return []

	hallway_entries: list[_HallwayEntry] = []
	for index, room in enumerate(floor_plan):
		if normalize_room_type(str(room.type)) != "hallway":
			continue
		hallway_entries.append(
			_HallwayEntry(index=index, room=room, polygon=_room_polygon(room))
		)

	if len(hallway_entries) < 2:
		return floor_plan

	hallway_indices = [entry.index for entry in hallway_entries]
	ds = _DisjointSet(hallway_indices)
	entry_by_index = {entry.index: entry for entry in hallway_entries}

	for i, entry_a in enumerate(hallway_entries):
		if entry_a.polygon is None:
			continue
		for entry_b in hallway_entries[i + 1 :]:
			if entry_b.polygon is None:
				continue
			overlap = _shared_wall_length(entry_a.polygon, entry_b.polygon)
			if overlap + tolerance >= min_overlap_length:
				ds.union(entry_a.index, entry_b.index)

	components: dict[int, list[_HallwayEntry]] = {}
	for entry in hallway_entries:
		root = ds.find(entry.index)
		components.setdefault(root, []).append(entry)

	merged_by_root: dict[int, ProcessedRoomData] = {}
	for root, entries in components.items():
		if len(entries) < 2:
			continue
		polygons = [entry.polygon for entry in entries if entry.polygon is not None]
		if len(polygons) < 2:
			continue
		merged_geometry = unary_union(polygons)
		merged_polygon = _extract_polygon(merged_geometry)
		if merged_polygon is None:
			continue
		merged_vertices = _polygon_vertices(merged_polygon)
		merged_by_root[root] = ProcessedRoomData(
			type="hallway",
			name=f"hallway_union_{root}",
			original_index=min(entry.room.original_index for entry in entries),
			vertices=merged_vertices,
			area=float(merged_polygon.area),
		)

	merged_roots_used: set[int] = set()
	result: list[ProcessedRoomData] = []
	for index, room in enumerate(floor_plan):
		entry = entry_by_index.get(index)
		if entry is None:
			result.append(room)
			continue

		root = ds.find(index)
		merged_room = merged_by_root.get(root)
		if merged_room is None:
			result.append(room)
			continue

		if root in merged_roots_used:
			continue

		merged_roots_used.add(root)
		result.append(merged_room)

	return result
