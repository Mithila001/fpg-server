"""Centralized configuration for path simulation.

All configuration constants and parameters related to path simulation
are maintained here to ensure a clear, organized structure.

No imports from outside this package.
"""

from __future__ import annotations

from typing import Dict

# ============================================================================
# GRID & RASTERIZATION
# ============================================================================

# Grid resolution in centimeters
# 15cm balances detail (for accurate room-by-room tracking) vs. speed
GRID_RESOLUTION_CM: float = 15.0

# ============================================================================
# SCORING CONFIGURATION
# ============================================================================

# Score margin threshold - plot is generated only when total_score exceeds this
PATH_SCORE_PLOT_SCORE_MARGIN: float = 40.0

# Target quiet zone fraction for furniture flexibility scoring
# We aim for ~35% of living/bedroom area to be traffic-free
TARGET_QUIET_FRACTION: float = 0.35

# Privacy zone buffer around bedroom doors (in cm)
# Any public path within this distance of a bedroom door is considered a breach
PRIVACY_RADIUS_CM: float = 150.0

# ============================================================================
# SCORING WEIGHTS
# ============================================================================
# Each metric is scored 0-100 independently, then weighted to contribute
# to the final 0-100 total score. Weights sum to 1.0.

SCORE_WEIGHTS: Dict[str, float] = {
    "circulation_efficiency": 0.30,  # 30% weight
    "privacy_score": 0.25,  # 25% weight
    "hallway_utility": 0.25,  # 25% weight
    "furniture_flexibility": 0.20,  # 20% weight
}

# Raw score ranges (0-100) for each metric before weighting
SCORE_RANGES: Dict[str, tuple[float, float]] = {
    "circulation_efficiency": (0.0, 100.0),
    "privacy_score": (0.0, 100.0),
    "hallway_utility": (0.0, 100.0),
    "furniture_flexibility": (0.0, 100.0),
}

# ============================================================================
# PATH VISUALIZATION COLORS
# ============================================================================
# One color per simulation class for consistent path visualization

PATH_COLORS: Dict[str, str] = {
    "entry_kitchen": "#E05D2C",  # Orange-red
    "entry_bedroom": "#2B8C8C",  # Teal
    "entry_bathroom": "#2C7FB8",  # Blue
    "bedroom_bathroom": "#3FA37A",  # Green
    "bedroom_kitchen": "#D9A441",  # Gold
}

# ============================================================================
# PLOTTER THEME (CLASSIC - light background)
# ============================================================================

PLOT_BG_COLOR: str = "#f7f4ef"  # Main background
PLOT_PANEL_BG_COLOR: str = "#ffffff"  # Panel background
PLOT_TEXT_COLOR: str = "#1f1f1f"  # Text color
PLOT_GRID_COLOR: str = "#e4e0d8"  # Grid lines

# Room colors for floor plan visualization
PLOT_ROOM_COLORS: Dict[str, str] = {
    "livingRoom": "#cfe1d6",  # Soft green-gray
    "bedroom": "#cfd9e6",  # Soft blue-gray
    "kitchen": "#e6dccf",  # Soft orange-gray
    "bathroom": "#cfe0e6",  # Soft cyan-gray
    "attachedBathroom": "#c7dbe6",  # Soft blue-gray (darker)
    "hallway": "#e6d4cf",  # Soft orange-pink
    "diningRoom": "#eadfcb",  # Soft yellow-gray
    "garage": "#dcdcdc",  # Light gray
    "verandaOutdoorSpace": "#d8e6d1",  # Light green
}

PLOT_DEFAULT_ROOM_COLOR: str = "#efefef"  # Fallback for unknown rooms

# ============================================================================
# ROOM TYPE CODES
# ============================================================================
# Integer codes used in the rasterized grid to identify room types
# These come from pathfinder.py but are centralized here for reference

ROOM_TYPE_CODES: Dict[str, int] = {
    "livingRoom": 1,
    "bedroom": 2,
    "kitchen": 3,
    "bathroom": 4,
    "attachedBathroom": 5,
    "hallway": 6,
    "diningRoom": 7,
    "garage": 8,
    "verandaOutdoorSpace": 9,
}

# ============================================================================
# HEATMAP & VISUALIZATION SETTINGS
# ============================================================================

# Neutral score returned when no relevant data is found (used during scoring edge cases)
NEUTRAL_SCORE_CIRCULATION: float = 20.0
NEUTRAL_SCORE_FURNITURE: float = 10.0
NEUTRAL_SCORE_HALLWAY: float = 18.0
NEUTRAL_SCORE_PRIVACY: float = 25.0

# Heatmap colormap for traffic intensity and other metrics
HEATMAP_COLORMAP: str = "RdYlGn_r"  # Red-Yellow-Green reversed (red=bad, green=good)
