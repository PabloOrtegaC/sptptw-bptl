"""Read and write SPTPTW benchmark instances in the Festa et al. (2013) /
Di Puglia Pugliese et al. (2020) text format.

File format
-----------
Line 1: ``n m _ windows_flag N``
        n = |V|, m = |A|, windows_flag = 1, N = number of subsets
Lines 2 .. n+1: out-degree of each node (1-indexed)
Then m lines: ``end cost travel_time`` (arcs grouped by start node)
Then 2 lines: source, destination
Then N lines: ``size  id_1 s_1 e_1 l_1  id_2 s_2 e_2 l_2  ...``
"""
import os
from typing import Tuple

from sptptw.graph import Arc, Graph, Node


def parse_instance(filepath: str) -> Tuple[Graph, int, int]:
    """Parse a benchmark instance file into a Graph plus source and destination."""
    G = Graph()
    with open(filepath, "r") as f:
        header = next(f).strip().split()
        n, _m, _, _, N = map(int, header)

        out_counts = [int(next(f).strip()) for _ in range(n)]

        for node_id in range(1, n + 1):
            G.add_node(Node(node_id))

        for node_id in range(1, n + 1):
            for _ in range(out_counts[node_id - 1]):
                arc_info = next(f).strip().split()
                end = int(float(arc_info[0]))
                cost = float(arc_info[1])
                travel_time = float(arc_info[2])
                G.add_arc(Arc(node_id, end, cost, travel_time))

        source = int(next(f).strip())
        destination = int(next(f).strip())

        for _ in range(N):
            subset_info = next(f).strip().split()
            subset_size = int(subset_info[0])
            subset = set()
            for i in range(subset_size):
                node_id = int(subset_info[1 + 4 * i])
                service_time = float(subset_info[2 + 4 * i])
                e = float(subset_info[3 + 4 * i])
                l = float(subset_info[4 + 4 * i])
                node = G.nodes[node_id]
                node.service_time = service_time
                node.time_window = (e, l)
                subset.add(node_id)
            G.add_subset(subset)

    return G, source, destination


def write_instance(G: Graph, source: int, destination: int, filepath: str) -> None:
    """Write a Graph to disk in the benchmark text format.

    The out-degree counts and the emitted arc records are derived from the
    same source of truth (``G.arcs``) so the two are guaranteed to agree.
    Some original benchmark files list the same (start, end) arc more than
    once; this writer collapses such duplicates into a single record.
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    n = len(G.nodes)
    N = len(G.subsets)

    # Group arcs by start node, preserving insertion order
    arcs_by_start: dict = {}
    for (start, end) in G.arcs:
        arcs_by_start.setdefault(start, []).append(end)

    m = sum(len(v) for v in arcs_by_start.values())

    with open(filepath, "w") as f:
        f.write(f"{n} {m} 0 1 {N}\n")

        # Out-degree counts, in node order
        for node_id in range(1, n + 1):
            f.write(f"{len(arcs_by_start.get(node_id, []))}\n")

        # Arc records, in the same node order
        for node_id in range(1, n + 1):
            for end in arcs_by_start.get(node_id, []):
                arc = G.get_arc_attributes(node_id, end)
                f.write(f"{arc.end} {arc.cost} {arc.travel_time}\n")

        f.write(f"{source}\n")
        f.write(f"{destination}\n")

        for subset in G.subsets:
            parts = [str(len(subset))]
            for node_id in sorted(subset):
                node = G.nodes[node_id]
                s = node.service_time if node.service_time is not None else 0.0
                e, l = node.time_window if node.time_window is not None else (0.0, 0.0)
                parts.extend([str(node_id), str(s), str(e), str(l)])
            f.write(" ".join(parts) + "\n")
