from __future__ import annotations


def compute_zone(
    x: float,
    y: float,
    min_x: float,
    min_y: float,
    width: float,
    height: float,
) -> tuple[int, int]:
    cell_w = max(1e-6, width / 3.0)
    cell_h = max(1e-6, height / 3.0)

    zone_x = int((x - min_x) / cell_w) + 1
    zone_y = int((y - min_y) / cell_h) + 1

    zone_x = min(3, max(1, zone_x))
    zone_y = min(3, max(1, zone_y))
    return zone_x, zone_y


def is_in_zone_range(zone: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> bool:
    zone_x, zone_y = zone
    x1, y1 = start
    x2, y2 = end
    return x1 <= zone_x <= x2 and y1 <= zone_y <= y2
