from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any

import networkx as nx

from app.algorithms.types import FpgRequirements

from ..util.scoring_common import (
    ROOM_TYPE_ATTACHED_BATHROOM,
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
ROOM_PATHING_MAX_SCORE = 30.0
HALLWAY_PRIVACY_MAX_SCORE = 10.0
DEBUG_VERBOSE = False  # Toggle this to False to silence terminal debug logs

RELATION_RULES: list[dict[str, Any]] = [
    {"rooms": [ROOM_TYPE_KITCHEN, ROOM_TYPE_DINING_ROOM], "cost": 0.5},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_KITCHEN], "cost": 1.0},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_VERANDA], "cost": 0.5},
    {"rooms": [ROOM_TYPE_LIVING_ROOM, ROOM_TYPE_BEDROOM], "cost": 2.0},
    {"rooms": [ROOM_TYPE_BEDROOM, ROOM_TYPE_ATTACHED_BATHROOM], "cost": 0.5},
    {"rooms": [ROOM_TYPE_BATHROOM, ROOM_TYPE_LIVING_ROOM], "cost": 0.5},
]

PATH_QUERIES: list[dict[str, str]] = [
    {"start": ROOM_TYPE_VERANDA, "end": ROOM_TYPE_LIVING_ROOM, "type": "public"},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_BEDROOM, "type": "private"},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_KITCHEN, "type": "public"},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_DINING_ROOM, "type": "public"},
    {"start": ROOM_TYPE_LIVING_ROOM, "end": ROOM_TYPE_BATHROOM, "type": "public"},
    {"start": ROOM_TYPE_BEDROOM, "end": ROOM_TYPE_BATHROOM, "type": "private"},
    {"start": ROOM_TYPE_KITCHEN, "end": ROOM_TYPE_DINING_ROOM, "type": "public"},
    {"start": ROOM_TYPE_BEDROOM, "end": ROOM_TYPE_ATTACHED_BATHROOM, "type": "private"},
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
            bedrooms = [
                point for point in room_points if point.room_type == ROOM_TYPE_BEDROOM
            ]
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

    hallways = [p for p in room_points if p.room_type == ROOM_TYPE_HALLWAY]
    if hallways:
        connectable_types = {
            ROOM_TYPE_LIVING_ROOM,
            ROOM_TYPE_BATHROOM,
            ROOM_TYPE_DINING_ROOM,
            ROOM_TYPE_KITCHEN,
            ROOM_TYPE_BEDROOM,
            "garage",
        }
        for hw in hallways:
            for other in room_points:
                if other.name == hw.name:
                    continue
                if (
                    other.room_type in connectable_types
                    or other.room_type == ROOM_TYPE_HALLWAY
                ):
                    graph.add_edge(
                        hw.name,
                        other.name,
                        relation_cost=1.0,
                        edge_distance=hypot(hw.x - other.x, hw.y - other.y),
                        relation=f"{hw.room_type}-{other.room_type}",
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


def _match_nodes(
    room_points: list[OptunaScorePoint], room_type: str
) -> list[OptunaScorePoint]:
    return [point for point in room_points if point.room_type == room_type]


def score_room_relations(
    requirements: FpgRequirements,
    room_points: list[OptunaScorePoint],
) -> SectionScore:
    room_map = room_types_by_name(room_points)
    graph = _build_graph(room_points)
    point_by_name = {point.name: point for point in room_points}

    # 1. Identify which room types are actually present in the generated points
    present_room_types = {point.room_type for point in room_points}

    # 2. Filter PATH_QUERIES to only include pairs where both rooms exist
    valid_queries = [
        query
        for query in PATH_QUERIES
        if query["start"] in present_room_types and query["end"] in present_room_types
    ]

    # 3. Calculate weight based on valid queries only
    num_valid = len(valid_queries)
    query_weight = ROOM_PATHING_MAX_SCORE / max(1, num_valid) if num_valid > 0 else 0.0

    max_cost = max(
        1.0,
        hypot(
            float(requirements.config.floor_plan_width),
            float(requirements.config.floor_plan_height),
        )
        * 3.0,
    )

    pathing_score = 0.0
    warnings: list[str] = []
    path_summaries: list[dict[str, Any]] = []

    # Track hallway crossing data
    hallway_crossing_data = {
        hw.name: {"public": 0, "private": 0, "queries": []}
        for hw in room_points
        if hw.room_type == ROOM_TYPE_HALLWAY
    }

    # We will accumulate debug reasons here
    debug_reasons: list[str] = []

    # 4. Iterate only over valid queries
    for query in valid_queries:
        start_type = query["start"]
        end_type = query["end"]
        start_nodes = _match_nodes(room_points, start_type)
        end_nodes = _match_nodes(room_points, end_type)

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
            log_msg = f"No path found for {start_type} -> {end_type}"
            log_critical_graph_scoring(log_msg)
            debug_reasons.append(
                f"Zero points for {start_type} -> {end_type}: No routable path found in graph."
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
        pathing_score += pair_score

        # Track which hallways were crossed
        for node_name in best_candidate.path:
            if node_name in hallway_crossing_data:
                hallway_crossing_data[node_name][query["type"]] += 1
                hallway_crossing_data[node_name]["queries"].append(query)

        # Track if we lost points due to high path cost
        if pair_score < query_weight:
            debug_reasons.append(
                f"Lost points on {start_type} -> {end_type}: Best path cost is {best_candidate.cost:.2f} "
                f"(Max threshold: {max_cost:.2f}). Scored {pair_score:.2f}/{query_weight:.2f}."
            )

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

    # Hallway privacy score calculation
    hallways = [p for p in room_points if p.room_type == ROOM_TYPE_HALLWAY]
    hallway_privacy_score = 0.0

    crossed_hallways = [
        hw_name
        for hw_name, data in hallway_crossing_data.items()
        if (data["public"] + data["private"]) > 0
    ]
    uncrossed_hallway_points = [
        point_by_name[hw_name]
        for hw_name, data in hallway_crossing_data.items()
        if (data["public"] + data["private"]) == 0
    ]

    if len(hallways) == 0:
        hallway_privacy_score = HALLWAY_PRIVACY_MAX_SCORE
    else:
        if len(crossed_hallways) > 0:
            total_hw_score = 0.0
            for hw_name in crossed_hallways:
                pub = hallway_crossing_data[hw_name]["public"]
                priv = hallway_crossing_data[hw_name]["private"]
                total = pub + priv

                if total == 1:
                    total_hw_score += 1.0
                else:
                    hw_score = abs(pub - priv) / total
                    total_hw_score += hw_score

            avg_hw_score = total_hw_score / len(crossed_hallways)
            hallway_privacy_score = avg_hw_score * HALLWAY_PRIVACY_MAX_SCORE
        else:
            hallway_privacy_score = HALLWAY_PRIVACY_MAX_SCORE

    total_score = pathing_score + hallway_privacy_score
    normalized = normalize_section_score(total_score, ROOM_RELATIONS_MAX_SCORE)

    if num_valid < len(PATH_QUERIES):
        warnings.append(
            f"Scored {num_valid}/{len(PATH_QUERIES)} possible relations based on present room types."
        )
        debug_reasons.append(
            f"Missing required rooms. Only evaluating {num_valid} out of {len(PATH_QUERIES)} path queries."
        )

    # --- ADDED DEBUG LOGGING HERE ---
    if DEBUG_VERBOSE and normalized < ROOM_RELATIONS_MAX_SCORE:
        print(
            f"\n[DEBUG_VERBOSE] ROOM RELATIONS SCORE FAIL: {normalized:.2f} / {ROOM_RELATIONS_MAX_SCORE:.2f}"
        )
        print("[DEBUG_VERBOSE] Causes for point deductions:")
        if not debug_reasons:
            print(
                "  - Unknown deduction cause (Check `normalize_section_score` or graph missing elements)"
            )
        for reason in debug_reasons:
            print(f"  - {reason}")
    # --------------------------------
    # print(f"FUNC: Hallway Crossing Data: {hallway_crossing_data}")
    # print(f"FUNC: Uncrossed Hallways: {[hw.name for hw in uncrossed_hallway_points]}")
    return SectionScore(
        score=normalized,
        max_score=ROOM_RELATIONS_MAX_SCORE,
        details={
            "rooms": room_map,
            "graph_nodes": graph.number_of_nodes(),
            "graph_edges": graph.number_of_edges(),
            "path_summaries": path_summaries,
            "graph": graph,
            "valid_queries_count": num_valid,
            "uncrossed_hallways": uncrossed_hallway_points,
            "hallway_crossings": hallway_crossing_data,
        },
        warnings=warnings,
    )
