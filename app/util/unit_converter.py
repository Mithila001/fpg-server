from __future__ import annotations

from typing import Any


CM_PER_METER = 100.0
# Internal solver unit scale in centimeters. 1 unit == 1 centimeter.
SERVER_UNIT_IN_CM = 1.0

_LINEAR_KEYS = {
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "x_end",
    "y_end",
    "width",
    "height",
    "floor_width",
    "floor_height",
    "min_width",
    "min_height",
}

_AREA_KEYS = {
    "area",
    "min_area",
    "max_area",
    "floor_area",
    "total_area",
}


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _convert_payload(data: Any, linear_factor: float, area_factor: float, key: str | None = None) -> Any:
    if isinstance(data, dict):
        return {
            item_key: _convert_payload(
                item_value,
                linear_factor=linear_factor,
                area_factor=area_factor,
                key=item_key,
            )
            for item_key, item_value in data.items()
        }

    if isinstance(data, list):
        return [
            _convert_payload(
                item,
                linear_factor=linear_factor,
                area_factor=area_factor,
                key=key,
            )
            for item in data
        ]

    if _is_numeric(data):
        if key in _AREA_KEYS:
            return float(data) * area_factor
        if key in _LINEAR_KEYS:
            return float(data) * linear_factor

    return data


def converter_cm_to_unit(data: Any) -> Any:
    """Convert incoming centimeter-based payload values into internal solver units."""
    linear_factor = 1.0 / SERVER_UNIT_IN_CM
    area_factor = linear_factor * linear_factor
    return _convert_payload(data, linear_factor=linear_factor, area_factor=area_factor)


def converter_unit_to_centimeters(data: Any) -> Any:
    """Convert internal solver-unit payload values into centimeter-based API values."""
    linear_factor = 1.0
    area_factor = 1.0
    return _convert_payload(data, linear_factor=linear_factor, area_factor=area_factor)


def converter_unit_to_meters(data: Any) -> Any:
    """Convert internal solver-unit payload values into meter-based API values."""
    linear_factor = SERVER_UNIT_IN_CM / CM_PER_METER
    area_factor = linear_factor * linear_factor
    return _convert_payload(data, linear_factor=linear_factor, area_factor=area_factor)
