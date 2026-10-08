#!/usr/bin/env python3
"""
Harness-only: compare groups of runs (e.g. one group per builder model) on the test set.

    python tools/compare_models.py --group opus=run1,run2,run3 --group sonnet=run4,run5,run6 [--bootstrap 2000]

Each run contributes its final snapshot (the highest scored version in
runs/_harness/<run>/). The metric is the task's (accuracy or macro-F1). For each
pair of groups it reports:
    bootstrap    paired bootstrap over test records of the difference in group
                 means: 95% interval and two-sided p. Captures test-set sampling
                 only; treats the runs as fixed.
    permutation  exact permutation test over run scores (all ways to split the
                 runs into two groups of the original sizes). Captures run-to-run
                 variance; with 3 vs 3 runs the smallest one-sided p is 0.05.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys

import numpy as np

from common import RUNS_DIR, load_task, read_jsonl

HARNESS_DIR = RUNS_DIR / "_harness"


def final_results(run_id: str) -> tuple[str, list[dict]]:
    versions = sorted(HARNESS_DIR.glob(f"{run_id}/v*_test_results.jsonl"),
                      key=lambda p: int(re.match(r"v(\d+)", p.name).group(1)))
    if not versions:
        sys.exit(f"{run_id}: no scored snapshots")
    rows = read_jsonl(versions[-1])
    errors = sum(1 for r in rows if r.get("error"))
    if errors:
        sys.exit(f"{versions[-1]}: {errors} records with errors; rescore first")
    return versions[-1].name[:3], rows


def metric_matrix(preds: np.ndarray, gold: np.ndarray, classes: list[str], metric: str) -> np.ndarray:
    """preds: runs x records of class indices. Returns one score per run."""
    if metric == "accuracy":
        return (preds == gold).mean(axis=1)
    scores = []
    for run in preds:
        f1s = []
        for c in range(len(classes)):
            tp = np.sum((run == c) & (gold == c))
            fp = np.sum((run == c) & (gold != c))
            fn = np.sum((run != c) & (gold == c))
            f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
        scores.append(np.mean(f1s))
    return np.array(scores)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--group", action="append", required=True, help="name=run_id,run_id,...")
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    groups: dict[str, list[str]] = {}
    for spec in args.group:
        name, _, runs = spec.partition("=")
        groups[name] = [r for r in runs.split(",") if r]

    tasks = {json.loads((RUNS_DIR / r / "run.json").read_text())["task"] for rs in groups.values() for r in rs}
    if len(tasks) != 1:
        sys.exit(f"runs span several tasks: {tasks}")
    task = load_task(tasks.pop())
    metric = task["metric"]
    classes = sorted(task["classes"])
    index = {c: i for i, c in enumerate(classes)}

    order: list[str] | None = None
    preds: dict[str, np.ndarray] = {}
    gold = None
    print(f"task {task['name']}, metric {metric}")
    for name, runs in groups.items():
        rows_per_run = []
        for run in runs:
            version, rows = final_results(run)
            rows = sorted(rows, key=lambda r: r["id"])
            ids = [r["id"] for r in rows]
            if order is None:
                order = ids
                gold = np.array([index[r["label"]] for r in rows])
            elif ids != order:
                sys.exit(f"{run} was scored on different test records")
            rows_per_run.append([index.get(r["prediction"], -1) for r in rows])
            print(f"  {name:10s} {run:32s} {version}")
        preds[name] = np.array(rows_per_run)

    scores = {name: metric_matrix(p, gold, classes, metric) for name, p in preds.items()}
    print()
    for name, s in scores.items():
        print(f"{name:10s} mean {s.mean():.4f}  runs {' '.join(f'{x:.4f}' for x in s)}")

    rng = np.random.default_rng(args.seed)
    n = len(gold)
    samples = [rng.integers(0, n, n) for _ in range(args.bootstrap)]
    print()
    for a, b in itertools.combinations(groups, 2):
        observed = scores[a].mean() - scores[b].mean()
        diffs = np.array([
            metric_matrix(preds[a][:, idx], gold[idx], classes, metric).mean()
            - metric_matrix(preds[b][:, idx], gold[idx], classes, metric).mean()
            for idx in samples
        ])
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        p_boot = min(1.0, 2 * min(np.mean(diffs <= 0), np.mean(diffs >= 0)))

        pooled = np.concatenate([scores[a], scores[b]])
        k = len(scores[a])
        perm = [pooled[list(c)].mean() - np.delete(pooled, list(c)).mean()
                for c in itertools.combinations(range(len(pooled)), k)]
        perm = np.array(perm)
        p_one = np.mean(perm >= observed - 1e-12) if observed >= 0 else np.mean(perm <= observed + 1e-12)
        p_two = np.mean(np.abs(perm) >= abs(observed) - 1e-12)
        print(f"{a} - {b}: {observed:+.4f}  bootstrap 95% [{lo:+.4f}, {hi:+.4f}] p={p_boot:.3f}  "
              f"permutation p(one-sided)={p_one:.3f} p(two-sided)={p_two:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
