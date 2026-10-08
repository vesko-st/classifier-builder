#!/usr/bin/env python3
"""
Follow a builder run: print oracle requests, journal entries and snapshots as
they appear, scoring each snapshot on the hidden validation split.

    python tools/watch_run.py RUN_DIR [--interval 5] [--idle-minutes 45]

Validation scores go to runs/_harness/<run_id>/, outside the builder's run
directory, so the builder never sees them.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from common import RUNS_DIR, private_dir, read_jsonl

HERE = Path(__file__).resolve().parent


def _new_lines(path: Path, seen: int) -> list[dict]:
    if not path.exists():
        return []
    rows = read_jsonl(path)
    return rows[seen:]


def _journal_titles(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line[3:].strip() for line in path.read_text().splitlines() if line.startswith("## ")]


def score(run_dir: Path, task: str, snap: dict, harness_dir: Path) -> dict:
    out = harness_dir / f"v{snap['version']:02d}_val"
    subprocess.run([
        sys.executable, str(HERE / "jev_classifier.py"), "run", str(run_dir / snap["path"]),
        str(private_dir(task) / "val.jsonl"), "--input-field", "text", "-q",
        "-o", f"{out}_results.jsonl", "--summary-output", f"{out}_summary.json",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return json.loads(Path(f"{out}_summary.json").read_text())


def emit(tag: str, text: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} [{tag}] {text}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--idle-minutes", type=float, default=45.0)
    args = parser.parse_args()

    run = json.loads((args.run_dir / "run.json").read_text())
    harness_dir = RUNS_DIR / "_harness" / run["run_id"]
    harness_dir.mkdir(parents=True, exist_ok=True)
    progress = harness_dir / "progress.jsonl"
    emit("start", f"watching {run['run_id']} (task {run['task']}, budget {run['budget']})")

    seen_log = seen_snap = seen_journal = 0
    spent = 0
    last_activity = time.monotonic()
    while time.monotonic() - last_activity < args.idle_minutes * 60:
        activity = False
        for entry in _new_lines(args.run_dir / "oracle_log.jsonl", seen_log):
            seen_log += 1
            spent += entry["cost"]
            activity = True
            if entry["kind"] == "label":
                emit("label", f"{len(entry['ids'])} labels, +{entry['cost']} pts (total {spent})")
            else:
                answer = entry["answer"].replace("\n", " ")
                emit("ask", f"+{entry['cost']} pts (total {spent}) Q: {entry['question'][:200]} | A: {answer[:300]}")
        titles = _journal_titles(args.run_dir / "journal.md")
        for title in titles[seen_journal:]:
            emit("journal", title[:200])
            activity = True
        seen_journal = len(titles)
        for snap in _new_lines(args.run_dir / "snapshots.jsonl", seen_snap):
            seen_snap += 1
            activity = True
            summary = score(args.run_dir, run["task"], snap, harness_dir)
            row = {**snap, "val_accuracy": summary.get("accuracy"), "val_macro_f1": summary.get("macro_f1")}
            with progress.open("a") as f:
                f.write(json.dumps(row) + "\n")
            est = "?" if snap["estimate"] is None else f"{snap['estimate']:.2f}"
            emit("snapshot", f"v{snap['version']:02d} at {snap['points_spent']} pts: val acc {row['val_accuracy']}, "
                             f"macro-F1 {row['val_macro_f1']}, builder estimate {est} | {snap['note'][:150]}")
        if activity:
            last_activity = time.monotonic()
        time.sleep(args.interval)
    emit("stop", f"idle for {args.idle_minutes} minutes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
