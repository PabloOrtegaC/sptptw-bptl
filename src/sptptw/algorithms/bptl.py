"""Backward-Propagated Temporal Labeling (BPTL).

Identical to the baseline labeling algorithm except for the time-pruning
rule. Where the baseline asks "is some node in T_{r+1} still reachable on
time?", BPTL applies two stronger checks computed once in preprocessing:

  L_i      : when extending TO a service node i, the label is pruned if
             arrival > L_i (Section 4.3).
  L_cut    : when adding any label at j with r subsets served, the label
             is pruned if time > L_cut(j, r) (Section 4.4).

Both checks integrate feasibility for ALL remaining subsets, not just the
immediately next one.
"""
import heapq
from collections import defaultdict
from typing import Dict, List, Tuple

from sptptw.algorithms._common import Label, dominates
from sptptw.graph import Graph
from sptptw.preprocessing import (
    compute_latest_arrival_bounds,
    compute_latest_reach_cutoffs,
    precompute_cost_lower_bound,
    precompute_time_shortest_paths,
)
from sptptw.solution import Solution

INF = float("inf")
NEG_INF = float("-inf")


def solve(G: Graph, source: int, destination: int) -> Solution:
    """Solve the SPTPTW instance and return a Solution dataclass."""
    cost_tail = precompute_cost_lower_bound(G)
    T_SP = precompute_time_shortest_paths(G)
    L_latest = compute_latest_arrival_bounds(G, T_SP)
    L_cut = compute_latest_reach_cutoffs(G, T_SP, L_latest)

    start_node = G.get_node_attributes(source)
    s_src = start_node.service_time if start_node.service_time is not None else 0.0
    e_src = start_node.time_window[0]
    y_start: Label = (0.0, e_src + s_src, 1, [source], [source])
    N = len(G.subsets)

    D: Dict[int, List[Label]] = defaultdict(list)
    L: List[Tuple[float, Label]] = []

    explored = 0
    peak_labels = 1
    current_labels = 1

    D[source].append(y_start)
    heapq.heappush(L, (y_start[0], y_start))

    best: Label = None
    c_bound = INF

    while L:
        _, y = heapq.heappop(L)
        explored += 1
        c_i, t_i, r_i, pi_i, served_i = y
        i = pi_i[-1]

        # Update the incumbent on every completed tour.
        if i == destination and r_i == N:
            if c_i < c_bound:
                c_bound = c_i
                best = y

        if c_i >= c_bound:
            continue

        # Cost lower bound (Section 3.3): prune when the optimistic completion
        # estimate already exceeds the current incumbent.
        if r_i < N:
            tail_lb = cost_tail[(i, r_i)]
            if c_i + tail_lb >= c_bound:
                continue

        for j in G.adj_list[i]:
            arc = G.get_arc_attributes(i, j)
            c_next = c_i + arc.cost
            t_pass = t_i + arc.travel_time

            # ----- pass-through extension (no service at j) -----
            y_pass: Label = (c_next, t_pass, r_i, pi_i + [j], served_i)
            before = len(D[j])
            _add_label(L, D, y_pass, G, c_bound, L_cut)
            after = len(D[j])
            current_labels += (after - before)
            if current_labels > peak_labels:
                peak_labels = current_labels

            # ----- service extension (if j is in the next subset) -----
            if r_i < N and j in G.subsets[r_i]:
                node_j = G.get_node_attributes(j)
                arrival = t_i + arc.travel_time

                # L_i check (Section 4.3). For nodes in T_N we have L_j = l_j
                # by definition, so the dict lookup falls back to l_j.
                Lj_arrival_bound = L_latest.get(j, node_j.time_window[1])
                if _is_feasible(arrival, node_j, Lj_arrival_bound):
                    s_j = node_j.service_time if node_j.service_time is not None else 0.0
                    t_served = max(arrival, node_j.time_window[0]) + s_j
                    y_serve: Label = (
                        c_next, t_served, r_i + 1, pi_i + [j], served_i + [j]
                    )
                    before = len(D[j])
                    _add_label(L, D, y_serve, G, c_bound, L_cut)
                    after = len(D[j])
                    current_labels += (after - before)
                    if current_labels > peak_labels:
                        peak_labels = current_labels

    if best is None:
        return Solution(explored=explored, peak_labels=peak_labels)

    cost, t, _r, path, served = best
    return Solution(
        cost=cost,
        completion_time=t,
        path=path,
        served=served,
        explored=explored,
        peak_labels=peak_labels,
    )


def _add_label(
    L: List[Tuple[float, Label]],
    D: Dict[int, List[Label]],
    y_j: Label,
    G: Graph,
    c_bound: float,
    L_cut: Dict[Tuple[int, int], float],
) -> None:
    """Insert y_j into D[j] and L if it survives the three pruning rules:
    cost bound, L_cut reachability cutoff, and dominance. Labels dominated
    by y_j are removed from both D[j] and L.
    """
    cost, time, r, path, _served = y_j
    j = path[-1]
    subsets = G.subsets

    if cost >= c_bound:
        return

    # L_cut bound (Section 4.4) replaces the baseline time-to-next-subset check
    if r < len(subsets):
        cutoff = L_cut.get((j, r), NEG_INF)
        if cutoff == NEG_INF or time > cutoff:
            return

     # Dominance against existing labels at the same node.
    dominated_by_existing = False
    to_remove = []
    for y_old in D[j]:
        if dominates(y_old, y_j):
            dominated_by_existing = True
            break
        if dominates(y_j, y_old):
            to_remove.append(y_old)

    if dominated_by_existing:
        return

    if to_remove:
        for y_old in to_remove:
            D[j].remove(y_old)
            for idx, item in enumerate(L):
                if item[1] == y_old:
                    del L[idx]
                    heapq.heapify(L)
                    break

    D[j].append(y_j)
    heapq.heappush(L, (cost, y_j))


def _is_feasible(arrival: float, node, Lj_arrival_bound: float) -> bool:
    """Two checks combined: the latest-arrival bound L_i, and the local
    time window. Both must hold for service at this node to be feasible.
    """
    if arrival > Lj_arrival_bound:
        return False
    return arrival <= node.time_window[1]
