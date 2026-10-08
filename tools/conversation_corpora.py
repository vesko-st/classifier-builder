"""Loaders for the three conversation tasks, from the corpora's primary sources.

Persuasion for Good (Wang et al., ACL 2019) gives persuasion_strategy (the
strategy of one persuader utterance, with the dialogue so far) and
persuasion_donation (whether the persuadee donated more than $0).
CraigslistBargain (He et al., 2018) gives craigslist_deal (whether a negotiation
ended in a deal), built from the raw CodaLab ``parsed.json``: the Hugging Face
copy drops the offer and accept events that carry the outcome, and the context
here keeps message turns only.

Raw files are downloaded once into data/raw/.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from common import DATA_DIR

RAW_DIR = DATA_DIR / "raw"

PERSUASION_BASE = "https://raw.githubusercontent.com/ohyj1002/persuasionforgood/master/data"
PERSUASION_FILES = {
    "full_dialog.csv": f"{PERSUASION_BASE}/FullData/full_dialog.csv",
    "full_info.csv": f"{PERSUASION_BASE}/FullData/full_info.csv",
    "300_dialog.xlsx": f"{PERSUASION_BASE}/AnnotatedData/300_dialog.xlsx",
}
CRAIGSLIST = {
    "train": "https://worksheets.codalab.org/rest/bundles/0xd34bbbc5fb3b4fccbd19e10756ca8dd7/contents/blob/parsed.json",
    "validation": "https://worksheets.codalab.org/rest/bundles/0x15c4160b43d44ee3a8386cca98da138c/contents/blob/parsed.json",
}

# Strategy labels rarer than this among persuader utterances are folded into "other".
LABEL_FLOOR = 100
CONTEXT_TURNS = 12


@dataclass
class Item:
    context: str
    question: str
    gold: Any
    meta: dict[str, Any] = field(default_factory=dict)


def _fetch(url: str, dest: Path, retries: int = 4) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    print(f"  downloading {url}")
    last: Exception | None = None
    for attempt in range(retries):
        try:
            tmp = dest.with_suffix(dest.suffix + ".part")
            with httpx.stream("GET", url, follow_redirects=True, timeout=180.0) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            tmp.replace(dest)
            return dest
        except Exception as exc:  # CodaLab is flaky; back off and retry
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url} after {retries} tries: {last}")


def _persuasion_files() -> dict[str, Path]:
    return {name: _fetch(url, RAW_DIR / "persuasion" / name) for name, url in PERSUASION_FILES.items()}


def _role_name(b4) -> str:
    return "Persuader" if int(b4) == 0 else "Persuadee"


def load_strategy() -> tuple[list[Item], dict]:
    import pandas as pd

    df = pd.read_excel(_persuasion_files()["300_dialog.xlsx"])
    df = df.sort_values(["B2", "Turn", "Unit"], kind="stable").reset_index(drop=True)

    er = df[(df["B4"] == 0) & df["er_label_1"].notna()]["er_label_1"].astype(str)
    kept = {lab for lab, c in er.value_counts().items() if c >= LABEL_FLOOR}
    kept.add("other")

    items: list[Item] = []
    dist: dict[str, int] = defaultdict(int)
    for b2, g in df.groupby("B2", sort=False):
        history: list[str] = []
        for _, row in g.iterrows():
            unit = str(row["Unit"]).strip()
            lab = row["er_label_1"]
            if int(row["B4"]) == 0 and pd.notna(lab) and unit:
                gold = str(lab) if str(lab) in kept else "other"
                ctx = "\n".join(history[-CONTEXT_TURNS:]) or "(start of conversation)"
                items.append(Item(
                    context=f"Charity-donation dialogue so far:\n{ctx}",
                    question=(
                        f'The persuader then says: "{unit}". '
                        "Which single persuasion strategy or dialogue act best describes it?"
                    ),
                    gold=gold,
                    meta={"dialogue_id": str(b2), "raw_label": str(lab)},
                ))
                dist[gold] += 1
            if unit:
                history.append(f"{_role_name(row['B4'])}: {unit}")
    return items, {"n": len(items), "labels": sorted(kept), "label_dist": dict(dist)}


def load_donation() -> tuple[list[Item], dict]:
    import pandas as pd

    files = _persuasion_files()
    info = pd.read_csv(files["full_info.csv"])
    dialog = pd.read_csv(files["full_dialog.csv"])

    donations: dict[str, float] = {}
    for _, r in info.iterrows():
        if int(r["B4"]) == 1:  # the persuadee row carries the actual donation in B6
            try:
                donations[str(r["B2"])] = float(r["B6"])
            except (TypeError, ValueError):
                continue

    items: list[Item] = []
    for b2, g in dialog.groupby("B2", sort=False):
        if str(b2) not in donations:
            continue
        lines = [f"{_role_name(row['B4'])}: {str(row['Unit']).strip()}"
                 for _, row in g.iterrows() if str(row["Unit"]).strip()]
        if not lines:
            continue
        items.append(Item(
            context="Charity-donation dialogue:\n" + "\n".join(lines),
            question="By the end of this conversation, did the persuadee agree to donate a positive amount?",
            gold=donations[str(b2)] > 0,
            meta={"dialogue_id": str(b2), "donation": donations[str(b2)]},
        ))
    return items, {"n": len(items)}


def _dialogue(d: dict) -> tuple[str, dict]:
    kbs = d["scenario"]["kbs"]
    role_of = {i: kbs[i]["personal"].get("Role", f"agent{i}") for i in range(len(kbs))}
    item0 = kbs[0]["item"]
    title = item0.get("Title")
    if isinstance(title, list):
        title = ", ".join(str(t) for t in title)
    category = item0.get("Category")
    if isinstance(category, list):
        category = category[0] if category else ""

    lines = []
    for e in d["events"]:
        if e.get("action") != "message":
            continue
        text = e.get("data")
        if not isinstance(text, str) or not text.strip():
            continue
        who = role_of.get(e.get("agent"), "agent").capitalize()
        lines.append(f"{who}: {text.strip()}")
    return "\n".join(lines), {"listing_price": item0.get("Price"), "title": title, "category": category}


def load_deal(split: str = "train") -> tuple[list[Item], dict]:
    path = _fetch(CRAIGSLIST[split], RAW_DIR / "craigslist" / f"{split}.json")
    items: list[Item] = []
    for d in json.loads(path.read_text()):
        transcript, meta = _dialogue(d)
        if not transcript:
            continue
        header = (f"Item for sale: {meta['title']} (category: {meta['category']}). "
                  f"Listing price: ${meta['listing_price']}.")
        items.append(Item(
            context=f"{header}\n\nConversation:\n{transcript}",
            question="Based on this conversation, did the buyer and seller reach a deal?",
            gold=(d.get("outcome") or {}).get("reward") == 1,
            meta=meta,
        ))
    return items, {"n": len(items)}
