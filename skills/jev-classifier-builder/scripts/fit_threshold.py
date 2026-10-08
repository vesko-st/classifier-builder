#!/usr/bin/env python3
"""
Fit a decision threshold for one class on labelled records.

    python scripts/fit_threshold.py RESULTS.jsonl --labels LABELS.jsonl --class hate [--metric macro_f1]

RESULTS.jsonl is the output of `jev_classifier.py run ... -o` (it needs
class_probabilities: a choice with map, two_level, criteria or ensemble).
LABELS.jsonl holds {"id", "label"} rows; only records in both files are used.
Fit on a random sample (see tools/sample.py --mode random): labels picked for
being uncertain are concentrated near the boundary and give a biased threshold.

Prints the metric at each threshold and the best one, ready for the
classifier's "decision": {"class": ..., "threshold": ...}. Ties go to the
threshold closest to 0.5.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import read_jsonl, read_jsonl_lenient
from jev_classifier import class_metrics


def predict(probs: dict[str, float], cls: str, threshold: float) -> str:
    if probs.get(cls, 0.0) >= threshold:
        return cls
    others = {c: p for c, p in probs.items() if c != cls}
    return max(others, key=lambda c: others[c]) if others else f"not {cls}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--class", dest="cls", required=True)
    parser.add_argument("--metric", choices=["macro_f1", "accuracy"], default="macro_f1")
    args = parser.parse_args()

    gold = {r["id"]: str(r["label"]) for r in read_jsonl(args.labels)}
    rows = [r for r in read_jsonl_lenient(args.results)[0] if "error" not in r and r["id"] in gold]
    if not rows:
        sys.exit("no labelled records in the results file")
    if not all(r.get("class_probabilities") for r in rows):
        sys.exit("results lack class_probabilities (needs map, two_level, criteria or ensemble)")

    scores = []
    for t in [i / 20 for i in range(1, 20)]:
        labeled = [{"gold": gold[r["id"]], "prediction": predict(r["class_probabilities"], args.cls, t)} for r in rows]
        acc = sum(x["gold"] == x["prediction"] for x in labeled) / len(labeled)
        value = class_metrics(labeled)["macro_f1"] if args.metric == "macro_f1" else acc
        scores.append((t, value, acc))
        print(f"threshold {t:.2f}  {args.metric} {value:.3f}  accuracy {acc:.3f}")
    best = max(scores, key=lambda s: (s[1], -abs(s[0] - 0.5)))
    print(f"-- {len(rows)} labelled records; best threshold {best[0]:.2f} ({args.metric} {best[1]:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
