"""Compatibility module for profile-based FPGR generator.

Public API remains ``FloorPlanGenerator`` for existing callers.
"""

from .fpgr_p_generate import FloorPlanGenerator

__all__ = ["FloorPlanGenerator"]
