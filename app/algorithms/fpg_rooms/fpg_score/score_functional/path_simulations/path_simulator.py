from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from .scorer import score_path_simulation


def evaluate_path_simulation(
	rooms: Sequence[Mapping[str, Any]],
	openings: Sequence[Mapping[str, Any]],
	*,
	enable_dev_plot: bool = False,
	output_dir: str | None = None,
) -> Tuple[float, Dict[str, Any]]:
	"""Evaluate circulation-based livability score in [0, 10]."""
	score, diagnostics = score_path_simulation(
		rooms,
		openings,
		enable_dev_plot=enable_dev_plot,
		output_dir=output_dir,
	)
	return max(0.0, min(10.0, float(score))), diagnostics
