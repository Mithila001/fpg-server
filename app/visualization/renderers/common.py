from __future__ import annotations

from collections.abc import Iterable

from ..backend import DrawingRenderer
from ..geometry import PointTuple, polygon_centroid
from ..models import PathOverlay, PointMarker, ZoneOverlay


def draw_zones(renderer: DrawingRenderer, zones: Iterable[ZoneOverlay]) -> None:
    for zone in zones:
        renderer.draw_polygon(
            zone.points,
            face_color=zone.face_color,
            edge_color=zone.edge_color,
            alpha=zone.alpha,
            line_width=zone.line_width,
            zorder=1.0,
        )
        if zone.label:
            renderer.draw_text(
                polygon_centroid(zone.points),
                zone.label,
                color=zone.edge_color,
                background_color="#ffffff",
                zorder=6.0,
            )


def draw_paths(renderer: DrawingRenderer, paths: Iterable[PathOverlay]) -> None:
    for path in paths:
        if len(path.points) < 2:
            continue

        if path.arrow_at_end and len(path.points) == 2:
            renderer.draw_arrow(
                path.points[0],
                path.points[1],
                color=path.color,
                line_width=path.line_width,
                zorder=3.0,
            )
        else:
            renderer.draw_polyline(
                path.points,
                color=path.color,
                line_width=path.line_width,
                dashed=path.dashed,
                zorder=3.0,
            )
            if path.arrow_at_end:
                renderer.draw_arrow(
                    path.points[-2],
                    path.points[-1],
                    color=path.color,
                    line_width=path.line_width,
                    zorder=3.1,
                )

        if path.label:
            renderer.draw_text(
                path.points[len(path.points) // 2],
                path.label,
                color=path.color,
                background_color="#ffffff",
                zorder=6.0,
            )


def draw_markers(
    renderer: DrawingRenderer,
    markers: Iterable[PointMarker],
    *,
    show_labels: bool,
    show_values: bool,
    default_color: str = "#7c3aed",
) -> None:
    for marker in markers:
        marker_color = marker.color or default_color
        if marker.radius_units is not None:
            renderer.draw_circle(
                marker.point,
                marker.radius_units,
                face_color=marker_color,
                edge_color="#111827",
                alpha=0.82,
                line_width=0.8,
                zorder=4.0,
            )
        else:
            renderer.draw_points(
                [marker.point],
                color=marker_color,
                size=marker.size,
                zorder=4.0,
            )

        label = _marker_label(marker, show_labels=show_labels, show_values=show_values)
        if label:
            renderer.draw_text(
                marker.point,
                label,
                color="#111827",
                font_size=8.0,
                vertical_alignment="bottom",
                background_color="#ffffff",
                zorder=6.0,
            )


def marker_points(markers: Iterable[PointMarker]) -> list[PointTuple]:
    return [marker.point for marker in markers]


def _marker_label(
    marker: PointMarker,
    *,
    show_labels: bool,
    show_values: bool,
) -> str | None:
    parts: list[str] = []
    if show_labels and marker.label:
        parts.append(marker.label)
    if show_values and marker.value is not None:
        parts.append(f"{marker.value:.2f}")
    return "\n".join(parts) if parts else None
