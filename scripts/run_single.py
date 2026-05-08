"""Solve a single SPTPTW instance.

Examples
--------
    python scripts/run_single.py instances/example/tiny.txt
    python scripts/run_single.py path/to/instance.txt --algorithm bptl
    python scripts/run_single.py path/to/instance.txt --algorithm both
"""
import argparse
import time
from pathlib import Path

from sptptw.algorithms import bptl, labeling
from sptptw.instance_io import parse_instance

ALGORITHMS = {"labeling": labeling, "bptl": bptl}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance", type=Path, help="path to a .txt instance file")
    parser.add_argument(
        "--algorithm", "-a",
        choices=["labeling", "bptl", "both"],
        default="both",
        help="which algorithm to run (default: both)",
    )
    args = parser.parse_args()

    if not args.instance.exists():
        parser.error(f"instance not found: {args.instance}")

    G, source, destination = parse_instance(str(args.instance))
    print(f"Instance: {args.instance.name}")
    print(f"  |V|={len(G.nodes)}  |A|={len(G.arcs)}  N={len(G.subsets)}")
    print(f"  source={source}  destination={destination}")
    print()

    algos_to_run = ["labeling", "bptl"] if args.algorithm == "both" else [args.algorithm]

    for name in algos_to_run:
        solve = ALGORITHMS[name]
        t0 = time.perf_counter()
        sol = solve(G, source, destination)
        elapsed = time.perf_counter() - t0
        print(f"[{name}]  {sol.summary()}")
        print(f"          wall-clock = {elapsed:.4f} s")
        if sol.feasible:
            print(f"          path = {sol.path}")
        print()


if __name__ == "__main__":
    main()
