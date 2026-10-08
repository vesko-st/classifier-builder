#!/usr/bin/env python3
"""
Report pool text copied into a classifier definition.

    python scripts/copy_check.py CLASSIFIER.json --pool WORK/pool.jsonl [-n 6]

Flags every run of N or more consecutive words (default 6) that the definition
(instructions, rules, option and question descriptions) shares with any pool
record, and every quoted passage of 4 or more words that appears in a pool
record. Prints the shared passage and the record id. Exit status 1 when
anything is found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import read_jsonl

WORD_RE = re.compile(r"[a-z0-9']+")
QUOTE_RE = re.compile(r"[\"“‘]([^\"”’]{3,200})[\"”’]")
SKIP_KEYS = {"map", "model", "version", "name", "type", "state_template", "decision"}


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            if key not in SKIP_KEYS:
                yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower().replace("’", "'"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("classifier")
    parser.add_argument("--pool", required=True)
    parser.add_argument("-n", type=int, default=6, help="shared word-run length that counts as a copy")
    args = parser.parse_args()

    with open(args.classifier) as f:
        texts = list(strings(json.load(f)))
    n = args.n
    index: dict[tuple[str, ...], str] = {}
    pool = read_jsonl(Path(args.pool))
    for record in pool:
        w = words(record["text"])
        for i in range(len(w) - n + 1):
            index.setdefault(tuple(w[i:i + n]), record["id"])

    found = []
    seen = set()
    for text in texts:
        w = words(text)
        i = 0
        while i <= len(w) - n:
            rid = index.get(tuple(w[i:i + n]))
            if rid is None:
                i += 1
                continue
            j = i + n
            while j < len(w) and index.get(tuple(w[j - n + 1:j + 1])) is not None:
                j += 1
            passage = " ".join(w[i:j])
            if passage not in seen:
                seen.add(passage)
                found.append((rid, passage))
            i = j
    pool_text = [(r["id"], " ".join(words(r["text"]))) for r in pool]
    for text in texts:
        for quote in QUOTE_RE.findall(text):
            q = " ".join(words(quote))
            if len(q.split()) < 4 or q in seen:
                continue
            hit = next((rid for rid, t in pool_text if f" {q} " in f" {t} "), None)
            if hit:
                seen.add(q)
                found.append((hit, q))

    for rid, passage in found:
        print(f"{rid}\t{passage}")
    print(f"{len(found)} copied passage(s)", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
