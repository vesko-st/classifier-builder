#!/usr/bin/env python3
"""
The 0-point baseline: a choice classifier built from the public task
definition alone (description + class names), scored on a harness split.

    python tools/zero_shot.py banking77_routing [--split val]

Writes baselines/<task>/zero_shot.json (the classifier), and
baselines/<task>/zero_shot_<split>_{results.jsonl,summary.json}.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import ROOT, load_task, private_dir

HERE = Path(__file__).resolve().parent


def build(task: dict) -> dict:
    return {
        "version": 1,
        "name": f"{task['name']}_zero_shot",
        "description": "0-point baseline from the public task definition.",
        "model": "jev-latest",
        "type": "choice",
        "instructions": f"{task['description']} Which class does this input belong to?",
        "criteria": task["classes"],
        "state_template": f"{task['input']}\n\n{{{{input}}}}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task")
    parser.add_argument("--split", default="val", choices=["val", "test"])
    args = parser.parse_args()

    out_dir = ROOT / "baselines" / args.task
    out_dir.mkdir(parents=True, exist_ok=True)
    clf_path = out_dir / "zero_shot.json"
    clf_path.write_text(json.dumps(build(load_task(args.task)), indent=2) + "\n")
    return subprocess.call([
        sys.executable, str(HERE / "jev_classifier.py"), "run", str(clf_path),
        str(private_dir(args.task) / f"{args.split}.jsonl"),
        "--input-field", "text", "--label-field", "label", "-q",
        "-o", str(out_dir / f"zero_shot_{args.split}_results.jsonl"),
        "--summary-output", str(out_dir / f"zero_shot_{args.split}_summary.json"),
    ])


if __name__ == "__main__":
    sys.exit(main())
