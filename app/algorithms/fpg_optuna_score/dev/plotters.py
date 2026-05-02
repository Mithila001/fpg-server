from __future__ import annotations

from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.axes import Axes
import networkx as nx

from ..util.scoring_common import OptunaScorePoint


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


def _ensure_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _positions(
    room_points: Sequence[OptunaScorePoint],
) -> dict[str, tuple[float, float]]:
    return {room.name: (room.x, room.y) for room in room_points}


def _draw_grid(
    ax: Axes, floor_width: float, floor_height: float, grid_scale: float
) -> None:
    if grid_scale <= 0:
        return

    x_ticks: list[float] = []
    y_ticks: list[float] = []

    x_pos = 0.0
    while x_pos <= floor_width + 1e-9:
        x_ticks.append(round(x_pos, 10))
        x_pos += grid_scale

    y_pos = 0.0
    while y_pos <= floor_height + 1e-9:
        y_ticks.append(round(y_pos, 10))
        y_pos += grid_scale

    if not x_ticks or x_ticks[-1] != floor_width:
        x_ticks.append(float(floor_width))
    if not y_ticks or y_ticks[-1] != floor_height:
        y_ticks.append(float(floor_height))

    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)
    ax.grid(
        True,
        which="major",
        color="#c7c7c7",
        linestyle="--",
        linewidth=1.0,
        alpha=0.8,
        zorder=0,
    )
    ax.tick_params(
        bottom=False,
        left=False,
        labelbottom=False,
        labelleft=False,
        length=0,
    )


def save_relation_graph_plot(
    graph: nx.Graph,
    room_points: Sequence[OptunaScorePoint],
    output_dir: str | Path,
    filename_prefix: str = "graph",
    floor_width: float | None = None,
    floor_height: float | None = None,
    grid_scale: float | None = None,
) -> Path:
    output_path = _ensure_output_dir(output_dir)
    stamp = _timestamp()
    file_path = output_path / f"{filename_prefix}_{stamp}.png"

    positions = _positions(room_points)

    # Calculate figsize based on floor aspect ratio
    if floor_width is not None and floor_height is not None:
        aspect_ratio = float(floor_width) / float(floor_height)
        # Base height of 10 inches, width scales with aspect ratio
        fig_height = 10
        fig_width = fig_height * aspect_ratio
    else:
        fig_width, fig_height = 12, 10

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Draw floor boundary if provided
    if floor_width is not None and floor_height is not None:
        floor_rect = patches.Rectangle(
            (0, 0),
            floor_width,
            floor_height,
            linewidth=2.5,
            edgecolor="#d32f2f",
            facecolor="none",
            linestyle="--",
            label=f"Floor Boundary ({floor_width:.1f}x{floor_height:.1f})",
        )
        ax.add_patch(floor_rect)

    # Draw grid lines based on grid_scale
    if grid_scale is not None and floor_width is not None and floor_height is not None:
        _draw_grid(ax, float(floor_width), float(floor_height), float(grid_scale))

    nx.draw_networkx_nodes(graph, positions, node_size=900, node_color="#f4d35e", ax=ax)
    nx.draw_networkx_labels(graph, positions, font_size=8, ax=ax)
    nx.draw_networkx_edges(graph, positions, edge_color="#5c677d", width=1.5, ax=ax)
    edge_labels = {
        (source, target): f"{data.get('relation_cost', 1.0):.1f}"
        for source, target, data in graph.edges(data=True)
    }
    nx.draw_networkx_edge_labels(
        graph, positions, edge_labels=edge_labels, font_size=7, ax=ax
    )

    # Set axis limits and aspect ratio
    if floor_width is not None and floor_height is not None:
        ax.set_xlim(0, floor_width)
        ax.set_ylim(0, floor_height)
        ax.set_aspect("equal", adjustable="box")
        ax.legend(loc="upper right", fontsize=9)

    ax.set_title("Optuna relation graph")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(file_path, dpi=180)
    plt.close(fig)
    return file_path


def save_relation_path_plot(
    graph: nx.Graph,
    room_points: Sequence[OptunaScorePoint],
    path_entries: Sequence[dict[str, Any]],
    output_dir: str | Path,
    filename_prefix: str = "pathing",
    floor_width: float | None = None,
    floor_height: float | None = None,
) -> Path:
    output_path = _ensure_output_dir(output_dir)
    stamp = _timestamp()
    file_path = output_path / f"{filename_prefix}_{stamp}.png"

    positions = _positions(room_points)
    total = max(1, len(path_entries))
    columns = max(1, ceil(total / 2))
    rows = 2 if total > 1 else 1

    # Calculate figsize based on floor aspect ratio
    if floor_width is not None and floor_height is not None:
        aspect_ratio = float(floor_width) / float(floor_height)
        # Base size per subplot
        subplot_width = 6 * aspect_ratio
        subplot_height = 6
        fig_width = subplot_width * columns
        fig_height = subplot_height * rows
    else:
        fig_width = 6 * columns
        fig_height = 6 * rows

    fig, axes = plt.subplots(rows, columns, figsize=(fig_width, fig_height))
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]

    for index, entry in enumerate(path_entries):
        axis = axes_list[index]

        # Draw floor boundary if provided
        if floor_width is not None and floor_height is not None:
            floor_rect = patches.Rectangle(
                (0, 0),
                floor_width,
                floor_height,
                linewidth=1.5,
                edgecolor="#d32f2f",
                facecolor="none",
                linestyle="--",
            )
            axis.add_patch(floor_rect)

        nx.draw_networkx_nodes(
            graph, positions, node_size=700, node_color="#d9d9d9", ax=axis
        )
        nx.draw_networkx_labels(graph, positions, font_size=7, ax=axis)
        nx.draw_networkx_edges(
            graph, positions, edge_color="#c0c0c0", width=1.0, ax=axis
        )

        path_nodes = entry.get("path", [])
        path_edges = (
            list(zip(path_nodes[:-1], path_nodes[1:])) if len(path_nodes) > 1 else []
        )
        if path_nodes:
            nx.draw_networkx_nodes(
                graph,
                positions,
                nodelist=path_nodes,
                node_size=800,
                node_color="#75c9b7",
                ax=axis,
            )
        if path_edges:
            nx.draw_networkx_edges(
                graph,
                positions,
                edgelist=path_edges,
                edge_color="#e76f51",
                width=3.0,
                ax=axis,
            )

        # Set axis limits and aspect ratio
        if floor_width is not None and floor_height is not None:
            axis.set_xlim(0, floor_width)
            axis.set_ylim(0, floor_height)
            axis.set_aspect("equal", adjustable="box")

        axis.set_title(
            f"{entry.get('label', 'path')}\nscore={entry.get('score', 0.0):.2f} cost={entry.get('cost', 0.0):.2f}"
        )
        axis.set_axis_off()

    for axis in axes_list[len(path_entries) :]:
        axis.set_axis_off()

    fig.tight_layout()
    fig.savefig(file_path, dpi=180)
    plt.close(fig)
    return file_path
