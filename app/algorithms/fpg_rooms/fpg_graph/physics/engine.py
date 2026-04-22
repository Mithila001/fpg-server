from __future__ import annotations

import math

from ..types import GraphBoundary, GraphConvergence, GraphEdge, GraphNode, GraphPhysicsConfig


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _apply_boundary(node: GraphNode, boundary: GraphBoundary) -> None:
    node.x = _clamp(node.x, node.radius, max(node.radius, boundary.width - node.radius))
    node.y = _clamp(node.y, node.radius, max(node.radius, boundary.height - node.radius))


def _resolve_overlaps(nodes: list[GraphNode], boundary: GraphBoundary) -> None:
    for i in range(len(nodes)):
        node_a = nodes[i]
        for j in range(i + 1, len(nodes)):
            node_b = nodes[j]
            dx = node_b.x - node_a.x
            dy = node_b.y - node_a.y
            dist = math.hypot(dx, dy)
            min_dist = node_a.radius + node_b.radius
            if dist >= min_dist:
                continue

            if dist < 1e-6:
                dx, dy, dist = 1.0, 0.0, 1.0

            overlap = min_dist - dist
            ux = dx / dist
            uy = dy / dist
            shift = overlap / 2.0

            node_a.x -= ux * shift
            node_a.y -= uy * shift
            node_b.x += ux * shift
            node_b.y += uy * shift

            _apply_boundary(node_a, boundary)
            _apply_boundary(node_b, boundary)


def run_force_directed_layout(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    boundary: GraphBoundary,
    config: GraphPhysicsConfig,
) -> GraphConvergence:
    if boundary.width <= 0 or boundary.height <= 0:
        raise ValueError("Boundary dimensions must be positive")

    by_id = {node.id: node for node in nodes}
    stable_steps = 0
    final_max_disp = 0.0

    for step in range(config.iterations):
        forces: dict[str, tuple[float, float]] = {node.id: (0.0, 0.0) for node in nodes}

        # Spring attractions.
        for edge in edges:
            node_a = by_id.get(edge.source_id)
            node_b = by_id.get(edge.target_id)
            if node_a is None or node_b is None:
                continue

            dx = node_b.x - node_a.x
            dy = node_b.y - node_a.y
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                dist = 1e-6
                dx = 1e-6

            ux = dx / dist
            uy = dy / dist

            target_distance = (node_a.radius + node_b.radius) * (2.0 - 0.5 * max(0.0, min(2.0, edge.weight)))
            spring_strength = config.spring_constant * max(0.1, edge.weight)
            spring_force = spring_strength * (dist - target_distance)

            fax, fay = forces[node_a.id]
            fbx, fby = forces[node_b.id]
            forces[node_a.id] = (fax + ux * spring_force, fay + uy * spring_force)
            forces[node_b.id] = (fbx - ux * spring_force, fby - uy * spring_force)

        # Pairwise repulsion.
        for i in range(len(nodes)):
            node_a = nodes[i]
            for j in range(i + 1, len(nodes)):
                node_b = nodes[j]
                dx = node_b.x - node_a.x
                dy = node_b.y - node_a.y
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1e-6:
                    dist_sq = 1e-6
                    dx = 1e-3
                    dy = 0.0

                dist = math.sqrt(dist_sq)
                ux = dx / dist
                uy = dy / dist
                repulse = config.repulsion_constant / dist_sq

                fax, fay = forces[node_a.id]
                fbx, fby = forces[node_b.id]
                forces[node_a.id] = (fax - ux * repulse, fay - uy * repulse)
                forces[node_b.id] = (fbx + ux * repulse, fby + uy * repulse)

        # Integrate velocities and positions.
        max_displacement = 0.0
        for node in nodes:
            fx, fy = forces[node.id]
            
            # --- 1. Horizontal "Squeeze" (Center-seeking) ---
            # Keeps the house from being too wide; pulls toward center X
            center_x = boundary.width / 2
            side_pull = 0.1  # Reduced from 0.5 to prevent "thin" houses
            fx += (center_x - node.x) * side_pull

            # --- 2. Back Push (Piston Effect) ---
            # This pushes nodes from the back (max height) toward the front (y=0)
            # The further back a node is, the harder it gets pushed
            back_push_strength = 5
            fy -= back_push_strength * (node.y / boundary.height)

            # --- 3. Front Resistance (Optional) ---
            # If nodes are hitting the front wall (y=0) too hard, 
            # this adds a small "cushion" as they get close to the edge.
            if node.y < boundary.height * 0.1:
                fy += 0.05
            
            node.vx = (node.vx + fx * config.time_step) * config.damping
            node.vy = (node.vy + fy * config.time_step) * config.damping

            speed = math.hypot(node.vx, node.vy)
            if speed > config.max_speed and speed > 0.0:
                ratio = config.max_speed / speed
                node.vx *= ratio
                node.vy *= ratio

            old_x, old_y = node.x, node.y
            node.x += node.vx * config.time_step
            node.y += node.vy * config.time_step
            _apply_boundary(node, boundary)

            displacement = math.hypot(node.x - old_x, node.y - old_y)
            max_displacement = max(max_displacement, displacement)

        _resolve_overlaps(nodes, boundary)

        final_max_disp = max_displacement
        if max_displacement < config.convergence_epsilon:
            stable_steps += 1
        else:
            stable_steps = 0

        if stable_steps >= config.stable_steps_required:
            return GraphConvergence(
                converged=True,
                iterations_run=step + 1,
                final_max_displacement=final_max_disp,
            )

    return GraphConvergence(
        converged=False,
        iterations_run=config.iterations,
        final_max_displacement=final_max_disp,
    )
