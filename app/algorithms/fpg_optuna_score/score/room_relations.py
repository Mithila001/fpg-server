from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any

import networkx as nx

from app.algorithms.types import FpgRequirements

from ..util.scoring_common import (
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_BEDROOM,
    ROOM_TYPE_DINING_ROOM,
    ROOM_TYPE_HALLWAY,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_VERANDA,
    OptunaScorePoint,
    SectionScore,
    log_critical_graph_scoring,
    normalize_section_score,
    room_types_by_name,
)

ROOM_RELATIONS_MAX_SCORE = 40.0

RELATION_RULES: list[dict[str, Any]] = [
    {"rooms": [ROOM_TYPE_KITCHEN, ROOM_TYPE_HALLWAY], "cost": 1.0},
    {"rooms": [ROOM_TYPE_KITCHEN, ROOM_TYPE_DINING_ROOM], "cost": 0.5},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_KITCHEN], "cost": 1.0},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_HALLWAY], "cost": 1.0},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_VERANDA], "cost": 0.5},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_BEDROOM], "cost": 2.0},
    {"rooms": [ROOM_TYPE_BEDROOM, ROOM_TYPE_HALLWAY], "cost": 0.5},
    {"rooms": [ROOM_TYPE_BEDROOM, "attachedBathroom"], "cost": 0.5},
    {"rooms": [ROOM_TYPE_BATHROOM, ROOM_TYPE_LIVING_ROOM], "cost": 0.5},
]

PATH_QUERIES: list[dict[str, str]] = [
    {"start": ROOM_TYPE_VERANDA, "end": ROOM_TYPE_LIVING_ROOM},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_BEDROOM},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_KITCHEN},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_DINING_ROOM},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_BATHROOM},
    {"start": ROOM_TYPE_BEDROOM, "end": ROOM_TYPE_BATHROOM},
    {"start": ROOM_TYPE_KITCHEN, "end": ROOM_TYPE_DINING_ROOM},
    {"start": ROOM_TYPE_BEDROOM, "end": "attachedBathroom"},
]


@dataclass
class RelationPathCandidate:
    start_name: str
    end_name: str
    path: list[str]
    cost: float


def _relation_weight(
    edge_cost: float,
    source: str,
    target: str,
    room_points: dict[str, OptunaScorePoint],
) -> float:
    source_point = room_points[source]
    target_point = room_points[target]
    distance = hypot(source_point.x - target_point.x, source_point.y - target_point.y)
    return distance + (distance * edge_cost)


def _build_graph(room_points: list[OptunaScorePoint]) -> nx.Graph:
    graph = nx.Graph()

    for point in room_points:
        graph.add_node(
            point.name,
            name=point.name,
            room_type=point.room_type,
            x=point.x,
            y=point.y,
        )

    for relation in RELATION_RULES:
        room_a, room_b = relation["rooms"]
        cost = float(relation["cost"])

        if room_a == ROOM_TYPE_BEDROOM and room_b == "attachedBathroom":
            bedrooms = [point for point in room_points if point.room_type == ROOM_TYPE_BEDROOM]
            attached_bathrooms = [
                point for point in room_points if point.room_type == "attachedBathroom"
            ]
            if not bedrooms:
                log_critical_graph_scoring(
                    "Missing bedroom node for attachedBathroom relation"
                )
                continue
            for bath in attached_bathrooms:
                closest_bedroom = min(
                    bedrooms,
                    key=lambda bedroom: hypot(bedroom.x - bath.x, bedroom.y - bath.y),
                )
                graph.add_edge(
                    bath.name,
                    closest_bedroom.name,
                    relation_cost=cost,
                    edge_distance=hypot(
                        closest_bedroom.x - bath.x,
                        closest_bedroom.y - bath.y,
                    ),
                    relation=f"{room_a}-{room_b}",
                )
            continue

        left_nodes = [point for point in room_points if point.room_type == room_a]
        right_nodes = [point for point in room_points if point.room_type == room_b]
        if not left_nodes or not right_nodes:
            log_critical_graph_scoring(
                f"Missing relation node(s) for {room_a} <-> {room_b}"
            )
            continue

        for left_node in left_nodes:
            for right_node in right_nodes:
                graph.add_edge(
                    left_node.name,
                    right_node.name,
                    relation_cost=cost,
                    edge_distance=hypot(
                        left_node.x - right_node.x,
                        left_node.y - right_node.y,
                    ),
                    relation=f"{room_a}-{room_b}",
                )

    return graph


def _path_cost(
    graph: nx.Graph,
    path: list[str],
    room_points: dict[str, OptunaScorePoint],
) -> float:
    total_cost = 0.0
    for source, target in zip(path[:-1], path[1:]):
        edge_data = graph.get_edge_data(source, target)
        if not edge_data:
            continue
        relation_cost = float(edge_data.get("relation_cost", 1.0))
        total_cost += _relation_weight(relation_cost, source, target, room_points)
    return total_cost


def _match_nodes(room_points: list[OptunaScorePoint], room_type: str) -> list[OptunaScorePoint]:
    return [point for point in room_points if point.room_type == room_type]


def score_room_relations(
    requirements: FpgRequirements,
    room_points: list[OptunaScorePoint],
) -> SectionScore:
    room_map = room_types_by_name(room_points)
    
    # print(f"\nRequirements From Score Room Relations: {requirements}")
    # print(f"Room Points From Score Room Relations: {room_points}\n")
    # print(f"Room Map: {room_map}\n")
    graph = _build_graph(room_points)
    point_by_name = {point.name: point for point in room_points}
    query_weight = ROOM_RELATIONS_MAX_SCORE / max(1, len(PATH_QUERIES))
    max_cost = max(
        1.0,
        hypot(
            float(requirements.config.floor_plan_width),
            float(requirements.config.floor_plan_height),
        )
        * 3.0,
    )

    raw_score = 0.0
    warnings: list[str] = []
    path_summaries: list[dict[str, Any]] = []

    for query in PATH_QUERIES:
        start_type = query["start"]
        end_type = query["end"]
        start_nodes = _match_nodes(room_points, start_type)
        end_nodes = _match_nodes(room_points, end_type)

        if not start_nodes or not end_nodes:
            log_critical_graph_scoring(
                f"Missing path node(s) for {start_type} -> {end_type}"
            )
            path_summaries.append(
                {
                    "label": f"{start_type} -> {end_type}",
                    "path": [],
                    "cost": 0.0,
                    "score": 0.0,
                    "reason": "missing_nodes",
                }
            )
            continue

        candidates: list[RelationPathCandidate] = []
        for start_node in start_nodes:
            for end_node in end_nodes:
                if start_node.name == end_node.name:
                    continue
                try:
                    path = nx.shortest_path(
                        graph,
                        source=start_node.name,
                        target=end_node.name,
                        weight=lambda source, target, data: _relation_weight(
                            float(data.get("relation_cost", 1.0)),
                            source,
                            target,
                            point_by_name,
                        ),
                    )
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

                candidates.append(
                    RelationPathCandidate(
                        start_name=start_node.name,
                        end_name=end_node.name,
                        path=path,
                        cost=_path_cost(graph, path, point_by_name),
                    )
                )

        if not candidates:
            log_critical_graph_scoring(
                f"No path found for {start_type} -> {end_type}"
            )
            path_summaries.append(
                {
                    "label": f"{start_type} -> {end_type}",
                    "path": [],
                    "cost": 0.0,
                    "score": 0.0,
                    "reason": "no_path",
                }
            )
            continue

        best_candidate = min(candidates, key=lambda item: item.cost)
        pair_score = query_weight * max(0.0, 1.0 - (best_candidate.cost / max_cost))
        raw_score += pair_score

        path_summaries.append(
            {
                "label": f"{start_type} -> {end_type}",
                "start": best_candidate.start_name,
                "end": best_candidate.end_name,
                "path": best_candidate.path,
                "cost": best_candidate.cost,
                "score": pair_score,
                "reason": "best_instance_pair",
            }
        )

    normalized = normalize_section_score(raw_score, ROOM_RELATIONS_MAX_SCORE)
    if normalized != raw_score:
        warnings.append(
            f"Room relation score normalized from {raw_score:.2f} to {normalized:.2f}"
        )
    # expose graph so caller can decide to save plots (based on threshold)

    return SectionScore(
        score=normalized,
        max_score=ROOM_RELATIONS_MAX_SCORE,
        details={
            "rooms": room_map,
            "graph_nodes": graph.number_of_nodes(),
            "graph_edges": graph.number_of_edges(),
            "path_summaries": path_summaries,
            "graph": graph,
        },
        warnings=warnings,
    )