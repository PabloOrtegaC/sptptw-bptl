"""Instance and solution validation.

Two validators are provided:

  validate_preconditions(G, source, destination)
      Checks that an instance is well-formed before solving:
        * source and destination are present and distinct;
        * T_1 = {source} and T_N = {destination};
        * subsets are non-empty, disjoint, and contain only known nodes;
        * arcs have non-negative cost and travel time, and are reflected
          in the adjacency list;
        * service times are non-negative and time windows satisfy e <= l.

  validate_solution(G, source, destination, path, served, expected_cost)
      Replays a returned solution against the instance and checks
      feasibility (visit order, time windows, served-node membership) and
      cost consistency. Used by tests and by the offline solution checker.
"""
from typing import List, Optional, Tuple

from sptptw.graph import Graph


def validate_preconditions(
    G: Graph, source: int, destination: int
) -> Tuple[bool, Optional[List[str]]]:
    """Return (is_valid, errors). ``errors`` is None when is_valid is True."""
    errors: List[str] = []

    if len(G.nodes) == 0:
        errors.append("Graph has no nodes.")
    if len(G.arcs) == 0:
        errors.append("Graph has no arcs.")

    node_ids = set(G.nodes.keys())

    if source not in node_ids:
        errors.append(f"Source node {source} is not in the graph.")
    if destination not in node_ids:
        errors.append(f"Destination node {destination} is not in the graph.")
    if source == destination:
        errors.append("Source and destination are the same.")

    if not isinstance(G.subsets, list) or len(G.subsets) < 2:
        errors.append("No subsets found or fewer than two exist.")

    # If the basics fail, no point in deeper checks
    if errors:
        return False, errors

    subsets = G.subsets

    if subsets[0] != {source}:
        errors.append(f"T1 must equal {{{source}}}, found {subsets[0]}.")
    if subsets[-1] != {destination}:
        errors.append(f"TN must equal {{{destination}}}, found {subsets[-1]}.")

    for idx, S in enumerate(subsets, start=1):
        if not isinstance(S, set):
            errors.append(f"T{idx} is not a set.")
            continue
        if len(S) == 0:
            errors.append(f"T{idx} is empty.")
        unknown = set(S) - node_ids
        if unknown:
            errors.append(f"T{idx} contains nodes not in the graph: {sorted(unknown)}")

    seen, duplicates = set(), set()
    for S in subsets:
        if isinstance(S, set):
            duplicates |= (S & seen)
            seen |= S
    if duplicates:
        errors.append(
            f"The subsets are not disjoint. Elements: {sorted(duplicates)} "
            f"are in two or more subsets"
        )

    for (i, j), arc in G.arcs.items():
        if i not in node_ids or j not in node_ids:
            errors.append(f"Arc {(i, j)} references node(s) not in graph.")
        if arc.cost < 0:
            errors.append(f"Arc {(i, j)} has negative cost: {arc.cost}.")
        if arc.travel_time < 0:
            errors.append(f"Arc {(i, j)} has negative travel_time: {arc.travel_time}.")
        if j not in G.adj_list.get(i, []):
            errors.append(f"Arc {(i, j)} exists but {j} not in adj_list[{i}].")

    service_nodes = (
        set().union(*[S for S in subsets if isinstance(S, set)]) if subsets else set()
    )
    for k in service_nodes:
        node = G.get_node_attributes(k)
        if node is None:
            errors.append(f"Node {k} referenced in subsets but not defined.")
            continue

        if node.service_time is None:
            errors.append(f"Node {k} has no service_time.")
        elif node.service_time < 0:
            errors.append(f"Node {k} has negative service_time: {node.service_time}.")

        tw = node.time_window
        if not (
            isinstance(tw, tuple)
            and len(tw) == 2
            and isinstance(tw[0], (int, float))
            and isinstance(tw[1], (int, float))
        ):
            errors.append(f"Node {k} time_window must be a 2-tuple [e, l], found: {tw}.")
        else:
            e, l = tw
            if e > l:
                errors.append(f"Node {k} time_window invalid: e={e} > l={l}.")

    return (False, errors) if errors else (True, None)


def validate_solution(
    G: Graph,
    source: int,
    destination: int,
    path: List[int],
    served: List[int],
    expected_cost: float,
    tolerance: float = 1e-6,
) -> str:
    """Replay a solution and return a status string starting with one of:
    ``OK``, ``NOT FEASIBLE``, ``FEASIBLE BUT COST MISMATCH``, or ``ERROR``.
    """
    subsets = G.subsets

    if not path:
        return "NOT FEASIBLE: Empty path"
    if path[0] != source:
        return f"NOT FEASIBLE: Path does not start at source {source}"
    if path[-1] != destination:
        return f"NOT FEASIBLE: Path does not end at destination {destination}"

    if len(served) != len(subsets):
        return (
            f"NOT FEASIBLE: Must serve exactly one node per subset "
            f"({len(subsets)} subsets vs {len(served)} served)"
        )
    if len(set(served)) != len(served):
        return "NOT FEASIBLE: served list contains duplicates"
    for k, v in enumerate(served):
        if v not in subsets[k]:
            return f"NOT FEASIBLE: served[{k}]={v} is not in subset T_{k + 1}"
    if served[0] != source:
        return f"NOT FEASIBLE: First served node must be the source {source}"
    if served[-1] != destination:
        return f"NOT FEASIBLE: Last served node must be the destination {destination}"

    # Walk the path and replay resources
    eval_cost = 0.0
    eval_time = 0.0
    next_served_idx = 1  # T_1 served at start

    for u, v in zip(path, path[1:]):
        arc = G.get_arc_attributes(u, v)
        if arc is None:
            return f"NOT FEASIBLE: Missing arc {u} -> {v}"
        eval_cost += float(arc.cost)
        eval_time += float(arc.travel_time)

        if next_served_idx < len(served) and v == served[next_served_idx]:
            nd = G.get_node_attributes(v)
            e, l = float(nd.time_window[0]), float(nd.time_window[1])
            s = float(nd.service_time)
            if eval_time > l:
                return (
                    f"NOT FEASIBLE: Time window violated at node {v} "
                    f"(arrival={eval_time}, window=[{e},{l}])"
                )
            eval_time = max(eval_time, e) + s
            next_served_idx += 1

    if next_served_idx != len(subsets):
        return (
            f"NOT FEASIBLE: Not all subsets were served "
            f"({next_served_idx} of {len(subsets)})"
        )

    if abs(eval_cost - expected_cost) > tolerance:
        return (
            f"FEASIBLE BUT COST MISMATCH: expected {expected_cost}, got {eval_cost}"
        )

    return f"OK: total cost {eval_cost}, total time {eval_time}"
