#!/usr/bin/env python3
"""
Create a builder workspace for one task.

    python tools/new_run.py banking77_routing --budget 100 [--run-id NAME] [--strategy uncertainty]
    python tools/new_run.py banking77_intents_fullpool --all-labels [--run-id NAME]

Writes runs/<run_id>/ with:
    run.json        task name, point budget, strategy, mode, creation time (read by ask_oracle.py)
    task.json       the public task definition, classes resolved
    pool.jsonl      unlabelled training pool (id, text)
    labels.jsonl    labels bought so far (empty; ask_oracle.py appends)
    classifiers/    where the builder saves classifier snapshots
Prints the run directory.

--all-labels gives the builder the gold label of every pool record in
labels.jsonl (tag "given") with a budget of 0, so the user cannot be asked
anything (mode "all_labels").
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

from common import DATA_DIR, ROOT, RUNS_DIR, TASKS_DIR, load_task, private_dir, read_jsonl, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task")
    parser.add_argument("--budget", type=int, help="points the builder may spend")
    parser.add_argument("--all-labels", action="store_true", help="give every pool label; budget 0")
    parser.add_argument("--run-id", help="default: <task>-<timestamp>")
    parser.add_argument("--strategy", default="free", help="skill/strategies/<name>.md, or 'free' for none")
    parser.add_argument("--constraint", action="append", default=[],
                        help="skill/constraints/<name>.md, applied on top of the strategy (repeatable)")
    args = parser.parse_args()
    for name in args.constraint:
        if not (ROOT / "skill" / "constraints" / f"{name}.md").exists():
            parser.error(f"no constraint file skill/constraints/{name}.md")
    if args.all_labels == (args.budget is not None):
        parser.error("pass exactly one of --budget and --all-labels")
    if not (TASKS_DIR / args.task / "task.json").exists():
        parser.error(f"unknown task {args.task!r}")
    pool = DATA_DIR / args.task / "pool.jsonl"
    if not pool.exists():
        parser.error(f"{pool} missing; run tools/prepare_tasks.py {args.task}")
    if args.strategy != "free" and not (ROOT / "skill" / "strategies" / f"{args.strategy}.md").exists():
        parser.error(f"no strategy file skill/strategies/{args.strategy}.md")

    run_id = args.run_id or f"{args.task}-{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    if run_dir.exists():
        parser.error(f"{run_dir} already exists")
    (run_dir / "classifiers").mkdir(parents=True)

    (run_dir / "run.json").write_text(json.dumps({
        "run_id": run_id,
        "task": args.task,
        "budget": 0 if args.all_labels else args.budget,
        "strategy": args.strategy,
        "constraints": args.constraint,
        "mode": "all_labels" if args.all_labels else "budget",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2) + "\n")
    # `source` names the dataset and how labels were derived; builders must not see it.
    public = {k: v for k, v in load_task(args.task).items() if k != "source"}
    (run_dir / "task.json").write_text(json.dumps(public, indent=2) + "\n")
    shutil.copy(pool, run_dir / "pool.jsonl")
    if args.all_labels:
        write_jsonl(run_dir / "labels.jsonl", ({"id": r["id"], "text": r["text"], "label": r["label"], "tag": "given"}
                                               for r in read_jsonl(private_dir(args.task) / "pool.jsonl")))
    else:
        (run_dir / "labels.jsonl").touch()
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
