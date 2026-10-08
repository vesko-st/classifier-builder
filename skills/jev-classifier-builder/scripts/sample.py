#!/usr/bin/env python3
"""
Pick unlabelled pool records to buy, at random or as a category audit.

    python scripts/sample.py RESULTS.jsonl --mode random -n 12 [--labels WORK/labels.jsonl] [--seed 1]
    python scripts/sample.py RESULTS.jsonl --mode category -n 10 [--min-size 5] [--labels ...]

RESULTS.jsonl is the output of `jev_classifier.py run ... -o` over the pool.

random    a uniform sample: the only unbiased basis for an accuracy estimate
          or for fitting a decision threshold.
category  a random sample spread over the classifier's categories (its top
          option, group/option path, clause, or agreement count): every
          category with at least --min-size records gets one pick, the rest
          are shared in proportion to category size. Finds options mapped to
          the wrong class, which margin-based picks miss when the classifier is
          confidently wrong.

Records already in --labels are skipped. Prints category, id, prediction, text;
the last line is the ids, ready to paste into a labelling request.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path

from common import read_jsonl, read_jsonl_lenient


def allocate(sizes: dict[str, int], n: int, min_size: int) -> dict[str, int]:
    eligible = {c: s for c, s in sizes.items() if s >= min_size}
    alloc = {c: 0 for c in sizes}
    if not eligible:
        eligible = sizes
    for c in sorted(eligible, key=lambda c: -eligible[c])[:n]:
        alloc[c] = 1
    left = n - sum(alloc.values())
    total = sum(eligible.values())
    quotas = {c: left * s / total for c, s in eligible.items()}
    for c, q in quotas.items():
        alloc[c] += int(q)
    for c in sorted(quotas, key=lambda c: quotas[c] - int(quotas[c]), reverse=True):
        if sum(alloc.values()) >= n:
            break
        alloc[c] += 1
    return {c: min(k, sizes[c]) for c, k in alloc.items() if k}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("--mode", choices=["random", "category"], required=True)
    parser.add_argument("-n", type=int, required=True)
    parser.add_argument("--labels", type=Path, help="skip records already labelled")
    parser.add_argument("--min-size", type=int, default=5, help="category mode: smallest category guaranteed a pick")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    owned = {r["id"] for r in read_jsonl(args.labels)} if args.labels and args.labels.exists() else set()
    rows = [r for r in read_jsonl_lenient(args.results)[0] if "error" not in r and r["id"] not in owned]
    rng = random.Random(args.seed)

    if args.mode == "random":
        picked = [("-", r) for r in rng.sample(rows, min(args.n, len(rows)))]
    else:
        by_cat: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_cat[str(r.get("category", r["prediction"]))].append(r)
        alloc = allocate({c: len(v) for c, v in by_cat.items()}, args.n, args.min_size)
        picked = [(c, r) for c, k in sorted(alloc.items(), key=lambda kv: -len(by_cat[kv[0]]))
                  for r in rng.sample(by_cat[c], k)]
        sizes = ", ".join(f"{c} {len(by_cat[c])}" for c in sorted(by_cat, key=lambda c: -len(by_cat[c])))
        print(f"-- category sizes (unlabelled): {sizes}", file=sys.stderr)

    for cat, r in picked:
        text = r["input"] if isinstance(r["input"], str) else str(r["input"])
        print(f"{cat[:40]:40}  {r['id']}  {r['prediction']}  {text[:110]}")
    print(" ".join(r["id"] for _, r in picked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
