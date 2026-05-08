"""Solution dataclass for SPTPTW algorithms."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Solution:
    """Result of solving an SPTPTW instance.

    Attributes
    ----------
    cost           : total travel cost C(v_e), or None if no feasible plan
    completion_time: cumulative time tau(v_e) at the destination
    path           : sequence of visited nodes (v_s, ..., v_e)
    served         : sequence of nodes selected to serve T_1, ..., T_N
    explored       : number of labels popped from the queue
    peak_labels    : maximum number of labels stored simultaneously
    feasible       : True iff a feasible plan was found
    """

    cost: Optional[float] = None
    completion_time: Optional[float] = None
    path: Optional[List[int]] = None
    served: Optional[List[int]] = None
    explored: int = 0
    peak_labels: int = 0
    feasible: bool = False

    def __post_init__(self):
        if self.cost is not None and self.path is not None:
            self.feasible = True

    def summary(self) -> str:
        if not self.feasible:
            return f"INFEASIBLE  (explored={self.explored})"
        return (
            f"cost={self.cost:.4f}  time={self.completion_time:.4f}  "
            f"|path|={len(self.path)}  served={self.served}  "
            f"explored={self.explored}  peak={self.peak_labels}"
        )
