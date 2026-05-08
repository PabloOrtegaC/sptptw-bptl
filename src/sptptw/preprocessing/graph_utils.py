"""Helpers for building reverse adjacencies and collecting vertices."""
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from sptptw.graph import Graph


def build_reverse_adj_cost(G: Graph) -> Dict[int, List[Tuple[int, float]]]:
    """Reverse adjacency weighted by arc cost: rev[v] = [(pred, c(pred,v)), ...]."""
    rev: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
    for u, nbrs in G.adj_list.items():
        for v in nbrs:
            arc = G.get_arc_attributes(u, v)
            rev[v].append((u, float(arc.cost)))
    return rev


def build_reverse_adj_time(G: Graph) -> Dict[int, List[Tuple[int, float]]]:
    """Reverse adjacency weighted by travel time: rev[v] = [(pred, t(pred,v)), ...]."""
    rev: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
    for u, nbrs in G.adj_list.items():
        for v in nbrs:
            arc = G.get_arc_attributes(u, v)
            rev[v].append((u, float(arc.travel_time)))
    return rev


def collect_vertices(G: Graph) -> Set[int]:
    """Set of all vertex ids appearing in G (including isolated ones in adj_list)."""
    V: Set[int] = set(G.adj_list.keys())
    for _u, nbrs in G.adj_list.items():
        for v in nbrs:
            V.add(v)
    return V
