"""Recursively validate every .txt instance under a folder and write a CSV report.

Examples
--------
    python scripts/dataset/validate_instances.py instances/original/ \\
        --out results/validation/original.csv

    python scripts/dataset/validate_instances.py instances/corrected/ \\
        --out results/validation/corrected.csv
"""
import argparse
import os
from pathlib import Path

import pandas as pd

from sptptw.instance_io import parse_instance
from sptptw.validation import validate_preconditions


def collect_instance_files(root: Path):
    files = []
    for dirpath, _dirs, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".txt"):
                full = Path(dirpath) / fname
                files.append((str(full.relative_to(root)), str(full)))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instances_root", type=Path,
                        help="root folder of instance .txt files (recursive)")
    parser.add_argument("--out", "-o", type=Path, required=True,
                        help="output CSV path")
    args = parser.parse_args()

    if not args.instances_root.exists():
        parser.error(f"instances root not found: {args.instances_root}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rel, full in collect_instance_files(args.instances_root):
        instance_name = Path(rel).stem
        folder = str(Path(rel).parent)
        try:
            G, source, destination = parse_instance(full)
            is_valid, errors = validate_preconditions(G, source, destination)
            row = {
                "instance": instance_name,
                "folder": folder,
                "is_valid": is_valid,
                "errors": "; ".join(errors) if errors else "",
            }
        except Exception as e:
            row = {
                "instance": instance_name, "folder": folder,
                "is_valid": False, "errors": f"PARSE_ERROR: {e}",
            }
        rows.append(row)

    df = pd.DataFrame(rows).sort_values(["folder", "instance"])
    df.to_csv(args.out, index=False)

    n_total = len(df)
    n_valid = int(df["is_valid"].sum())
    print(f"Validated {n_total} instances: {n_valid} valid, {n_total - n_valid} invalid")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
