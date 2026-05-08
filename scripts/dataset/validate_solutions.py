"""Verify each solution from a benchmark CSV against its instance.

Replays the path returned by an algorithm, checks that subsets are served
in order within their time windows, and confirms the reported cost.

Examples
--------
    python scripts/dataset/validate_solutions.py \\
        --instances instances/corrected/ \\
        --results   results/raw/bptl.csv \\
        --out       results/validation/bptl_solutions.csv
"""
import argparse
import ast
import os
from pathlib import Path

import pandas as pd

from sptptw.instance_io import parse_instance
from sptptw.validation import validate_solution


def collect_instance_map(root: Path):
    m = {}
    for dirpath, _dirs, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".txt"):
                m[Path(fname).stem] = str(Path(dirpath) / fname)
    return m


def _status_class(msg: str) -> str:
    if not isinstance(msg, str):
        return "UNKNOWN"
    if msg.startswith("OK"):
        return "OK"
    if msg.startswith("FEASIBLE BUT COST MISMATCH"):
        return "COST_MISMATCH"
    if msg.startswith("NOT FEASIBLE"):
        return "NOT_FEASIBLE"
    if msg.startswith("ERROR"):
        return "ERROR"
    return "UNKNOWN"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", type=Path, required=True,
                        help="folder of instance .txt files (recursive)")
    parser.add_argument("--results", type=Path, required=True,
                        help="benchmark CSV (output of scripts/run_benchmark.py)")
    parser.add_argument("--out", type=Path, required=True,
                        help="output CSV with per-row validation status")
    args = parser.parse_args()

    if not args.instances.exists():
        parser.error(f"instances folder not found: {args.instances}")
    if not args.results.exists():
        parser.error(f"results CSV not found: {args.results}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    inst_map = collect_instance_map(args.instances)
    df = pd.read_csv(args.results)

    # Accept either the new 'served' column or the legacy 'served_nodes'
    served_col = (
        "served" if "served" in df.columns
        else "served_nodes" if "served_nodes" in df.columns
        else None
    )
    if served_col is None:
        parser.error(
            "results CSV must have a 'served' or 'served_nodes' column; "
            f"found columns: {df.columns.tolist()}"
        )

    out_rows = []
    counts = {"OK": 0, "NOT_FEASIBLE": 0, "COST_MISMATCH": 0, "ERROR": 0, "UNKNOWN": 0}

    for _, row in df.iterrows():
        instance_name = row["instance"]
        if pd.isna(row.get("path")) or pd.isna(row.get("cost")):
            msg = "ERROR: row has no solution to validate"
        elif instance_name not in inst_map:
            msg = f"ERROR: instance file not found for {instance_name}"
        else:
            try:
                G, source, dest = parse_instance(inst_map[instance_name])
                # Old CSVs may store nodes as floats (e.g. '[80, 92.0, 24.0]'),
                # so route through float() before int().
                path = [int(float(x)) for x in ast.literal_eval(row["path"])]
                served = [int(float(x)) for x in ast.literal_eval(row[served_col])]
                expected = float(row["cost"])
                msg = validate_solution(G, source, dest, path, served, expected)
            except Exception as e:
                msg = f"ERROR: {e}"

        cls = _status_class(msg)
        counts[cls] = counts.get(cls, 0) + 1
        out_rows.append({
            "instance": instance_name,
            "algorithm": row.get("algorithm"),
            "expected_cost": row.get("cost"),
            "validation_status": cls,
            "validation_message": msg,
        })

    pd.DataFrame(out_rows).to_csv(args.out, index=False)
    print(f"Validated {len(out_rows)} solutions")
    for cls, n in counts.items():
        print(f"  {cls:14s} : {n}")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
