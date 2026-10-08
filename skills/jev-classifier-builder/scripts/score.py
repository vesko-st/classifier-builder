#!/usr/bin/env python3
"""
Score pool results against bought labels, without calling Jev again.

    python scripts/score.py RESULTS.jsonl --labels WORK/labels.jsonl [--tag check | --exclude-tag check]
    python scripts/score.py RESULTS.jsonl --labels WORK/labels.jsonl --ids-file ids.txt

RESULTS.jsonl is the output of `jev_classifier.py run ... -o` over the pool.
--tag keeps labels tagged "tag": TAG in the labels file (e.g. a random
check set); --exclude-tag drops them (e.g. score the rest). --ids-file keeps
only the ids listed in a file (whitespace-separated).

Prints n, accuracy with a 90% interval, macro-F1, and the ids it gets wrong
(at most --max-wrong of them). --confusions N adds per-class precision, recall
and F1 (worst F1 first) and the N most frequent gold -> predicted confusions.
For ensemble results it also scores each member (from member_predictions).
Labelled records missing from RESULTS are reported, not scored.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

from common import read_jsonl, read_jsonl_lenient
from jev_classifier import class_metrics


def wilson(k: int, n: int, z: float = 1.645) -> tuple[float, float]:
    if not n:
        return 0.0, 0.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def report(name: str, pairs: list[tuple[str, str, str]]) -> None:
    n = len(pairs)
    k = sum(g == p for _, g, p in pairs)
    lo, hi = wilson(k, n)
    f1 = class_metrics([{"gold": g, "prediction": p} for _, g, p in pairs])["macro_f1"]
    print(f"{name}: n {n}, accuracy {k / n:.3f} (90% {lo:.2f}-{hi:.2f}), macro-F1 {f1:.3f}")


def print_confusions(pairs: list[tuple[str, str, str]], top: int) -> None:
    classes = sorted({g for _, g, _ in pairs} | {p for _, _, p in pairs})
    rows = []
    for c in classes:
        tp = sum(g == c and p == c for _, g, p in pairs)
        n_gold = sum(g == c for _, g, _ in pairs)
        n_pred = sum(p == c for _, _, p in pairs)
        prec = tp / n_pred if n_pred else 0.0
        rec = tp / n_gold if n_gold else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append((f1, c, n_gold, prec, rec))
    print("per class (worst F1 first): class n precision recall F1")
    for f1, c, n, prec, rec in sorted(rows):
        print(f"  {c} {n} {prec:.2f} {rec:.2f} {f1:.2f}")
    counts = Counter((g, p) for _, g, p in pairs if g != p)
    print("top confusions (gold -> predicted, count):")
    for (g, p), k in counts.most_common(top):
        print(f"  {g} -> {p} {k}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("--labels", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tag")
    group.add_argument("--exclude-tag")
    group.add_argument("--ids-file", type=Path)
    parser.add_argument("--max-wrong", type=int, default=200, help="list at most this many wrong ids")
    parser.add_argument("--confusions", type=int, default=0, metavar="N",
                        help="print per-class scores and the N most frequent confusions")
    args = parser.parse_args()

    labels = read_jsonl(args.labels)
    if args.tag:
        labels = [r for r in labels if r.get("tag") == args.tag]
    elif args.exclude_tag:
        labels = [r for r in labels if r.get("tag") != args.exclude_tag]
    elif args.ids_file:
        keep = set(args.ids_file.read_text().split())
        labels = [r for r in labels if r["id"] in keep]
    if not labels:
        sys.exit("no labels match")

    rows, bad = read_jsonl_lenient(args.results)
    by_id = {r["id"]: r for r in rows if "error" not in r}
    scored = [(lab["id"], str(lab["label"]), str(by_id[lab["id"]]["prediction"]))
              for lab in labels if lab["id"] in by_id]
    missing = [lab["id"] for lab in labels if lab["id"] not in by_id]
    if not scored:
        sys.exit("none of the labelled records are in RESULTS")

    report("classifier", scored)
    wrong = [(i, g, p) for i, g, p in scored if g != p]
    if wrong:
        more = f" ... and {len(wrong) - args.max_wrong} more" if len(wrong) > args.max_wrong else ""
        print("wrong: " + " ".join(f"{i}({g}->{p})" for i, g, p in wrong[: args.max_wrong]) + more)
    if args.confusions:
        print_confusions(scored, args.confusions)

    votes = {i: by_id[i].get("member_predictions") for i, _, _ in scored}
    if all(isinstance(v, list) for v in votes.values()):
        for m in range(min(len(v) for v in votes.values())):
            report(f"member {m}", [(i, g, str(votes[i][m])) for i, g, _ in scored])

    if missing:
        print(f"-- {len(missing)} labelled records not in RESULTS (failed or not run): {' '.join(missing)}",
              file=sys.stderr)
    if bad:
        print(f"-- skipped {bad} unreadable lines in RESULTS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
