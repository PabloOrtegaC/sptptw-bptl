# Benchmark instances

The benchmark used in the paper is the SPTPTW dataset of
**Di Puglia Pugliese, Guerriero & Macrina (2020)**, which extends the SPTP
test problems of **Festa, Guerriero & Napoletano (2013)** with travel times,
service times, and time windows.

## Folder layout

```
instances/
├── original/          ← the dataset as published by Di Puglia Pugliese et al.
└── corrected/         ← the same instances after the precondition repairs
                        described below. THIS is the set used to produce
                        Tables 2 and 3 of the paper.
```

The two folders mirror the same subdirectory tree (visiting orders ×
topologies). All experiments in the paper use `instances/corrected/`.

## File format

Each instance is a plain-text file with the following structure:

```
n m _ windows_flag N        # |V|, |A|, unused (for future extensions),
                              1 (time-windows flag), number of subsets N

out_deg(1)                  # number of outgoing arcs from each node,
out_deg(2)                  # one per line, in 1-indexed order
...
out_deg(n)

end cost travel_time        # arc records, m of them total, grouped by start
...                         # node (out_deg(i) records for node i, in order)

source                      # node id of the source v_s
destination                 # node id of the destination v_e

size  id_1 s_1 e_1 l_1  id_2 s_2 e_2 l_2  ...     # subset T_1
size  ...                                          # subset T_2
...                                                # one line per subset
```

Notes:
- Node IDs are in `[1, n]` (1-indexed).
- For each service node `i`: `s_i` is the service duration, `[e_i, l_i]` is
  the time window (earliest and latest service-start times).
- The first subset `T_1` must equal `{source}` and the last subset `T_N` must
  equal `{destination}`. Subsets must be pairwise disjoint.
- Transit nodes (vertices that do not belong to any `T_h`) appear in the
  graph but not in any subset line, and have neither service time nor a
  time window.

The format is exactly the one used by Di Puglia Pugliese et al. (2020); the
implementation reading and writing it is in
[`src/sptptw/instance_io.py`](../src/sptptw/instance_io.py).

## Counts (Table 1 of the paper)

| visiting order | complete | grid | random | total |
|:---|---:|---:|---:|---:|
| max2min  |  84 | 160 | 232 | 476 |
| min2max  |  82 | 160 | 232 | 474 |
| inv      |  84 | 160 | 232 | 476 |
| original |  84 | 160 | 232 | 476 |
| **total**| **334** | **640** | **928** | **1902** |

## Why a `corrected/` set exists

A small number of instances in the original dataset violate the formal
preconditions assumed throughout the paper. The script in
[`scripts/dataset/fix_instances.py`](../scripts/dataset/fix_instances.py)
applies three deterministic, conservative repairs:

1. **`T_1 = {source}` is enforced.** If `T_1` does not exactly equal
   `{source}`, it is replaced with `{source}`.
2. **`T_N = {destination}` is enforced.** Symmetric to the rule above.
3. **Subsets are made pairwise disjoint.** When an element appears in
   multiple subsets:
   - If the element is the source, it is kept only in `T_1`.
   - If it is the destination, it is kept only in `T_N`.
   - Otherwise, it is kept in exactly one of the subsets that contained it.
     To avoid emptying any subset, if removing it would leave one subset
     empty, it is kept in that subset; if removing it would empty more than
     one subset, the instance is declared **unrepairable** and is skipped.
     When no subset is at risk of becoming empty, the kept subset is chosen
     uniformly at random among those that contained the element.

Repairs that fall outside this catalogue (negative weights, malformed
records, etc.) cause the instance to be skipped rather than silently
modified. The status of every instance (`ALREADY_VALID`, `REPAIRED`, or
`UNREPAIRABLE`) is logged in a CSV report.

## Re-running the correction script

The version of `instances/corrected/` shipped in this repository is the
**authoritative** corrected set used to produce Tables 2 and 3 of the
paper. Re-running the correction script is therefore not required to
reproduce the experiments — it is provided so the procedure is documented
and auditable.

```bash
# 1. Drop the original dataset under instances/original/ preserving the
#    visiting-order x topology subfolder structure (max2min/, min2max/, ...)

# 2. Generate a freshly-corrected set:
python scripts/dataset/fix_instances.py \
    --in     instances/original/ \
    --out    instances/corrected_regenerated/ \
    --report results/validation/correction_report.csv

# 3. Confirm every corrected instance passes preconditions:
python scripts/dataset/validate_instances.py instances/corrected_regenerated/ \
    --out results/validation/corrected_regenerated.csv
```

Repair rules 1 and 2 above are deterministic. Rule 3 contains a uniform
random tiebreaker that fires when a duplicated element could legitimately
remain in more than one subset. Re-running the script therefore produces a
**valid but not bit-identical** corrected set: the resulting files satisfy
exactly the same preconditions as the shipped ones, but the specific
subset assignments for some duplicated elements may differ. Both choices
are equally legitimate and either is suitable for reproducing the paper's
claims.

## Provenance and citation

If you publish results using this dataset, please cite the original sources:

- Festa, P., Guerriero, F., Napoletano, A. (2013). *Solving the Shortest
  Path Tour Problem.* European Journal of Operational Research.
- Di Puglia Pugliese, L., Guerriero, F., Macrina, G. (2020). *The shortest
  path tour problem with time windows.* Networks.
