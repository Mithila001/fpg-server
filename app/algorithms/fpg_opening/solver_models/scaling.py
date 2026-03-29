from __future__ import annotations


OPENING_SCALE = 1


def to_scaled_int(value: float, scale: int = OPENING_SCALE) -> int:
    return int(round(value * scale))


def from_scaled_int(value: int, scale: int = OPENING_SCALE) -> float:
    return value / float(scale)