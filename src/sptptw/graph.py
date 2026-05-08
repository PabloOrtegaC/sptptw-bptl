"""Graph data structures for the SPTPTW.

Defines the directed weighted graph G = (V, A) with cost and travel time on
each arc, and time windows / service times on service nodes (Section 2 of
the paper).
"""
from typing import Dict, List, Optional, Set, Tuple


class Node:
    """A vertex of the SPTPTW graph.

    Attributes
    ----------
    node_id      : integer identifier
    time_window  : (e_i, l_i) earliest and latest service-start times,
                   or None for transit nodes
    service_time : s_i, the service duration; None for transit nodes
    """

    __slots__ = ("node_id", "time_window", "service_time")

    def __init__(
        self,
        node_id: int,
        time_window: Optional[Tuple[float, float]] = None,
        service_time: Optional[float] = None,
    ):
        self.node_id = node_id
        self.time_window = time_window
        self.service_time = service_time

    def __repr__(self) -> str:
        return (
            f"Node({self.node_id}, time_window={self.time_window}, "
            f"service_time={self.service_time})"
        )


class Arc:
    """A directed arc with cost c(i,j) and travel time t(i,j)."""

    __slots__ = ("start", "end", "cost", "travel_time")

    def __init__(self, start: int, end: int, cost: float, travel_time: float):
        self.start = start
        self.end = end
        self.cost = cost
        self.travel_time = travel_time

    def __repr__(self) -> str:
        return (
            f"Arc({self.start} -> {self.end}, cost={self.cost}, "
            f"travel_time={self.travel_time})"
        )


class Graph:
    """SPTPTW graph G = (V, A) with an ordered list of disjoint subsets T_1..T_N."""

    def __init__(self):
        self.adj_list: Dict[int, List[int]] = {}
        self.nodes: Dict[int, Node] = {}
        self.arcs: Dict[Tuple[int, int], Arc] = {}
        self.subsets: List[Set[int]] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node
        self.adj_list.setdefault(node.node_id, [])

    def add_arc(self, arc: Arc) -> None:
        """Add or replace an arc.

        If an arc with the same (start, end) is added more than once, the
        attributes are overwritten but ``adj_list`` is NOT double-populated.
        This keeps ``arcs`` and ``adj_list`` consistent and prevents
        write_instance from emitting more arc records than the out-degree
        counts declare.
        """
        key = (arc.start, arc.end)
        is_new = key not in self.arcs
        self.arcs[key] = arc
        if is_new:
            self.adj_list.setdefault(arc.start, []).append(arc.end)

    def add_subset(self, subset: Set[int]) -> None:
        self.subsets.append(subset)

    def get_node_attributes(self, node_id: int) -> Optional[Node]:
        return self.nodes.get(node_id)

    def get_arc_attributes(self, start: int, end: int) -> Optional[Arc]:
        return self.arcs.get((start, end))

    def __repr__(self) -> str:
        return (
            f"Graph(|V|={len(self.nodes)}, |A|={len(self.arcs)}, "
            f"N={len(self.subsets)})"
        )
