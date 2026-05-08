"""Baseline labeling algorithm of Di Puglia Pugliese et al. (2020).

Time pruning uses the local time-to-next-subset check (Section 4.2): when
extending to node j with r subsets served, the label is kept iff some w in
T_{r+1} satisfies time + delta(j, w) <= l_w. This is the reference against
which BPTL is compared in the experiments.
"""
import heapq
from collections import defaultdict
from typing import Dict, List, Tuple

from sptptw.algorithms._common import Label, dominates
from sptptw.graph import Graph
from sptptw.preprocessing import (
    precompute_cost_lower_bound,
    precompute_time_shortest_paths,
)
from sptptw.solution import Solution

INF = float("inf")


def solve(G: Graph, source: int, destination: int) -> Solution:
    """Solve the SPTPTW instance and return a Solution dataclass."""
    cost_tail = precompute_cost_lower_bound(G)
    T_SP = precompute_time_shortest_paths(G)

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

        if i == destination and r_i == N:
            if c_i < c_bound:
                c_bound = c_i
                best = y

        if c_i >= c_bound:
            continue

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
            _add_label(L, D, y_pass, G, c_bound, T_SP)
            after = len(D[j])
            current_labels += (after - before)
            if current_labels > peak_labels:
                peak_labels = current_labels

            # ----- service extension (if j is in the next subset) -----
            if r_i < N and j in G.subsets[r_i]:
                node_j = G.get_node_attributes(j)
                arrival = t_i + arc.travel_time
                if _is_feasible(arrival, node_j):
                    s_j = node_j.service_time if node_j.service_time is not None else 0.0
                    t_served = max(arrival, node_j.time_window[0]) + s_j
                    y_serve: Label = (
                        c_next, t_served, r_i + 1, pi_i + [j], served_i + [j]
                    )
                    before = len(D[j])
                    _add_label(L, D, y_serve, G, c_bound, T_SP)
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
    T_SP: Dict[Tuple[int, int], float],
) -> None:
    """Push y_j into D[j] and L if it is below the cost bound, passes the
    time-to-next-subset check, and is not dominated. Drop existing labels
    that y_j dominates from BOTH D[j] and L (matching the original behavior).
    """
    cost, time, r, path, _served = y_j
    j = path[-1]
    subsets = G.subsets

    if cost >= c_bound:
        return

    # Time bound check (Section 4.2)
    if r < len(subsets):
        all_violated = True
        for w in subsets[r]:
            l_w = G.get_node_attributes(w).time_window[1]
            t_short = T_SP.get((j, w), INF)
            if time + t_short <= l_w:
                all_violated = False
                break
        if all_violated:
            return

    # Dominance check
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


def _is_feasible(arrival: float, node) -> bool:
    """A served node must satisfy arrival <= l_j (early arrival is allowed
    and consumes waiting time)."""
    return arrival <= node.time_window[1]
