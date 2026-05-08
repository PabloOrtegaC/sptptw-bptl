"""Apply best-effort repairs to every malformed instance under a folder.

Reads `.txt` instances recursively from ``--in``, applies ``fix_instance`` to
each, and writes the repaired version under ``--out`` preserving the
relative path. A CSV report records whether each instance was already valid,
repaired, or unrepairable.

Examples
--------
    python scripts/dataset/fix_instances.py \\
        --in  instances/original/ \\
        --out instances/corrected/ \\
        --report results/validation/correction_report.csv
"""
import argparse
import os
import random 
from pathlib import Path

import pandas as pd

from sptptw.correction import fix_instance
from sptptw.instance_io import parse_instance, write_instance
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
    parser.add_argument("--in", dest="in_root", type=Path, required=True,
                        help="root folder of original instances (recursive)")
    parser.add_argument("--out", dest="out_root", type=Path, required=True,
                        help="root folder where corrected instances will be written")
    parser.add_argument("--report", type=Path, default=None,
                        help="optional CSV report path")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for the disjointness tiebreaker (default: 42)")
    args = parser.parse_args()

    if not args.in_root.exists():
        parser.error(f"input root not found: {args.in_root}")
    args.out_root.mkdir(parents=True, exist_ok=True)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    
    rows = []
    n_already_ok = n_repaired = n_failed = 0

    for rel, full in collect_instance_files(args.in_root):
        instance_name = Path(rel).stem
        folder = str(Path(rel).parent)
        save_path = args.out_root / rel

        try:
            G, source, destination = parse_instance(full)
            already_ok, _ = validate_preconditions(G, source, destination)

            if already_ok:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                write_instance(G, source, destination, str(save_path))
                status = "ALREADY_VALID"
                n_already_ok += 1
            else:
                G_fix, src_fix, dst_fix = fix_instance(G, source, destination)
                if G_fix is None:
                    status = "UNREPAIRABLE"
                    n_failed += 1
                else:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    write_instance(G_fix, src_fix, dst_fix, str(save_path))
                    status = "REPAIRED"
                    n_repaired += 1
        except Exception as e:
            status = f"PARSE_ERROR: {e}"
            n_failed += 1

        rows.append({"instance": instance_name, "folder": folder, "status": status})
        print(f"  [{status:14s}] {rel}")

    print()
    print(f"Already valid : {n_already_ok}")
    print(f"Repaired      : {n_repaired}")
    print(f"Failed        : {n_failed}")
    print(f"Total         : {n_already_ok + n_repaired + n_failed}")

    if args.report is not None:
        df = pd.DataFrame(rows).sort_values(["folder", "instance"])
        df.to_csv(args.report, index=False)
        print(f"\nReport written to {args.report}")


if __name__ == "__main__":
    main()
