"""Cost lower bound C_underline(i, r) used by both algorithms (Section 3.3 of paper).

The bound combines:
  Psi(v)        : cost of the cheapest path tour from a service node v to v_e
                  that serves the remaining subsets in order.
  sigma(i, j)   : shortest-path cost from i to j on the cost-weighted graph.

For a state at node i having served r subsets:
  C_underline(i, r) = min_{j in T_{r+1}} { sigma(i, j) + Psi(j) }   if i is transit
                    = Psi(i)                                        if i is a service node
"""
from collections import defaultdict
from typing import Dict, Tuple

from sptptw.graph import Graph
from sptptw.preprocessing.dijkstra import multisource_dijkstra
from sptptw.preprocessing.graph_utils import build_reverse_adj_cost, collect_vertices

INF = float("inf")


def _precompute_psi(rev_adj_cost, subsets) -> Dict[int, float]:
    """Psi(v) for every service node v: cost of the cheapest tail tour to v_e."""
    K = len(subsets) - 1  # last subset index
    if K == 0:
        return {v: 0.0 for v in subsets[0]}

    # h[r] = distance from any node to the cheapest completion that starts by
    # entering subset T_{r+1}. We initialize at the destination layer (T_K).
    h = [defaultdict(lambda: INF) for _ in range(K)]
    init_base = {d: 0.0 for d in subsets[K]}
    h[K - 1] = multisource_dijkstra(rev_adj_cost, init_base)

    for r in range(K - 2, -1, -1):
        init = {x: h[r + 1][x] for x in subsets[r + 1]}
        h[r] = multisource_dijkstra(rev_adj_cost, init)

    psi: Dict[int, float] = {}
    for r, S in enumerate(subsets):
        for v in S:
            psi[v] = 0.0 if r == K else h[r].get(v, INF)
    return psi


def _precompute_min_transit_plus_tail(
    G: Graph, rev_adj_cost, subsets, psi: Dict[int, float]
) -> Dict[Tuple[int, int], float]:
    """For every (u, r): cheapest cost from u that enters T_{r+1} and completes the tour."""
    V_all = collect_vertices(G)
    M: Dict[Tuple[int, int], float] = {}
    for r in range(len(subsets)):
        init = {j: psi[j] for j in subsets[r] if psi.get(j, INF) < INF}
        dist = multisource_dijkstra(rev_adj_cost, init) if init else {}
        for u in V_all:
            M[(u, r)] = dist.get(u, INF)
    return M


def precompute_cost_lower_bound(G: Graph) -> Dict[Tuple[int, int], float]:
    """Return C_underline as a dict keyed by (node, r_already_served)."""
    rev_adj = build_reverse_adj_cost(G)
    psi = _precompute_psi(rev_adj, G.subsets)
    return _precompute_min_transit_plus_tail(G, rev_adj, G.subsets, psi)
