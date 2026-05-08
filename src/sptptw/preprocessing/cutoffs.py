"""Backward-propagated latest-arrival bounds and reachability cutoffs.

This module is the main contribution of the paper (Section 4 of
Ortega, Duitama, Medaglia). Given the time-shortest-path distances delta,
it computes:

  L_i for every service node i in T_h:
      The latest arrival time at i that still allows completing all remaining
      subsets T_{h+1}, ..., T_N within their time windows.
      Recurrence (h = N-1, ..., 1):
        L_i = min { l_i,  max_{j in T_{h+1}} ( L_j - delta(i,j) - s_i ) }
      Base case: L_j = l_j for j in T_N.

  L_cut(i, k) for any node i and any subset index k:
      The latest time a partial path may be at i and still reach some node
      in T_{k+1} on time to complete the tour.
        L_cut(i, k) = max_{j in T_{k+1}} ( L_j - delta(i, j) )
"""
from typing import Dict, Tuple

from sptptw.graph import Graph
from sptptw.preprocessing.graph_utils import collect_vertices

INF = float("inf")
NEG_INF = float("-inf")


def compute_latest_arrival_bounds(
    G: Graph, delta: Dict[Tuple[int, int], float]
) -> Dict[int, float]:
    """Return L_i for every service node, computed by backward DP over the subsets."""
    N = len(G.subsets)
    L: Dict[int, float] = {}

    # Base case: last subset
    for j in G.subsets[-1]:
        _e_j, l_j = G.get_node_attributes(j).time_window
        L[j] = l_j

    # Backwards through subsets: T_{N-1}, T_{N-2}, ..., T_1
    for h in range(N - 2, -1, -1):
        for i in G.subsets[h]:
            node_i = G.get_node_attributes(i)
            _e_i, l_i = node_i.time_window
            s_i = node_i.service_time or 0.0

            best = None
            for j in G.subsets[h + 1]:
                L_j = L.get(j)
                if L_j is None:
                    continue
                t_ij = delta.get((i, j), INF)
                if t_ij >= INF:
                    continue
                # Latest arrival at i that still permits service-then-travel-to-j
                candidate = L_j - t_ij - s_i
                best = candidate if best is None else max(best, candidate)

            L[i] = min(l_i, best) if best is not None else l_i
    return L


def compute_latest_reach_cutoffs(
    G: Graph,
    delta: Dict[Tuple[int, int], float],
    L_arrival: Dict[int, float],
) -> Dict[Tuple[int, int], float]:
    """Return L_cut[(i, r)] for every node i and every subset index r in [0..N-1].

    Convention: r is the number of subsets ALREADY served. The next subset to
    serve is therefore T_{r+1}, indexed as ``G.subsets[r]`` (0-indexed list).
    """
    N = len(G.subsets)
    L_cut: Dict[Tuple[int, int], float] = {}
    V = collect_vertices(G)

    for r in range(N):
        subset = G.subsets[r]
        L_w = {
            w: L_arrival.get(w, G.get_node_attributes(w).time_window[1])
            for w in subset
        }
        for i in V:
            best = NEG_INF
            for w in subset:
                t_short = delta.get((i, w), INF)
                if t_short < INF:
                    cand = L_w[w] - t_short
                    if cand > best:
                        best = cand
            L_cut[(i, r)] = best
    return L_cut
