#!/usr/bin/env python3
"""
Harness-only: one line per run with test scores of the first and final snapshot.

    python tools/collect_runs.py run1 run2 ...

Columns: task metric, first and final snapshot test score, points spent at the
final snapshot, the builder's own final estimate, number of snapshots, builder
cost (USD) and wall time from runs/_harness/<run>/summary.json.
"""

from __future__ import annotations

import json
import sys

from common import RUNS_DIR, read_jsonl

HARNESS_DIR = RUNS_DIR / "_harness"


def test_score(run_id: str, version: int, metric: str) -> str:
    path = HARNESS_DIR / run_id / f"v{version:02d}_test_summary.json"
    if not path.exists():
        return "  -  "
    summary = json.loads(path.read_text())
    if summary.get("errors"):
        return "err"
    return f"{summary[metric]:.3f}"


def main() -> None:
    print(f"{'run':34} {'metric':9} {'first':>6} {'final':>6} {'pts':>4} {'est':>5} {'n':>2} {'usd':>5} {'min':>4}")
    for run_id in sys.argv[1:]:
        run_dir = RUNS_DIR / run_id
        snaps_path = run_dir / "snapshots.jsonl"
        if not snaps_path.exists():
            print(f"{run_id:34} no snapshots")
            continue
        snaps = read_jsonl(snaps_path)
        metric = json.loads((run_dir / "task.json").read_text()).get("metric", "accuracy")
        summary_path = HARNESS_DIR / run_id / "summary.json"
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        cost = summary.get("cost") or summary.get("total_cost_usd")
        wall = summary.get("wall_seconds")
        last = snaps[-1]
        print(f"{run_id:34} {metric:9} {test_score(run_id, snaps[0]['version'], metric):>6} "
              f"{test_score(run_id, last['version'], metric):>6} {last.get('points_spent', 0):>4} "
              f"{last.get('estimate') or 0:>5.3f} {len(snaps):>2} "
              f"{cost if cost is None else round(cost, 2)!s:>5} {wall and round(wall / 60)!s:>4}")


if __name__ == "__main__":
    main()
