from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
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
from app.core.fpg_rooms.config_fpg import OPTUNA_SCORING_VALUES

# Updated per your instructions
ROOM_RELATIONS_MAX_SCORE = float(
    OPTUNA_SCORING_VALUES.get("optuna_score_relations", 0.0)
)
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
    turn_penalty: float


def _relation_weight(
    edge_cost: float,
    source: str,
    target: str,
    room_points: dict[str, OptunaScorePoint],
) -> float:
    p1, p2 = room_points[source], room_points[target]
    distance = math.hypot(p1.x - p2.x, p1.y - p2.y)
    return distance + (distance * edge_cost)


def _get_turn_penalty(
    path: list[str], room_points: dict[str, OptunaScorePoint]
) -> float:
    """
    Calculates the average turn penalty across a given path.
    A penalty is applied if a path direction change at any node exceeds 120 degrees.
    Max turn is 180 degrees (which yields a 100% penalty for that junction).
    """
    num_junctions = len(path) - 2
    if num_junctions <= 0:
        return 0.0

    total_penalty = 0.0

    for i in range(num_junctions):
        p1 = room_points[path[i]]
        p2 = room_points[path[i + 1]]
        p3 = room_points[path[i + 2]]

        # Direction vectors
        v1_x, v1_y = p2.x - p1.x, p2.y - p1.y
        v2_x, v2_y = p3.x - p2.x, p3.y - p2.y

        angle1 = math.degrees(math.atan2(v1_y, v1_x))
        angle2 = math.degrees(math.atan2(v2_y, v2_x))

        # Shortest angle difference
        turn_angle = abs(angle2 - angle1)
        if turn_angle > 180:
            turn_angle = 360 - turn_angle

        if turn_angle > 120:
            # Scale the excess over 120 relative to the 60-degree remaining range (180 - 120)
            junction_penalty = (turn_angle - 120) / 60.0
            total_penalty += junction_penalty

    return total_penalty / num_junctions


def _add_graph_edge(
    graph: nx.Graph,
    u: OptunaScorePoint,
    v: OptunaScorePoint,
    cost: float,
    relation_name: str,
) -> None:
    graph.add_edge(
        u.name,
        v.name,
        relation_cost=cost,
        edge_distance=math.hypot(u.x - v.x, u.y - v.y),
        relation=relation_name,
    )


def _build_graph(room_points: list[OptunaScorePoint]) -> nx.Graph:
    graph = nx.Graph()
    rooms_by_type = defaultdict(list)

    for point in room_points:
        graph.add_node(
            point.name,
            name=point.name,
            room_type=point.room_type,
            x=point.x,
            y=point.y,
        )
        rooms_by_type[point.room_type].append(point)

    for relation in RELATION_RULES:
        room_a, room_b = relation["rooms"]
        cost = float(relation["cost"])

        # Attached bathroom special edge case
        if room_a == ROOM_TYPE_BEDROOM and room_b == "attachedBathroom":
            bedrooms = rooms_by_type[ROOM_TYPE_BEDROOM]
            for bath in rooms_by_type["attachedBathroom"]:
                if not bedrooms:
                    log_critical_graph_scoring(
                        "Missing bedroom node for attachedBathroom relation"
                    )
                    continue
                closest_bedroom = min(
                    bedrooms,
                    key=lambda b: math.hypot(b.x - bath.x, b.y - bath.y),
                )
                _add_graph_edge(
                    graph, bath, closest_bedroom, cost, f"{room_a}-{room_b}"
                )
            continue

        # Standard relation mapping
        nodes_a = rooms_by_type[room_a]
        nodes_b = rooms_by_type[room_b]

        if not nodes_a or not nodes_b:
            log_critical_graph_scoring(
                f"Missing relation node(s) for {room_a} <-> {room_b}"
            )
            continue

        for na in nodes_a:
            for nb in nodes_b:
                _add_graph_edge(graph, na, nb, cost, f"{room_a}-{room_b}")

    # Process Hallways connects universally
    connectable_types = {
        ROOM_TYPE_LIVING_ROOM,
        ROOM_TYPE_BATHROOM,
        ROOM_TYPE_DINING_ROOM,
        ROOM_TYPE_KITCHEN,
        ROOM_TYPE_BEDROOM,
        ROOM_TYPE_HALLWAY,
        "garage",
    }
    for hw in rooms_by_type[ROOM_TYPE_HALLWAY]:
        for other in room_points:
            if other.name != hw.name and other.room_type in connectable_types:
                _add_graph_edge(
                    graph, hw, other, 1.0, f"{hw.room_type}-{other.room_type}"
                )

    return graph


def score_room_relations(
    requirements: FpgRequirements,
    room_points: list[OptunaScorePoint],
) -> SectionScore:
    room_map = room_types_by_name(room_points)
    graph = _build_graph(room_points)
    point_by_name = {point.name: point for point in room_points}

    present_room_types = {point.room_type for point in room_points}
    valid_queries = [
        query
        for query in PATH_QUERIES
        if query["start"] in present_room_types and query["end"] in present_room_types
    ]

    num_valid = len(valid_queries)
    query_weight = ROOM_PATHING_MAX_SCORE / max(1, num_valid) if num_valid > 0 else 0.0
    max_cost = max(
        1.0,
        math.hypot(
            float(requirements.config.floor_plan_width),
            float(requirements.config.floor_plan_height),
        )
        * 3.0,
    )

    pathing_score = 0.0
    warnings: list[str] = []
    path_summaries: list[dict[str, Any]] = []
    debug_reasons: list[str] = []

    hallway_crossing_data = {
        hw.name: {"public": 0, "private": 0, "queries": []}
        for hw in room_points
        if hw.room_type == ROOM_TYPE_HALLWAY
    }

    for query in valid_queries:
        start_type, end_type = query["start"], query["end"]
        start_nodes = [p for p in room_points if p.room_type == start_type]
        end_nodes = [p for p in room_points if p.room_type == end_type]

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
                        weight=lambda s, t, d: _relation_weight(
                            float(d.get("relation_cost", 1.0)), s, t, point_by_name
                        ),
                    )
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

                path_cost = sum(
                    _relation_weight(
                        float(graph.get_edge_data(s, t).get("relation_cost", 1.0)),
                        s,
                        t,
                        point_by_name,
                    )
                    for s, t in zip(path[:-1], path[1:])
                )

                candidates.append(
                    RelationPathCandidate(
                        start_name=start_node.name,
                        end_name=end_node.name,
                        path=path,
                        cost=path_cost,
                        turn_penalty=_get_turn_penalty(path, point_by_name),
                    )
                )

        if not candidates:
            log_critical_graph_scoring(f"No path found for {start_type} -> {end_type}")
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

        best_candidate = min(candidates, key=lambda c: c.cost)

        # Base Path Cost Score
        base_pair_score = query_weight * max(
            0.0, 1.0 - (best_candidate.cost / max_cost)
        )

        # Apply Angle Turn Penalty Scaling
        pair_score = base_pair_score * (1.0 - best_candidate.turn_penalty)
        pathing_score += pair_score

        for node_name in best_candidate.path:
            if node_name in hallway_crossing_data:
                hallway_crossing_data[node_name][query["type"]] += 1
                hallway_crossing_data[node_name]["queries"].append(query)

        if base_pair_score < query_weight:
            debug_reasons.append(
                f"Lost points on {start_type} -> {end_type}: Best path cost is {best_candidate.cost:.2f} "
                f"(Max threshold: {max_cost:.2f}). Base Scored {base_pair_score:.2f}/{query_weight:.2f}."
            )
        if best_candidate.turn_penalty > 0:
            debug_reasons.append(
                f"Turn penalty on {start_type} -> {end_type}: Reduced score by {best_candidate.turn_penalty * 100:.1f}% "
                f"due to sharp directional changes."
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

    # Hallway privacy scoring
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

    if not hallway_crossing_data or not crossed_hallways:
        hallway_privacy_score = HALLWAY_PRIVACY_MAX_SCORE
    else:
        total_hw_score = 0.0
        for hw_name in crossed_hallways:
            pub = hallway_crossing_data[hw_name]["public"]
            priv = hallway_crossing_data[hw_name]["private"]
            total = pub + priv
            total_hw_score += 1.0 if total == 1 else abs(pub - priv) / total

        hallway_privacy_score = (
            total_hw_score / len(crossed_hallways)
        ) * HALLWAY_PRIVACY_MAX_SCORE

    total_score = pathing_score + hallway_privacy_score
    normalized = normalize_section_score(total_score, ROOM_RELATIONS_MAX_SCORE)

    if num_valid < len(PATH_QUERIES):
        warnings.append(
            f"Scored {num_valid}/{len(PATH_QUERIES)} possible relations based on present room types."
        )
        debug_reasons.append(
            f"Missing required rooms. Only evaluating {num_valid} out of {len(PATH_QUERIES)} queries."
        )

    if DEBUG_VERBOSE and normalized < ROOM_RELATIONS_MAX_SCORE:
        print(
            f"\n[DEBUG_VERBOSE] ROOM RELATIONS SCORE FAIL: {normalized:.2f} / {ROOM_RELATIONS_MAX_SCORE:.2f}"
        )
        print("[DEBUG_VERBOSE] Causes for point deductions:")
        if not debug_reasons:
            print(
                "  - Unknown deduction cause (Check `normalize_section_score` or missing elements)"
            )
        for reason in debug_reasons:
            print(f"  - {reason}")

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
