import networkx as nx
from collections import deque
from backend.core.logger import logger


def run_cascade(
    G: nx.DiGraph,
    shocked_edges: list[dict],
    max_depth: int = 4,
    decay_factor: float = 0.5
) -> dict:
    """
    BFS shock propagation through the trade network.

    shocked_edges format:
    [
        {
            "from": "RUS",
            "to":   "IND",
            "commodity": "CRUDE_OIL",
            "closure_pct": 50.0   # 0–100% closure
        }
    ]

    Returns cascade results per node showing propagated impact.
    """
    if G is None or G.number_of_nodes() == 0:
        return {"error": "empty graph"}

    # Track impact per node: {iso_code: impact_score 0–100}
    node_impacts   = {node: 0.0 for node in G.nodes()}
    edge_impacts   = {}
    visited_edges  = set()

    # BFS queue: (from_node, to_node, current_shock_pct, depth)
    queue = deque()

    # Apply initial shocks
    for shock in shocked_edges:
        from_node    = shock["from"]
        to_node      = shock["to"]
        closure_pct  = min(float(shock.get("closure_pct", 50)), 100.0)

        if not G.has_node(from_node) or not G.has_node(to_node):
            logger.warning(f"Node not in graph: {from_node} or {to_node}")
            continue

        # Direct impact on the shocked edge
        edge_key = (from_node, to_node)
        edge_impacts[edge_key] = {
            "from":          from_node,
            "to":            to_node,
            "commodity":     shock.get("commodity", "ALL"),
            "closure_pct":   closure_pct,
            "depth":         0,
            "is_direct":     True
        }

        # Impact on destination node (importer)
        node_impacts[to_node] = min(
            node_impacts[to_node] + closure_pct,
            100.0
        )

        # Impact on source node (exporter loses revenue)
        node_impacts[from_node] = min(
            node_impacts[from_node] + closure_pct * 0.3,
            100.0
        )

        # Seed BFS from the destination node
        queue.append((from_node, to_node, closure_pct, 0))

    # BFS propagation
    while queue:
        from_node, to_node, shock_pct, depth = queue.popleft()

        if depth >= max_depth:
            continue

        edge_key = (from_node, to_node, depth)
        if edge_key in visited_edges:
            continue
        visited_edges.add(edge_key)

        # Propagate to downstream neighbors of to_node
        for neighbor in G.successors(to_node):
            if neighbor == from_node:
                continue  # avoid cycles

            edge_data    = G[to_node][neighbor]
            edge_weight  = edge_data.get("weight", 0.5)

            # Propagated shock decays with depth and scales with edge weight
            propagated_shock = shock_pct * decay_factor * edge_weight

            if propagated_shock < 1.0:
                continue  # too small to matter

            # Update node impact
            node_impacts[neighbor] = min(
                node_impacts[neighbor] + propagated_shock,
                100.0
            )

            # Record edge impact
            cascade_edge_key = (to_node, neighbor)
            if cascade_edge_key not in edge_impacts:
                edge_impacts[cascade_edge_key] = {
                    "from":        to_node,
                    "to":          neighbor,
                    "commodity":   "CASCADE",
                    "closure_pct": round(propagated_shock, 2),
                    "depth":       depth + 1,
                    "is_direct":   False
                }

            queue.append((to_node, neighbor, propagated_shock, depth + 1))

    # Only return nodes with non-zero impact
    affected_nodes = {
        node: round(impact, 2)
        for node, impact in node_impacts.items()
        if impact > 0
    }

    logger.info(
        f"BFS cascade complete — "
        f"{len(affected_nodes)} nodes affected, "
        f"{len(edge_impacts)} edges impacted"
    )

    return {
        "node_impacts":  affected_nodes,
        "edge_impacts":  list(edge_impacts.values()),
        "affected_count": len(affected_nodes),
    }