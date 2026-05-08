"""Multi-source Dijkstra over a reverse adjacency.

Operating on the reverse adjacency lets a single sweep compute distances
from every node TO a fixed target set, which is the direction in which the
cost lower bound, the time shortest paths, and the latest-arrival bounds
are all propagated.
"""
import heapq
from collections import defaultdict
from typing import Dict, List, Tuple

INF = float("inf")


def multisource_dijkstra(
    rev_adj: Dict[int, List[Tuple[int, float]]],
    init_costs: Dict[int, float],
) -> Dict[int, float]:
    """Run multi-source Dijkstra on a reverse-adjacency representation.

    ``rev_adj[v] = [(pred, weight), ...]`` lists arcs entering v.
    ``init_costs`` maps each source node to its initial distance and seeds
    the search; nodes not in this map start at +infinity.
    """
    dist: Dict[int, float] = defaultdict(lambda: INF)
    pq: List[Tuple[float, int]] = []

    for x, c in init_costs.items():
        c = float(c)
        if c < dist[x]:
            dist[x] = c
            heapq.heappush(pq, (c, x))

    while pq:
        d, u = heapq.heappop(pq)
        # Lazy deletion: skip entries whose distance has since been improved.
        if d != dist[u]:
            continue
        for pred, w in rev_adj.get(u, []):
            nd = d + w
            if nd < dist[pred]:
                dist[pred] = nd
                heapq.heappush(pq, (nd, pred))
    return dist