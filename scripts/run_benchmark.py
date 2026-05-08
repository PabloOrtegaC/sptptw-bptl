"""Run an algorithm over a folder of instances and dump per-instance results to CSV.

Each instance runs in its own subprocess so a timeout can be enforced reliably.

Examples
--------
    # Run BPTL on every .txt under instances/corrected/ with a 15-min timeout
    python scripts/run_benchmark.py instances/corrected/ \\
        --algorithm bptl --timeout 900 --out results/raw/bptl.csv

    # Resume an interrupted run (skips instances already in the CSV)
    python scripts/run_benchmark.py instances/corrected/ \\
        --algorithm labeling --out results/raw/labeling.csv --resume
"""
import argparse
import json
import multiprocessing as mp
import os
import time
from pathlib import Path

import pandas as pd

from sptptw.algorithms import bptl, labeling
from sptptw.instance_io import parse_instance

ALGORITHMS = {"labeling": labeling, "bptl": bptl}


def collect_instance_files(root: Path):
    files = []
    for dirpath, _dirs, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".txt"):
                full = Path(dirpath) / fname
                files.append((str(full.relative_to(root)), str(full)))
    return sorted(files)


def _worker(algo_name, instance_path, q):
    """Run one (instance, algorithm) pair in a child process; report via queue."""
    try:
        G, source, destination = parse_instance(instance_path)
    except Exception as e:
        q.put({"status": f"PARSE_ERROR: {e}"})
        return

    solve = ALGORITHMS[algo_name]
    t0 = time.perf_counter()
    try:
        sol = solve(G, source, destination)
        elapsed = time.perf_counter() - t0
        q.put({
            "cost": sol.cost,
            "completion_time": sol.completion_time,
            "path": json.dumps(sol.path) if sol.path else None,
            "served": json.dumps(sol.served) if sol.served else None,
            "explored_labels": sol.explored,
            "peak_labels": sol.peak_labels,
            "solution_time": elapsed,
            "status": "SUCCESS" if sol.feasible else "NO_SOLUTION",
        })
    except Exception as e:
        q.put({"status": f"ERROR: {e}", "solution_time": time.perf_counter() - t0})


def run_with_timeout(algo_name, instance_path, timeout):
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(algo_name, instance_path, q), daemon=True)
    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate()
        p.join(5)
        return {"status": "TIMEOUT_KILLED", "solution_time": float(timeout)}

    if not q.empty():
        return q.get_nowait()

    return {"status": "ERROR: child produced no result"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instances_root", type=Path,
                        help="folder containing .txt instance files (recursively scanned)")
    parser.add_argument("--algorithm", "-a", required=True, choices=list(ALGORITHMS),
                        help="which algorithm to run")
    parser.add_argument("--out", "-o", type=Path, required=True,
                        help="output CSV path")
    parser.add_argument("--timeout", "-t", type=int, default=900,
                        help="per-instance timeout in seconds (default: 900)")
    parser.add_argument("--resume", action="store_true",
                        help="skip instances already present in the output CSV")
    args = parser.parse_args()

    if not args.instances_root.exists():
        parser.error(f"instances root not found: {args.instances_root}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    instance_files = collect_instance_files(args.instances_root)
    print(f"Found {len(instance_files)} instances under {args.instances_root}")

    done = set()
    if args.resume and args.out.exists() and args.out.stat().st_size > 0:
        df_existing = pd.read_csv(args.out)
        done = set(df_existing["instance"].tolist())
        print(f"Resuming: {len(done)} instances already in {args.out}, will skip")

    write_header = not (args.out.exists() and args.out.stat().st_size > 0)

    for rel, full in instance_files:
        instance_name = Path(rel).stem
        if instance_name in done:
            continue
        print(f"  [{args.algorithm}] {rel} ... ", end="", flush=True)

        result = run_with_timeout(args.algorithm, full, args.timeout)
        row = {
            "instance": instance_name,
            "algorithm": args.algorithm,
            "cost": result.get("cost"),
            "completion_time": result.get("completion_time"),
            "path": result.get("path"),
            "served": result.get("served"),
            "explored_labels": result.get("explored_labels"),
            "peak_labels": result.get("peak_labels"),
            "solution_time": result.get("solution_time"),
            "status": result.get("status"),
        }
        pd.DataFrame([row]).to_csv(
            args.out, mode="a", index=False, header=write_header
        )
        write_header = False
        print(f"{row['status']}  cost={row['cost']}  time={row['solution_time']}")

    print(f"\nDone. Results in {args.out}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
