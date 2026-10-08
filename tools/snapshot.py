#!/usr/bin/env python3
"""
Save a classifier version for a run, with the points spent so far.

    python tools/snapshot.py RUN_DIR CLF.json --token T --estimate 0.85 --note "added map"

Validates the classifier, copies it to RUN_DIR/classifiers/vNN.json, and appends
{"version", "time", "points_spent", "estimate", "note"} to RUN_DIR/snapshots.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ask_oracle import spent
from common import OwnershipError, check_owner, read_jsonl, run_lock, token_from
from jev_classifier import ClassifierError, load_classifier


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("classifier")
    parser.add_argument("--estimate", type=float, help="your estimated accuracy, 0-1")
    parser.add_argument("--note", default="", help="what changed")
    parser.add_argument("--token", help="from tools/claim_run.py (default: $RUN_TOKEN)")
    args = parser.parse_args()

    if not (args.run_dir / "run.json").exists():
        parser.error(f"{args.run_dir} is not a run directory")
    if args.estimate is not None and not 0 <= args.estimate <= 1:
        parser.error("--estimate must be between 0 and 1")
    try:
        check_owner(args.run_dir, token_from(args.token))
        clf = load_classifier(args.classifier)
    except (ClassifierError, OwnershipError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    with run_lock(args.run_dir):
        log = args.run_dir / "snapshots.jsonl"
        version = len(read_jsonl(log)) + 1 if log.exists() else 1
        dest = args.run_dir / "classifiers" / f"v{version:02d}.json"
        dest.write_text(json.dumps(clf, indent=2, ensure_ascii=False) + "\n")
        entry = {
            "version": version,
            "path": str(dest.relative_to(args.run_dir)),
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "points_spent": spent(args.run_dir),
            "estimate": args.estimate,
            "note": args.note,
        }
        with log.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry))
    return 0


if __name__ == "__main__":
    sys.exit(main())
