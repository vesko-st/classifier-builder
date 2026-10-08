#!/usr/bin/env python3
"""
Error analysis around the decision boundary, for building from labels.

    python tools/boundary.py band RESULTS.jsonl --labels L [--ids-file F] [--quantile 0.15] [--per-pair 6]
    python tools/boundary.py confident RESULTS.jsonl --labels L [--ids-file F] [--min-margin 0.6] [-n 30]
    python tools/boundary.py compare OLD.jsonl NEW.jsonl --labels L [--ids-file F]

RESULTS are outputs of `jev_classifier.py run ... -o`; --labels gives the gold
labels and --ids-file restricts everything to a subset (e.g. the building set).
The margin is the one tools/uncertain.py uses: how far a record is from flipping.

band       The lowest-margin records (the --quantile share of the subset), correct
           and wrong together, grouped by the unordered pair of their top two
           classes. Per pair: how many records, how the gold labels split between
           the two classes, how many the classifier gets right, then up to
           --per-pair records with gold, prediction, margin and text.
confident  Errors with margin >= --min-margin. For each, the most similar record
           in the subset (word overlap) whose gold label is the class predicted;
           a high overlap means the labels themselves disagree on near-identical
           inputs.
compare    What a revision changed, from OLD's point of view: records fixed and
           broken, split by OLD's margin band, accuracy and macro-F1 before and
           after, and a noise check. A revision whose fixes minus breaks is not
           above 2 * sqrt(fixes + breaks) is within noise.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from common import read_jsonl, read_jsonl_lenient
from uncertain import jaccard, margin, words

BANDS = [(0.0, 0.2, "margin <0.2"), (0.2, 0.6, "0.2-0.6"), (0.6, 9.0, "margin >=0.6")]


def load(results: Path, labels: Path, ids_file: Path | None) -> tuple[dict[str, dict], dict[str, str]]:
    gold = {r["id"]: str(r["label"]) for r in read_jsonl(labels) if "label" in r}
    keep = set(ids_file.read_text().split()) if ids_file else None
    rows, _ = read_jsonl_lenient(results)
    out = {r["id"]: r for r in rows
           if "id" in r and "error" not in r and r["id"] in gold and (keep is None or r["id"] in keep)}
    return out, gold


def scores(rows: dict[str, dict], gold: dict[str, str]) -> tuple[float, float]:
    ids = list(rows)
    if not ids:
        return 0.0, 0.0
    acc = sum(str(rows[i].get("prediction")) == gold[i] for i in ids) / len(ids)
    f1s = []
    for c in sorted({gold[i] for i in ids}):
        tp = sum(gold[i] == c and str(rows[i].get("prediction")) == c for i in ids)
        fp = sum(gold[i] != c and str(rows[i].get("prediction")) == c for i in ids)
        fn = sum(gold[i] == c and str(rows[i].get("prediction")) != c for i in ids)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return acc, sum(f1s) / len(f1s)


def text_of(r: dict) -> str:
    t = r.get("input")
    return (t if isinstance(t, str) else str(t)).replace("\n", " ")


def cmd_band(args) -> None:
    rows, gold = load(args.results, args.labels, args.ids_file)
    scored = sorted((margin(r) + (r,) for r in rows.values()), key=lambda t: t[0])
    k = max(1, round(args.quantile * len(scored)))
    band = scored[:k]
    groups: dict[frozenset, list] = {}
    for m, top, r in band:
        groups.setdefault(frozenset((top[0][0], top[1][0])), []).append((m, top, r))
    right = sum(str(r.get("prediction")) == gold[r["id"]] for _, _, r in band)
    print(f"band: lowest-margin {k} of {len(scored)} records (margin <= {band[-1][0]:.3f}); "
          f"{right} right, {k - right} wrong; {len(groups)} class pairs\n")
    for pair, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        a, b = sorted(pair)
        ga = sum(gold[r["id"]] == a for _, _, r in items)
        gb = sum(gold[r["id"]] == b for _, _, r in items)
        ok = sum(str(r.get("prediction")) == gold[r["id"]] for _, _, r in items)
        print(f"== {a} | {b}: {len(items)} records, gold {a} {ga} / {b} {gb} / other {len(items) - ga - gb}, "
              f"{ok} right")
        for m, top, r in items[: args.per_pair]:
            mark = "ok " if str(r.get("prediction")) == gold[r["id"]] else "ERR"
            print(f"  {mark} {m:.3f} {r['id']} gold={gold[r['id']]} pred={r.get('prediction')}  {text_of(r)[:args.width]}")
        print()


def cmd_confident(args) -> None:
    rows, gold = load(args.results, args.labels, args.ids_file)
    vocab = {i: words(text_of(r)) for i, r in rows.items()}
    errs = sorted(((margin(r)[0], r) for r in rows.values()
                   if str(r.get("prediction")) != gold[r["id"]] and margin(r)[0] >= args.min_margin),
                  key=lambda t: -t[0])
    noisy = 0
    for m, r in errs[: args.n]:
        pred = str(r.get("prediction"))
        twins = [(jaccard(vocab[r["id"]], vocab[j]), j) for j in rows if j != r["id"] and gold[j] == pred]
        sim, twin = max(twins, default=(0.0, None))
        flag = "LABELS DISAGREE" if sim >= args.dup else ""
        noisy += bool(flag)
        print(f"{m:.3f} {r['id']} gold={gold[r['id']]} pred={pred}  {text_of(r)[:args.width]}")
        if twin:
            print(f"      nearest gold={pred}: {sim:.2f} {twin}  {text_of(rows[twin])[:args.width]}  {flag}")
    print(f"\n-- {len(errs)} errors with margin >= {args.min_margin} of {len(rows)} records; "
          f"listed {min(args.n, len(errs))}, of which {noisy} have a near-identical record "
          f"(overlap >= {args.dup}) labelled the other way", file=sys.stderr)


def cmd_compare(args) -> None:
    old, gold = load(args.old, args.labels, args.ids_file)
    new, _ = load(args.new, args.labels, args.ids_file)
    common = [i for i in old if i in new]
    old = {i: old[i] for i in common}
    new = {i: new[i] for i in common}
    print(f"{len(common)} records in both\n")
    print(f"{'OLD margin':14} {'records':>8} {'fixed':>6} {'broken':>7}")
    tf = tb = 0
    for lo, hi, name in BANDS:
        ids = [i for i in common if lo <= margin(old[i])[0] < hi]
        f = sum(str(old[i].get("prediction")) != gold[i] and str(new[i].get("prediction")) == gold[i] for i in ids)
        b = sum(str(old[i].get("prediction")) == gold[i] and str(new[i].get("prediction")) != gold[i] for i in ids)
        tf, tb = tf + f, tb + b
        print(f"{name:14} {len(ids):8d} {f:6d} {b:7d}")
    oa, of = scores(old, gold)
    na, nf = scores(new, gold)
    noise = 2 * math.sqrt(tf + tb)
    verdict = "ABOVE NOISE" if tf - tb > noise else "WITHIN NOISE"
    print(f"\naccuracy {oa:.4f} -> {na:.4f}, macro-F1 {of:.4f} -> {nf:.4f}")
    print(f"fixed {tf}, broken {tb}: net {tf - tb:+d} vs noise 2*sqrt({tf + tb}) = {noise:.1f} -> {verdict}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("band", "confident", "compare"):
        p = sub.add_parser(name)
        if name == "compare":
            p.add_argument("old", type=Path)
            p.add_argument("new", type=Path)
        else:
            p.add_argument("results", type=Path)
        p.add_argument("--labels", type=Path, required=True)
        p.add_argument("--ids-file", type=Path, help="restrict to these ids (e.g. the building set)")
        p.add_argument("--width", type=int, default=160, help="characters of text to show")
        if name == "band":
            p.add_argument("--quantile", type=float, default=0.15)
            p.add_argument("--per-pair", type=int, default=6)
        if name == "confident":
            p.add_argument("--min-margin", type=float, default=0.6)
            p.add_argument("-n", type=int, default=30)
            p.add_argument("--dup", type=float, default=0.5, help="overlap that counts as near-identical")
    args = parser.parse_args()
    {"band": cmd_band, "confident": cmd_confident, "compare": cmd_compare}[args.cmd](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
