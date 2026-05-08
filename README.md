# SPTPTW-BPTL

Exact algorithms for the **Shortest Path Tour Problem with Time Windows**
(SPTPTW). This repository contains:

- a clean reimplementation of the dynamic-programming labeling algorithm of
  **Di Puglia Pugliese, Guerriero & Macrina (2020)** (`labeling`, the
  baseline);
- the **Backward-Propagated Temporal Labeling** algorithm (`bptl`) introduced
  in the accompanying paper, which strengthens temporal pruning with two new
  bounds computed in preprocessing;
- the benchmark dataset (original and corrected), the dataset-correction
  pipeline, the benchmark runner, and the analysis tooling needed to
  reproduce Tables 2 and 3 of the paper.

> Ortega, P., Duitama, J., and Medaglia, A. L.
> *Improved Time Bounds for Exact Algorithms of the Shortest Path Tour
> Problem with Time Windows.*

---

## What the paper contributes, and where to find it in the code

The contribution is a pair of backward-propagated bounds, computed once in
preprocessing and used to prune labels earlier than the baseline's local
time-to-next-subset check:

- $L_i$ (the **latest-arrival bound** at a service node $i \in T_h$): the
  latest arrival at $i$ that still allows completing all remaining subsets.
- $L_{\text{cut}}(i, k)$ (the **reachability cutoff**): the latest time a
  partial path may be at any node $i$ and still reach $T_{k+1}$ in time to
  complete the tour.

Both are derived in **Section 4** of the paper. The implementation lives in
[`src/sptptw/preprocessing/cutoffs.py`](src/sptptw/preprocessing/cutoffs.py).

### Paper-to-code map

| Paper section | Code |
|---|---|
| §2  Problem definition; resource recursion | [`src/sptptw/graph.py`](src/sptptw/graph.py), [`src/sptptw/algorithms/labeling.py`](src/sptptw/algorithms/labeling.py) |
| §3  Labeling framework (state, dominance, feasibility) | [`src/sptptw/algorithms/_common.py`](src/sptptw/algorithms/_common.py), [`src/sptptw/algorithms/labeling.py`](src/sptptw/algorithms/labeling.py) |
| §3.3 Cost lower bound $\underline{C}(i,r)$ | [`src/sptptw/preprocessing/cost_bounds.py`](src/sptptw/preprocessing/cost_bounds.py) |
| §4.1 Time shortest paths $\delta(i,j)$ | [`src/sptptw/preprocessing/time_distances.py`](src/sptptw/preprocessing/time_distances.py) |
| §4.2 Baseline time-to-next-subset check | [`src/sptptw/algorithms/labeling.py`](src/sptptw/algorithms/labeling.py) |
| §4.3 Latest-arrival bounds $L_i$ | [`src/sptptw/preprocessing/cutoffs.py`](src/sptptw/preprocessing/cutoffs.py) (`compute_latest_arrival_bounds`) |
| §4.4 Reachability cutoffs $L_{\text{cut}}(i,k)$ | [`src/sptptw/preprocessing/cutoffs.py`](src/sptptw/preprocessing/cutoffs.py) (`compute_latest_reach_cutoffs`) |
| §4 Integration into the labeling framework | [`src/sptptw/algorithms/bptl.py`](src/sptptw/algorithms/bptl.py) |
| §5.1 Runtime experiments (Table 2) | [`scripts/run_benchmark.py`](scripts/run_benchmark.py), [`results/raw/`](results/raw/) |
| §5.2 Search-space and memory metrics (Table 3) | same — `explored_labels` and `peak_labels` columns |


The two algorithm files share the entirety of their preprocessing, dominance,
feasibility, and cost-bound logic; the difference between them is exactly the
time-pruning rule discussed in Section 4. This makes the contribution easy
to audit: read `labeling.py` and `bptl.py` side by side.

---

## Repository layout

```
sptptw-bptl/
├── pyproject.toml              # package config, dependencies, pytest setup
├── LICENSE                     # MIT
├── README.md                   # this file
│
├── src/sptptw/
│   ├── graph.py                # Graph, Node, Arc data structures
│   ├── instance_io.py          # parse / write benchmark .txt files
│   ├── solution.py             # Solution dataclass returned by both solvers
│   ├── validation.py           # precondition + solution checkers
│   ├── correction.py           # fix_instance(): best-effort repairs
│   │
│   ├── preprocessing/
│   │   ├── dijkstra.py
│   │   ├── graph_utils.py
│   │   ├── cost_bounds.py      # C_underline(i, r)
│   │   ├── time_distances.py   # delta(i, j)
│   │   └── cutoffs.py          # L_i and L_cut(i, k)   <-- main contribution
│   │
│   └── algorithms/
│       ├── _common.py          # dominance + window check, shared
│       ├── labeling.py         # baseline (Di Puglia Pugliese et al., 2020)
│       └── bptl.py             # Backward-Propagated Temporal Labeling
│
├── scripts/
│   ├── run_single.py           # solve one instance
│   ├── run_benchmark.py        # batch runner with per-instance timeouts
│   └── dataset/
│       ├── validate_instances.py    # check preconditions
│       ├── fix_instances.py         # build corrected/ from original/
│       └── validate_solutions.py    # replay solutions in a results CSV
│
├── instances/
│   ├── README.md               # file format + correction process
│   ├── original/               # Di Puglia Pugliese et al. dataset
│   └── corrected/              # authoritative repaired set used in the paper
│
├── results/
    ├── raw/                    # one CSV per (algorithm, run) from run_benchmark
    └── validation/             # correction reports and solution checks

```

---

## Installation

Requires Python 3.10 or later.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate            # Linux / macOS
# .venv\Scripts\activate              # Windows

# 2. Install the package in editable mode plus dev dependencies
pip install -e ".[dev]"

```

---

## Quick start

```bash

# Solve an instance with a chosen algorithm
python scripts/run_single.py path/to/instance.txt --algorithm bptl
```

---

## Reproducing the paper

The corrected dataset shipped in [`instances/corrected/`](instances/corrected/)
contains the **exact files** used to produce Tables 2 and 3 of the paper.
Reproducing the experiments therefore does not require running the dataset
correction step.

### 1. Confirm every corrected instance is well-formed

```bash
python scripts/dataset/validate_instances.py instances/corrected/ \
    --out results/validation/corrected.csv
```

Expected output: `Validated 1902 instances: 1902 valid, 0 invalid`.

### 2. Run both algorithms over the corrected set

The runner spawns each solve in a subprocess so per-instance timeouts are
enforced reliably. The 900-second limit matches what the paper reports.

```bash
python scripts/run_benchmark.py instances/corrected/ \
    --algorithm labeling --out results/raw/labeling.csv --timeout 900

python scripts/run_benchmark.py instances/corrected/ \
    --algorithm bptl     --out results/raw/bptl.csv     --timeout 900
```

If a run is interrupted, restart it with `--resume` and it will skip
instances already in the output CSV.

### 3. Cross-check the returned solutions

```bash
python scripts/dataset/validate_solutions.py \
    --instances instances/corrected/ \
    --results   results/raw/bptl.csv \
    --out       results/validation/bptl_solutions.csv
```

This replays each path against its instance, checks all time windows, and
verifies the reported cost. Every row should come back `OK`.


---

## How the corrected set was produced

The corrected instances in `instances/corrected/` were derived from the
original Di Puglia Pugliese et al. (2020) (https://drive.google.com/drive/folders/1kocgLjfMHst6BiC_9WBBlOKh8PXi2Ver) dataset (`instances/original/`)
by applying three precondition repairs, documented in detail in
[`instances/README.md`](instances/README.md): forcing
`T_1 = {source}`, forcing `T_N = {destination}`, and resolving subset
overlaps so that the subsets are pairwise disjoint.

The script `scripts/dataset/fix_instances.py` documents the procedure and
can be run on `instances/original/` to regenerate a corrected set:

```bash
python scripts/dataset/fix_instances.py \
    --in     instances/original/ \
    --out    instances/corrected/ \
    --report results/validation/correction_report.csv
```

The repair rules are deterministic except for one tie-breaking case: when a
duplicated element could legitimately remain in more than one subset, the
host subset is chosen uniformly at random. Re-running the script therefore
produces a **valid but not bit-identical** corrected set. This does not
affect the validity of any reported result, since every corrected set
satisfies the same preconditions and any of them is a legitimate witness
for the paper's claims; the version shipped in this repository is the one
on which Tables 2 and 3 were computed.


---

## Citation

```bibtex
@article{ortega2026sptptw,
  title   = {Improved Time Bounds for Exact Algorithms of the Shortest Path
             Tour Problem with Time Windows},
  author  = {Ortega, Pablo and Duitama, Jorge and Medaglia, Andr{\'e}s L.},
  journal = {},
  year    = {},
  doi     = {}
}
```

If you also use the benchmark instances, please additionally cite:

- Festa, P., Guerriero, F., Napoletano, A. (2013). *Solving the Shortest
  Path Tour Problem.*
- Di Puglia Pugliese, L., Guerriero, F., Macrina, G. (2020). *The shortest
  path tour problem with time windows.*

---

## License

MIT. See [`LICENSE`](LICENSE).

## Contact

For questions about the implementation, please open a GitHub issue.
For questions about the paper, contact Andrés L. Medaglia at
`amedagli@uniandes.edu.co`.
