#!/usr/bin/env python3
"""Export each run's final classifier and scores into results/ for sharing.

For every run under runs/ with saved snapshots, writes

    results/<run_id>/classifier.json   the final snapshot
    results/<run_id>/run.json          settings, builder model and cost, and every
                                       snapshot with points spent, the builder's
                                       estimate and the test score on each System 1 model

and results/runs.csv with one row per run. Bought labels, journals, transcripts
and per-record predictions stay in runs/.

    python tools/export_results.py [--exclude PREFIX ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

from common import ROOT

RUNS = ROOT / "runs"
HARNESS = RUNS / "_harness"
OUT = ROOT / "results"
SUMMARY_RE = re.compile(r"^v(\d+)_(?:(\w+)_)?test_summary\.json$")
SCORE_FIELDS = ("accuracy", "macro_f1", "est_cost_usd", "total", "answered")
BUILDER_FIELDS = ("model", "effort", "wall_seconds", "num_turns", "total_cost_usd")


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _test_scores(run_id: str) -> dict[int, dict[str, dict]]:
    scores: dict[int, dict[str, dict]] = {}
    for path in sorted((HARNESS / run_id).glob("v*_test_summary.json")):
        match = SUMMARY_RE.match(path.name)
        if not match:
            continue
        summary = json.loads(path.read_text())
        backend = match.group(2) or "jev"
        scores.setdefault(int(match.group(1)), {})[backend] = {
            k: summary[k] for k in SCORE_FIELDS if k in summary
        }
    return scores


def export(run_dir: Path) -> dict | None:
    snapshots = _jsonl(run_dir / "snapshots.jsonl")
    if not snapshots:
        return None
    run_id = run_dir.name
    settings = json.loads((run_dir / "run.json").read_text())
    final = snapshots[-1]
    scores = _test_scores(run_id)
    builder_path = HARNESS / run_id / "summary.json"
    builder = json.loads(builder_path.read_text()) if builder_path.exists() else {}

    record = {
        **settings,
        "builder": {k: builder[k] for k in BUILDER_FIELDS if k in builder} or {"runner": "interactive pilot"},
        "final_version": final["version"],
        "snapshots": [
            {
                "version": s["version"],
                "points_spent": s.get("points_spent"),
                "estimate": s.get("estimate"),
                "note": s.get("note"),
                "test": scores.get(s["version"], {}),
            }
            for s in snapshots
        ],
    }
    dest = OUT / run_id
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run_dir / final["path"], dest / "classifier.json")
    (dest / "run.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    jev = scores.get(final["version"], {}).get("jev", {})
    return {
        "run_id": run_id,
        "task": settings.get("task"),
        "mode": settings.get("mode", "budget"),
        "strategy": settings.get("strategy"),
        "constraints": "+".join(settings.get("constraints", [])),
        "builder_model": record["builder"].get("model", "claude-opus-5-5"),
        "budget": settings.get("budget"),
        "points_spent": final.get("points_spent"),
        "final_version": final["version"],
        "test_accuracy": jev.get("accuracy"),
        "test_macro_f1": jev.get("macro_f1"),
        "builder_cost_usd": round(builder["total_cost_usd"], 2) if "total_cost_usd" in builder else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exclude", nargs="*", default=["smoke-"], help="run-id prefixes to skip")
    args = parser.parse_args()

    rows = []
    for run_dir in sorted(p for p in RUNS.iterdir() if p.is_dir() and not p.name.startswith("_")):
        if any(run_dir.name.startswith(prefix) for prefix in args.exclude):
            continue
        row = export(run_dir)
        if row:
            rows.append(row)
    if not rows:
        sys.exit("no runs with snapshots found")
    with open(OUT / "runs.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"exported {len(rows)} runs to {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
