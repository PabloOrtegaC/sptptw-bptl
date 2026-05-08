"""Shortest travel times delta(i, j) on the time-weighted graph (Section 4.1).

These distances ignore service and waiting times. They are used both by the
baseline time-to-next-subset check and by the latest-arrival / reachability
bounds introduced in this work.
"""
from typing import Dict, Tuple

from sptptw.graph import Graph
from sptptw.preprocessing.dijkstra import multisource_dijkstra
from sptptw.preprocessing.graph_utils import build_reverse_adj_time, collect_vertices

INF = float("inf")


def precompute_time_shortest_paths(G: Graph) -> Dict[Tuple[int, int], float]:
    """Return delta as a dict keyed by (origin, destination_in_some_subset).

    For every node v and every service node w, delta[(v, w)] is the
    shortest travel time from v to w on the time-weighted graph.
    """
    rev_adj = build_reverse_adj_time(G)
    V = collect_vertices(G)

    delta: Dict[Tuple[int, int], float] = {}
    for r, subset in enumerate(G.subsets):
        for w in subset:
            dist = multisource_dijkstra(rev_adj, {w: 0.0})
            for v in V:
                delta[(v, w)] = dist.get(v, INF)
    return delta
