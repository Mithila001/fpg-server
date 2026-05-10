from typing import List, Tuple


def centroid_from_vertices(vertices: List[Tuple[float, float]]) -> tuple[float, float]:
    if not vertices:
        return (0.0, 0.0)
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _edge_list(
    vertices: List[Tuple[float, float]],
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    edges: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    if not vertices:
        return edges
    for i in range(len(vertices)):
        a = vertices[i]
        b = vertices[(i + 1) % len(vertices)]
        edges.append((a, b))
    return edges


def _same_point(
    a: Tuple[float, float], b: Tuple[float, float], tol: float = 1e-6
) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def polygon_shared_edge(r1: object, r2: object) -> bool:
    """Return True if polygons r1 and r2 share at least one edge.

    Each room is expected to have attribute or key `vertices` as a list of (x,y).
    """
    v1 = (
        getattr(r1, "vertices", None) or r1.get("vertices")
        if isinstance(r1, dict)
        else None
    )
    v2 = (
        getattr(r2, "vertices", None) or r2.get("vertices")
        if isinstance(r2, dict)
        else None
    )
    if not v1 or not v2:
        return False

    edges1 = _edge_list(v1)
    edges2 = _edge_list(v2)

    for a1, b1 in edges1:
        for a2, b2 in edges2:
            # check if edges are the same disregarding direction
            if (_same_point(a1, a2) and _same_point(b1, b2)) or (
                _same_point(a1, b2) and _same_point(b1, a2)
            ):
                return True
    return False
