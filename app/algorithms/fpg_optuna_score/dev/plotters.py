from __future__ import annotations

from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx

from ..util.scoring_common import OptunaScorePoint


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


def _ensure_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _positions(room_points: Sequence[OptunaScorePoint]) -> dict[str, tuple[float, float]]:
    return {room.name: (room.x, room.y) for room in room_points}


def save_relation_graph_plot(
    graph: nx.Graph,
    room_points: Sequence[OptunaScorePoint],
    output_dir: str | Path,
    filename_prefix: str = "graph",
) -> Path:
    output_path = _ensure_output_dir(output_dir)
    stamp = _timestamp()
    file_path = output_path / f"{filename_prefix}_{stamp}.png"

    positions = _positions(room_points)
    fig, ax = plt.subplots(figsize=(12, 10))
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
    ax.set_title("Optuna relation graph")
    ax.set_axis_off()
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
) -> Path:
    output_path = _ensure_output_dir(output_dir)
    stamp = _timestamp()
    file_path = output_path / f"{filename_prefix}_{stamp}.png"

    positions = _positions(room_points)
    total = max(1, len(path_entries))
    columns = max(1, ceil(total / 2))
    rows = 2 if total > 1 else 1

    fig, axes = plt.subplots(rows, columns, figsize=(6 * columns, 6 * rows))
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]

    for index, entry in enumerate(path_entries):
        axis = axes_list[index]
        nx.draw_networkx_nodes(
            graph, positions, node_size=700, node_color="#d9d9d9", ax=axis
        )
        nx.draw_networkx_labels(graph, positions, font_size=7, ax=axis)
        nx.draw_networkx_edges(graph, positions, edge_color="#c0c0c0", width=1.0, ax=axis)

        path_nodes = entry.get("path", [])
        path_edges = list(zip(path_nodes[:-1], path_nodes[1:])) if len(path_nodes) > 1 else []
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

        axis.set_title(
            f"{entry.get('label', 'path')}\nscore={entry.get('score', 0.0):.2f} cost={entry.get('cost', 0.0):.2f}"
        )
        axis.set_axis_off()

    for axis in axes_list[len(path_entries):]:
        axis.set_axis_off()

    fig.tight_layout()
    fig.savefig(file_path, dpi=180)
    plt.close(fig)
    return file_path