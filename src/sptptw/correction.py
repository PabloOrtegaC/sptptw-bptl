"""Best-effort repair of malformed SPTPTW instances.

A small fraction of the original benchmark instances of Festa et al. (2013) /
Di Puglia Pugliese et al. (2020) violate the formal preconditions assumed
throughout this work: T_1 = {source}, T_N = {destination}, and the subsets
must be pairwise disjoint. The repairs implemented here are:

  1.  Force T_1 to {source} and T_N to {destination}, replacing whatever was
      there before.
  2.  Resolve subset overlaps:
        * if the duplicated element is the source, keep it only in T_1;
        * if it is the destination, keep it only in T_N;
        * otherwise, keep it in one of the subsets it appears in. To avoid
          emptying any subset, if removing the element would leave exactly
          one subset empty, the element is kept in that subset; if removing
          it would empty multiple subsets, the instance is declared
          unrepairable. Otherwise a uniformly random subset (among those
          that contain the element) is chosen.

If after applying repairs the instance still violates preconditions, the
function returns ``(None, None, None)`` to signal that it could not be fixed.
"""
import random
import re
from typing import Optional, Tuple

from sptptw.graph import Graph
from sptptw.validation import validate_preconditions


def fix_instance(
    G: Graph, source: int, destination: int
) -> Tuple[Optional[Graph], Optional[int], Optional[int]]:
    """Attempt to repair an instance in place. Returns (G, source, destination)
    if fully fixed, or ``(None, None, None)`` if the violations can't be repaired
    by the rules above.
    """
    correct, errors = validate_preconditions(G, source, destination)
    if correct:
        return G, source, destination

    for error in errors:
        if re.match(r"T1 must equal .*, found .*\.$", error):
            G.subsets[0] = {source}

        elif re.match(r"TN must equal .*, found .*\.$", error):
            G.subsets[-1] = {destination}

        elif re.match(r"The subsets are not disjoint\.", error):
            duplicates = [int(x) for x in re.findall(r"\d+", error)]
            for duplicate in duplicates:
                if duplicate == source:
                    G.subsets[0].add(source)
                    for k in range(1, len(G.subsets)):
                        G.subsets[k].discard(duplicate)
                elif duplicate == destination:
                    G.subsets[-1].add(destination)
                    for k in range(len(G.subsets) - 1):
                        G.subsets[k].discard(duplicate)
                else:
                    present_in = [
                        k for k, S in enumerate(G.subsets) if duplicate in S
                    ]
                    if not present_in:
                        continue

                    would_empty = [k for k in present_in if len(G.subsets[k]) == 1]
                    if len(would_empty) > 1:
                        return None, None, None
                    if len(would_empty) == 1:
                        keep_in = would_empty[0]
                    else:
                        keep_in = random.choice(present_in)

                    for k in range(len(G.subsets)):
                        if k != keep_in:
                            G.subsets[k].discard(duplicate)
        else:
            # Unrecognized violation; we don't know how to fix it
            return None, None, None

    correct_after, _ = validate_preconditions(G, source, destination)
    if not correct_after:
        return None, None, None
    return G, source, destination
