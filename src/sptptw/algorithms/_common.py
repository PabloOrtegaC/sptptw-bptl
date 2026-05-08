"""Shared label representation and dominance check.

A label is a 5-tuple ``(cost, time, r, path, served)``:
  cost   : C(i), cumulative travel cost
  time   : tau(i), clock after the last completed service
  r      : number of subsets served so far (T_1 counted, since v_s in T_1)
  path   : list of visited node ids, source first
  served : list of node ids selected to serve T_1, ..., T_r

Dominance compares only the first three resources, as in
Di Puglia Pugliese et al. (2020). The path and served lists are carried
along for solution reconstruction and have no effect on the comparison.
"""
from typing import Tuple

Label = Tuple[float, float, int, list, list]


def dominates(a: Label, b: Label) -> bool:
    """Return True iff ``a`` dominates ``b``: c_a <= c_b, t_a <= t_b,
    r_a >= r_b, with at least one strict inequality."""
    c1, t1, r1, _, _ = a
    c2, t2, r2, _, _ = b
    cond = (c1 <= c2) and (t1 <= t2) and (r1 >= r2)
    strict = (c1 < c2) or (t1 < t2) or (r1 > r2)
    return cond and strict