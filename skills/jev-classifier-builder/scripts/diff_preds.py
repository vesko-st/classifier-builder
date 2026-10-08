#!/usr/bin/env python3
"""
Compare two classifier versions' predictions on the same inputs, e.g. to see
how far a rule reaches.

    python scripts/diff_preds.py OLD.jsonl NEW.jsonl [--labels WORK/labels.jsonl]

OLD/NEW are outputs of `jev_classifier.py run ... -o` over the same file.
Prints every record whose prediction changed (old -> new, and the gold label
when bought), then a summary: changes, and bought labels each version gets
wrong.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import read_jsonl, read_jsonl_lenient


def load(path: Path) -> dict:
    rows, bad = read_jsonl_lenient(path)
    if bad:
        print(f"-- {path}: skipped {bad} unreadable lines", file=sys.stderr)
    return {r["id"]: r for r in rows if "error" not in r}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--labels", type=Path)
    args = parser.parse_args()

    old, new = load(args.old), load(args.new)
    gold = {r["id"]: r["label"] for r in read_jsonl(args.labels)} if args.labels and args.labels.exists() else {}
    common = sorted(old.keys() & new.keys())
    changed = [i for i in common if str(old[i]["prediction"]) != str(new[i]["prediction"])]
    for i in changed:
        text = new[i]["input"] if isinstance(new[i]["input"], str) else str(new[i]["input"])
        mark = ""
        if i in gold:
            mark = f"  [label {gold[i]}: {'fixed' if str(new[i]['prediction']) == gold[i] else 'broken' if str(old[i]['prediction']) == gold[i] else 'still wrong'}]"
        print(f"{i}  {old[i]['prediction']} -> {new[i]['prediction']}{mark}  {text[:110]}")

    print(f"-- {len(changed)} of {len(common)} predictions changed", file=sys.stderr)
    for name, preds in (("old", old), ("new", new)):
        wrong = [i for i in gold if i in preds and str(preds[i]["prediction"]) != gold[i]]
        if gold:
            print(f"-- {name}: {len(wrong)} of {len(gold)} bought labels wrong: {', '.join(wrong) or 'none'}", file=sys.stderr)
    missing = sum(1 for p in (args.old, args.new) for r in read_jsonl_lenient(p)[0] if "error" in r)
    if missing:
        print(f"-- {missing} failed calls excluded; rerun to fill them", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
