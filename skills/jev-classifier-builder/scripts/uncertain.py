#!/usr/bin/env python3
"""
List the pool records a classifier is least sure about.

    python scripts/uncertain.py RESULTS.jsonl [--labels WORK/labels.jsonl] [-n 20] [--dedupe 0.6]

RESULTS.jsonl is the output of `jev_classifier.py run ... -o`. The margin is how
far a record is from flipping: with a stored "decision" threshold, twice the
distance of that class's probability from the threshold; otherwise the top
class probability minus the second. Records already in --labels are skipped.
Prints margin, id, the prediction and the runner-up class, text.

With --by disagreement (ensemble outputs), records where the members disagree
come first, most evenly split first, then by margin; the member votes are
printed too.

Repeats are skipped, so each pick teaches something new:
  --per-pair K   at most K records per confusion (unordered pair of top two
                 classes). Default 2 when there are more than two classes,
                 off for binary tasks; 0 turns it off.
  --dedupe J     a record whose word overlap (Jaccard) with an already-listed
                 or already-labelled record is at least J (default 0.6; 0 off).
Unreadable lines (a file still being written) are skipped and counted.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import read_jsonl, read_jsonl_lenient

WORD_RE = re.compile(r"[a-z0-9']+")


def margin(record: dict) -> tuple[float, list[tuple[str, float]]]:
    """(margin, [prediction, runner-up]). Uses the result's own "margin", which
    honours a stored decision threshold, when present."""
    probs = record.get("class_probabilities") or record.get("probabilities") or {}
    pred = str(record.get("prediction"))
    first = (pred, probs.get(pred, 0.0)) if pred in probs else None
    rest = sorted(((c, p) for c, p in probs.items() if first is None or c != pred), key=lambda kv: -kv[1])
    top = ([first] if first else []) + rest
    top = (top + [("-", 0.0), ("-", 0.0)])[:2]
    m = record["margin"] if isinstance(record.get("margin"), (int, float)) else abs(top[0][1] - top[1][1])
    return m, top


def words(text: object) -> frozenset[str]:
    return frozenset(WORD_RE.findall(str(text).lower()))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("--labels", type=Path, help="skip records already labelled")
    parser.add_argument("-n", type=int, default=20)
    parser.add_argument("--by", choices=["margin", "disagreement"], default="margin")
    parser.add_argument("--dedupe", type=float, default=0.6, help="word-overlap threshold for near-duplicates")
    parser.add_argument("--per-pair", type=int, help="max records per top-two class pair (default: 2 if >2 classes)")
    args = parser.parse_args()

    labelled = read_jsonl(args.labels) if args.labels and args.labels.exists() else []
    owned = {r["id"] for r in labelled}
    all_rows, bad = read_jsonl_lenient(args.results)
    rows = [r for r in all_rows if "id" in r and "error" not in r and r["id"] not in owned]
    failed = sum(1 for r in all_rows if "error" in r)
    if args.by == "disagreement" and not any("member_predictions" in r for r in rows):
        sys.exit("--by disagreement needs ensemble results (member_predictions)")

    def split(r: dict) -> float:
        votes = r.get("member_predictions") or []
        return max(votes.count(v) for v in votes) / len(votes) if votes else 1.0

    key = (lambda t: (split(t[2]), t[0])) if args.by == "disagreement" else (lambda t: t[0])
    scored = sorted((margin(r) + (r,) for r in rows), key=key)

    n_classes = len({c for r in rows for c in (r.get("class_probabilities") or r.get("probabilities") or {})})
    per_pair = args.per_pair if args.per_pair is not None else (2 if n_classes > 2 else 0)
    seen = [words(r["text"]) for r in labelled]
    pairs: dict[frozenset[str], int] = {}
    shown = dupes = capped = 0
    for m, top, r in scored:
        if shown >= args.n:
            break
        pair = frozenset((top[0][0], top[1][0]))
        if per_pair and pairs.get(pair, 0) >= per_pair:
            capped += 1
            continue
        w = words(r["input"])
        if args.dedupe > 0 and any(jaccard(w, s) >= args.dedupe for s in seen):
            dupes += 1
            continue
        seen.append(w)
        pairs[pair] = pairs.get(pair, 0) + 1
        shown += 1
        text = r["input"] if isinstance(r["input"], str) else str(r["input"])
        votes = f"  [{','.join(r['member_predictions'])}]" if args.by == "disagreement" else ""
        print(f"{m:.3f}  {r['id']}  {top[0][0]} {top[0][1]:.2f} | {top[1][0]} {top[1][1]:.2f}{votes}  {text[:120]}")

    if capped:
        print(f"-- skipped {capped} records past {per_pair} per confusion pair (--per-pair)", file=sys.stderr)
    if dupes:
        print(f"-- skipped {dupes} near-duplicates of listed or labelled records", file=sys.stderr)
    if args.by == "disagreement":
        print(f"-- members disagree on {sum(split(r) < 1 for r in rows)} unlabelled records", file=sys.stderr)
    below = {t: sum(1 for m, _, _ in scored if m < t) for t in (0.1, 0.3, 0.5)}
    print(f"-- {len(rows)} unlabelled records; margin <0.1: {below[0.1]}, <0.3: {below[0.3]}, <0.5: {below[0.5]}"
          + (f"; {failed} failed calls, rerun to fill them" if failed else "")
          + (f"; {bad} unreadable lines skipped (file still being written?)" if bad else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
