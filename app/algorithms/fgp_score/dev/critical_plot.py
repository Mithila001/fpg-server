from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Sequence

import matplotlib

# Force headless backend so no UI is displayed.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from app.algorithms.fgp_score.score_critical.adjacency_relations import (
	validate_adjacency_relations,
)
from app.algorithms.fgp_score.score_critical.empty_space import validate_empty_space
from app.algorithms.fgp_score.score_critical.inward_pocket import (
	detect_inward_pocket_violation_v2,
)
from app.algorithms.types.domain import ProcessedRoomData
from app.core.fpg_rooms.config_score import SCORE_VALIDATION_MIN_OVERLAP


def _default_output_dir() -> str:
	return os.path.abspath(
		os.path.join(
			os.path.dirname(__file__),
			"..",
			"..",
			"..",
			"..",
			"test",
			"outputs",
			"score",
			"critical_score",
		)
	)


def _iter_polygons(geom: Any) -> list[Polygon]:
	if geom is None or getattr(geom, "is_empty", True):
		return []
	if isinstance(geom, Polygon):
		return [geom]
	if isinstance(geom, MultiPolygon):
		return list(geom.geoms)

	polygons: list[Polygon] = []
	for candidate in getattr(geom, "geoms", []):
		if isinstance(candidate, Polygon):
			polygons.append(candidate)
	return polygons


def _room_polygons(scoring_plan: Sequence[ProcessedRoomData]) -> list[tuple[ProcessedRoomData, Polygon]]:
	polygons: list[tuple[ProcessedRoomData, Polygon]] = []
	for room in scoring_plan:
		if not room.vertices or len(room.vertices) < 3:
			continue
		poly = Polygon(room.vertices)
		if poly.is_empty:
			continue
		polygons.append((room, poly))
	return polygons


def _configure_axes(ax: Any, room_poly_pairs: list[tuple[ProcessedRoomData, Polygon]]) -> None:
	all_x: list[float] = []
	all_y: list[float] = []

	for _room, poly in room_poly_pairs:
		min_x, min_y, max_x, max_y = poly.bounds
		all_x.extend([float(min_x), float(max_x)])
		all_y.extend([float(min_y), float(max_y)])

	if not all_x or not all_y:
		ax.set_xlim(0, 1)
		ax.set_ylim(0, 1)
	else:
		min_x = min(all_x)
		max_x = max(all_x)
		min_y = min(all_y)
		max_y = max(all_y)
		pad = max(2.0, 0.05 * max(max_x - min_x, max_y - min_y, 1.0))
		ax.set_xlim(min_x - pad, max_x + pad)
		ax.set_ylim(min_y - pad, max_y + pad)

	ax.set_aspect("equal", adjustable="box")
	ax.grid(True, linestyle=":", alpha=0.3)


def _draw_rooms(ax: Any, room_poly_pairs: list[tuple[ProcessedRoomData, Polygon]]) -> None:
	palette = {
		"bedroom": "#9ecae1",
		"bathroom": "#6baed6",
		"attachedBathroom": "#4292c6",
		"kitchen": "#a1d99b",
		"diningRoom": "#fdd0a2",
		"livingRoom": "#fdae6b",
		"garage": "#bdbdbd",
		"hallway": "#d4b9da",
		"veranda": "#c7e9c0",
	}
	for room, poly in room_poly_pairs:
		color = palette.get(str(room.type), "#c7c7c7")
		patch = MplPolygon(
			list(poly.exterior.coords),
			closed=True,
			facecolor=color,
			edgecolor="#2b2b2b",
			linewidth=1.0,
			alpha=0.65,
		)
		ax.add_patch(patch)

		c = poly.centroid
		ax.text(
			float(c.x),
			float(c.y),
			str(room.name),
			ha="center",
			va="center",
			fontsize=7,
			color="#111111",
		)


def _add_summary(ax: Any, passed: bool, lines: list[str]) -> None:
	status_text = "PASS" if passed else "FAIL"
	status_color = "#2e7d32" if passed else "#c62828"
	payload = "\n".join([f"status: {status_text}"] + lines)
	ax.text(
		0.02,
		0.98,
		payload,
		transform=ax.transAxes,
		va="top",
		ha="left",
		fontsize=8,
		color=status_color,
		bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": status_color},
	)


def save_critical_score_plot(
	scoring_plan: Sequence[ProcessedRoomData],
	relation_constraints: Sequence[Any],
	floor_width: float,
	floor_height: float,
	inward_pocket_max_length: float,
	*,
	min_overlap: int = SCORE_VALIDATION_MIN_OVERLAP,
	tolerance: float = 1e-6,
	output_dir: str | None = None,
) -> str:
	"""Save a 3-panel critical score debug plot and return output path."""
	output_dir = output_dir or _default_output_dir()
	os.makedirs(output_dir, exist_ok=True)

	room_poly_pairs = _room_polygons(scoring_plan)
	room_polygons = [poly for _room, poly in room_poly_pairs]

	adjacency_violations = validate_adjacency_relations(
		scoring_plan,
		relation_constraints,
		min_overlap=int(min_overlap),
		tolerance=tolerance,
	)
	adjacency_passed = len(adjacency_violations) == 0

	empty_violations, empty_diag = validate_empty_space(
		scoring_plan,
		floor_width,
		floor_height,
		tolerance=tolerance,
	)
	empty_passed = len(empty_violations) == 0

	inward_violation, inward_diag = detect_inward_pocket_violation_v2(
		scoring_plan,
		max_inward_length=inward_pocket_max_length,
		tolerance=tolerance,
	)
	inward_passed = not inward_violation

	checks_passed = int(adjacency_passed) + int(empty_passed) + int(inward_passed)
	critical_score = (25.0 * checks_passed / 3.0)

	fig, axes = plt.subplots(1, 3, figsize=(24, 8), dpi=180, facecolor="#fafafa")
	ax_adj, ax_empty, ax_inward = axes

	# Panel 1: adjacency check status.
	_draw_rooms(ax_adj, room_poly_pairs)
	_configure_axes(ax_adj, room_poly_pairs)
	ax_adj.set_title("critical: adjacency")
	adj_lines = [
		f"violations: {len(adjacency_violations)}",
		(
			f"first: {adjacency_violations[0][:120]}"
			if adjacency_violations
			else "first: none"
		),
	]
	_add_summary(ax_adj, adjacency_passed, adj_lines)

	# Panel 2: empty-space check with air-gap overlays.
	_draw_rooms(ax_empty, room_poly_pairs)
	_configure_axes(ax_empty, room_poly_pairs)
	ax_empty.set_title("critical: empty_space")
	if room_polygons:
		union_shape = unary_union(room_polygons)
		boundary_shape = (
			Polygon(union_shape.exterior)
			if isinstance(union_shape, Polygon)
			else MultiPolygon([Polygon(poly.exterior) for poly in _iter_polygons(union_shape)])
		)
		air_gaps = boundary_shape.difference(union_shape)
		for gap in _iter_polygons(air_gaps):
			ax_empty.add_patch(
				MplPolygon(
					list(gap.exterior.coords),
					closed=True,
					facecolor="#ef5350",
					edgecolor="#b71c1c",
					alpha=0.5,
				)
			)
	empty_lines = [
		f"air_gap_area: {float(empty_diag.get('air_gap_area', 0.0)):.2f}",
		f"union_area: {float(empty_diag.get('union_area', 0.0)):.2f}",
		f"violations: {len(empty_violations)}",
	]
	_add_summary(ax_empty, empty_passed, empty_lines)

	# Panel 3: inward-pocket check with hull/pockets/violating segments.
	_draw_rooms(ax_inward, room_poly_pairs)
	_configure_axes(ax_inward, room_poly_pairs)
	ax_inward.set_title("critical: inward_pocket")
	if room_polygons:
		union_shape = unary_union(room_polygons)
		hull = union_shape.convex_hull
		if isinstance(hull, Polygon):
			hx, hy = hull.exterior.xy
			ax_inward.plot(hx, hy, linestyle="--", color="#4f4f4f", linewidth=1.5)

		pockets = hull.difference(union_shape)
		for pocket in _iter_polygons(pockets):
			ax_inward.add_patch(
				MplPolygon(
					list(pocket.exterior.coords),
					closed=True,
					facecolor="#ffd54f",
					edgecolor="#ef6c00",
					alpha=0.35,
				)
			)

		for segment in inward_diag.get("violating_segments", []):
			x1 = float(segment.get("x1", 0.0))
			y1 = float(segment.get("y1", 0.0))
			x2 = float(segment.get("x2", 0.0))
			y2 = float(segment.get("y2", 0.0))
			ax_inward.plot([x1, x2], [y1, y2], color="#d32f2f", linewidth=2.5)

	inward_lines = [
		f"max_delta: {float(inward_diag.get('max_inward_segment_length', 0.0)):.2f}",
		f"threshold: {float(inward_diag.get('threshold', inward_pocket_max_length)):.2f}",
		f"violating_segments: {len(inward_diag.get('violating_segments', []))}",
	]
	_add_summary(ax_inward, inward_passed, inward_lines)

	fig.suptitle(
		"fgp critical score debug | "
		f"passed={checks_passed}/3 | score={critical_score:.2f}/25",
		fontsize=13,
	)

	timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
	filename = f"critical_score_{timestamp}_{uuid.uuid4().hex[:8]}.png"
	save_path = os.path.join(output_dir, filename)

	fig.tight_layout(rect=[0.0, 0.02, 1.0, 0.95])
	fig.savefig(save_path, dpi=220)
	plt.close(fig)

	return save_path
