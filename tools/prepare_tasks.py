#!/usr/bin/env python3
"""
Download the pilot datasets and write fixed splits.

For each task:
    data/<task>/pool.jsonl              {"id", "text"}: what the builder sees
    data/<task>/private/pool.jsonl      {"id", "text", "label"}: bought through the oracle
    data/<task>/private/val.jsonl       harness only: learning curves
    data/<task>/private/test.jsonl      harness only: final scores

Splits are stratified by label, duplicates (case/whitespace-insensitive) are
removed across all splits, and the seed is fixed so reruns are identical.
Banking77 and tweet_hate use the whole official test split (3,080 and 2,970
records), as published results do. tweet_hate_fullpool is tweet_hate with the
whole training split as the pool. tweet_hate_testsplit draws pool, validation
and test all from the official test split, so they share one distribution; its
scores are not comparable with published numbers.

The conversation tasks load their corpora through tools/conversation_corpora.py,
which downloads the raw files into data/raw/. persuasion_strategy is split by dialogue, because messages
from one dialogue share context; persuasion_donation has too few dialogues for
the standard sizes; craigslist_deal tests on the corpus's validation split.

    python tools/prepare_tasks.py [task ...]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
import sys
from collections import defaultdict
from typing import Any, Callable

import httpx

from common import ROOT, TASKS_DIR, DATA_DIR, private_dir, write_jsonl

SEED = 20260923
SIZES = {"pool": 1000, "val": 200, "test": 400}
BANKING77_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/{split}.csv"
PERSUADER_MESSAGE_RE = re.compile(r'^The persuader then says: "(.*)"\. Which single', re.DOTALL)

Record = dict  # {"text": str, "label": str}


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def banking77() -> dict[str, list[Record]]:
    out = {}
    for split in ("train", "test"):
        resp = httpx.get(BANKING77_URL.format(split=split), timeout=60, follow_redirects=True)
        resp.raise_for_status()
        rows = csv.DictReader(io.StringIO(resp.text))
        out[split] = [{"text": r["text"].strip(), "label": r["category"]} for r in rows]
    return out


def banking77_routing() -> dict[str, list[Record]]:
    mapping = json.loads((TASKS_DIR / "banking77_routing" / "private" / "mapping.json").read_text())
    team_of = {intent: team for team, intents in mapping.items() for intent in intents}
    sources = banking77()
    intents = {r["label"] for rows in sources.values() for r in rows}
    missing, extra = intents - team_of.keys(), team_of.keys() - intents
    if missing or extra or len(team_of) != sum(len(v) for v in mapping.values()):
        sys.exit(f"routing mapping must cover each intent once; missing={missing} extra={extra}")
    return {
        split: [{"text": r["text"], "label": team_of[r["label"]], "intent": r["label"]} for r in rows]
        for split, rows in sources.items()
    }


def tweet_hate() -> dict[str, list[Record]]:
    from datasets import load_dataset

    ds = load_dataset("cardiffnlp/tweet_eval", "hate")
    names = ds["train"].features["label"].names  # ['non-hate', 'hate']
    rename = {"non-hate": "not_hate", "hate": "hate"}
    return {
        split: [{"text": r["text"].strip(), "label": rename[names[r["label"]]]} for r in ds[split]]
        for split in ("train", "validation", "test")
    }


def _sales_items(task: str, *args: Any) -> list[Any]:
    import conversation_corpora as corpora

    loader = {
        "persuasion_strategy": corpora.load_strategy,
        "persuasion_donation": corpora.load_donation,
        "craigslist_deal": corpora.load_deal,
    }[task]
    items, _ = loader(*args)
    return items


def persuasion_strategy() -> dict[str, list[Record]]:
    rows = []
    for item in _sales_items("persuasion_strategy"):
        match = PERSUADER_MESSAGE_RE.match(item.question)
        if not match:
            sys.exit(f"unexpected persuasion question format: {item.question[:120]!r}")
        rows.append({
            "text": f"{item.context}\n\nPersuader message to tag: {match.group(1)}",
            "label": item.gold,
            "group": item.meta["dialogue_id"],
        })
    return {"all": rows}


def persuasion_donation() -> dict[str, list[Record]]:
    return {"all": [{"text": item.context, "label": "donated" if item.gold else "not_donated"}
                    for item in _sales_items("persuasion_donation")]}


def craigslist_deal() -> dict[str, list[Record]]:
    return {split: [{"text": item.context, "label": "deal" if item.gold else "no_deal"}
                    for item in _sales_items("craigslist_deal", split)]
            for split in ("train", "validation")}


def grouped_split(rows: list[Record], sizes: dict[str, int], rng: random.Random) -> dict[str, list[Record]]:
    """Whole groups per split, filled in order until each reaches its size."""
    by_group: dict[str, list[Record]] = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)
    groups = sorted(by_group)
    rng.shuffle(groups)
    remaining = iter(groups)
    splits: dict[str, list[Record]] = {}
    for split, n in sizes.items():
        splits[split] = []
        while len(splits[split]) < n and (group := next(remaining, None)) is not None:
            splits[split].extend(dict(r) for r in by_group[group])
        rng.shuffle(splits[split])
    return splits


def stratified_sample(rows: list[Record], n: int, rng: random.Random) -> list[Record]:
    """Proportional allocation with largest remainders; every class keeps at least one row."""
    by_label: dict[str, list[Record]] = defaultdict(list)
    for r in rows:
        by_label[r["label"]].append(r)
    for group in by_label.values():
        rng.shuffle(group)
    total = len(rows)
    quotas = {k: n * len(v) / total for k, v in by_label.items()}
    alloc = {k: max(1, int(q)) for k, q in quotas.items()}
    by_remainder = sorted(quotas, key=lambda k: quotas[k] - int(quotas[k]), reverse=True)
    i = 0
    while sum(alloc.values()) < n:
        k = by_remainder[i % len(by_remainder)]
        if alloc[k] < len(by_label[k]):
            alloc[k] += 1
        i += 1
    picked = [r for k, group in by_label.items() for r in group[: alloc[k]]]
    rng.shuffle(picked)
    return picked[:n]


# task -> (loader, {split: source split(s) to draw from, in order})
TASKS: dict[str, tuple[Callable[[], dict[str, list[Record]]], dict[str, str]]] = {
    "banking77_intents": (banking77, {"test": "test", "pool": "train", "val": "train"}),
    "banking77_intents_fullpool": (banking77, {"test": "test", "val": "train", "pool": "train"}),
    "banking77_routing": (banking77_routing, {"test": "test", "pool": "train", "val": "train"}),
    "banking77_routing_fullpool": (banking77_routing, {"test": "test", "val": "train", "pool": "train"}),
    "tweet_hate": (tweet_hate, {"test": "test", "pool": "train", "val": "validation"}),
    "tweet_hate_fullpool": (tweet_hate, {"test": "test", "pool": "train", "val": "validation"}),
    "tweet_hate_testsplit": (tweet_hate, {"pool": "test", "val": "test", "test": "test"}),
    "persuasion_strategy": (persuasion_strategy, {"test": "all", "pool": "all", "val": "all"}),
    "persuasion_donation": (persuasion_donation, {"pool": "all", "val": "all", "test": "all"}),
    "craigslist_deal": (craigslist_deal, {"test": "validation", "pool": "train", "val": "train"}),
    "craigslist_deal_fullpool": (craigslist_deal, {"test": "validation", "val": "train", "pool": "train"}),
}
# Tasks whose test split is every record the earlier splits did not take.
REST_TEST = {"tweet_hate_testsplit", "persuasion_donation"}
# Tasks scored on the whole official test split (duplicates kept), so results
# are comparable with published numbers.
FULL_TEST = {"banking77_intents", "banking77_intents_fullpool", "banking77_routing", "banking77_routing_fullpool",
             "tweet_hate", "tweet_hate_fullpool", "craigslist_deal", "craigslist_deal_fullpool"}
# Tasks whose pool is the whole (deduplicated) source split rather than a sample;
# any validation split must come first in the plan so the pool takes the rest.
FULL_POOL = {"tweet_hate_fullpool", "banking77_intents_fullpool", "banking77_routing_fullpool",
             "craigslist_deal_fullpool"}
# Tasks split by whole groups (records carry a "group"), with their split sizes.
GROUPED = {"persuasion_strategy": {"test": 1500, "pool": 1000, "val": 200}}
TASK_SIZES = {"persuasion_donation": {"pool": 500, "val": 100}}
PREFIXES = {"banking77_intents": "bi", "banking77_intents_fullpool": "bif", "banking77_routing": "br", "banking77_routing_fullpool": "brf", "tweet_hate": "th", "tweet_hate_fullpool": "thf",
            "tweet_hate_testsplit": "tht", "persuasion_strategy": "ps", "persuasion_donation": "pd",
            "craigslist_deal": "cd", "craigslist_deal_fullpool": "cdf"}


def prepare(name: str) -> None:
    loader, plan = TASKS[name]
    sources = loader()
    rng = random.Random(f"{SEED}:{name}")
    sizes = {**SIZES, **TASK_SIZES.get(name, {})}
    seen: set[str] = set()
    splits: dict[str, list[Record]] = {}
    if name in GROUPED:
        splits = grouped_split(sources["all"], GROUPED[name], rng)
        plan = {}
    # Test first so duplicates of test texts never land in the pool or validation.
    for split, source in plan.items():
        if split == "test" and name in FULL_TEST:
            splits[split] = [dict(r) for r in sources[source]]
            seen |= {_norm(r["text"]) for r in splits[split]}
            continue
        candidates = []
        for r in sources[source]:
            key = _norm(r["text"])
            if r["text"] and key not in seen:
                seen.add(key)
                candidates.append(r)
        if (split == "pool" and name in FULL_POOL) or (split == "test" and name in REST_TEST):
            splits[split] = [dict(r) for r in candidates]
            rng.shuffle(splits[split])
            continue
        splits[split] = stratified_sample(candidates, sizes[split], rng)
        chosen = {_norm(r["text"]) for r in splits[split]}
        seen -= {_norm(r["text"]) for r in candidates} - chosen

    prefix = PREFIXES[name]
    for split, rows in splits.items():
        for i, r in enumerate(rows):
            r["id"] = f"{prefix}-{split}-{i:04d}"
        write_jsonl(private_dir(name) / f"{split}.jsonl", ({"id": r["id"], **{k: v for k, v in r.items() if k != "id"}} for r in rows))
    write_jsonl(DATA_DIR / name / "pool.jsonl", ({"id": r["id"], "text": r["text"]} for r in splits["pool"]))

    if name.startswith("banking77_intents"):
        classes = sorted({r["label"] for rows in sources.values() for r in rows}, key=str.lower)
        (TASKS_DIR / name / "classes.json").write_text(json.dumps({c: None for c in classes}, indent=2) + "\n")

    counts = {s: len(rows) for s, rows in splits.items()}
    n_labels = {s: len({r["label"] for r in rows}) for s, rows in splits.items()}
    print(f"{name}: sizes={counts} classes={n_labels}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", help=f"default: all of {', '.join(TASKS)}")
    names = parser.parse_args().tasks or list(TASKS)
    unknown = [n for n in names if n not in TASKS]
    if unknown:
        parser.error(f"unknown tasks: {unknown}")
    for name in names:
        prepare(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
