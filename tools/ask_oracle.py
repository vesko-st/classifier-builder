#!/usr/bin/env python3
"""
The simulated user: the only way a builder learns about the labels.

    # Buy gold labels for pool records: 2 points each (records already bought are free)
    python tools/ask_oracle.py RUN_DIR --token T label br-pool-0001 br-pool-0042

    # Tag labels to score them apart later (tools/score.py --tag check)
    python tools/ask_oracle.py RUN_DIR --token T label --tag check br-pool-0007 br-pool-0310

    # Ask a question: answered by a separate model, scored 2, 5 or 10 points
    python tools/ask_oracle.py RUN_DIR --token T ask "Should PIN changes go to the cards team?"

    # Points spent and remaining
    python tools/ask_oracle.py RUN_DIR status

The token comes from tools/claim_run.py (or set RUN_TOKEN).

Question costs, per part (a message asking for verdicts on several cases is
several parts; examples that only illustrate one question are not):
     2  about one record or message type, or a yes/no fact
     5  a targeted policy question about a group of messages or a rule
    10  open-ended, needing a view across many examples (answered in summary)
A message costs the sum of its parts, and at least 2 per record whose label it reveals.

Requests that would exceed the budget are refused. Every request is appended to
RUN_DIR/oracle_log.jsonl; bought labels, and labels an answer reveals for pool
ids it names (tag "revealed"), are appended to RUN_DIR/labels.jsonl.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

from common import (
    OwnershipError,
    TASKS_DIR,
    check_owner,
    guideline,
    load_env,
    private_dir,
    read_jsonl,
    run_lock,
    token_from,
)

ORACLE_MODEL = "claude-opus-5-5"
# 1: Sonnet 5, answering from the guideline and the 150-record sample only.
# 2: Opus 5.5, which may explore every labelled pool record through tools before answering.
# 3: as 2, but an answer given before any search is sent back, so every answer rests on a search of the labels.
# 4: Opus 5.5 answering from the guideline and a fixed note on how all the labels apply it
#    (tools/infer_policy.py), without searching per question.
ORACLE_VERSION = 4
LABEL_COST = 2
QUESTION_COSTS = (2, 5, 10)
SAMPLE_SIZE = 150
MAX_QUESTION_CHARS = 1500
LIST_LIMIT = 25
SNIPPET_CHARS = 400
ID_RE = re.compile(r"\b[a-z]{2,4}-(?:pool|val|test)-\d{4}\b")

SYSTEM = """\
You are the domain expert who owns a text classification task. An engineer is \
building an automatic classifier for it and asks you questions. You know the \
labelling policy (below) and can see labelled examples.

How to answer:
- Answer truthfully and concisely, the way a busy expert would: answer what was \
asked, not more. Do not recite the whole policy, list every class boundary, or \
volunteer rules the question did not ask about.
- Ground answers in the policy and the labelled examples. If they conflict, the \
labels win. If you are unsure, say so.
- Below the policy is a note on how your labels actually apply it, written from \
all of them. Treat it as your own knowledge of your data: where it differs from \
the written policy, the note is right, because it describes the labels. The \
sample is only for orientation. Do not mention the note.
- Only reveal the label of a record, or cite example records, if the question \
asks for it. Unrequested examples are billed to the engineer.
- Speak in plain terms. Do not mention the policy document, how it is \
organised, or internal names the engineer has not seen (anything beyond the \
task's class names and record ids).

- For open-ended questions, answer at summary level in at most about 100 \
words: the main points only, no exhaustive lists. The engineer can follow up.

Then price the message. Split it into its separate questions: every case, \
phrasing or class the engineer wants a separate verdict on is its own part, even \
when they are bundled in one sentence or a numbered list. Examples given only to \
illustrate one question, where your answer is a single rule, are not extra \
parts; if you answer by ruling on each example separately, each is a part. \
Price each part:
- 2: about a single record or message type, or a yes/no fact.
- 5: a targeted policy question about a group of messages or a rule.
- 10: open-ended, or needing a view across many examples (e.g. "what are the \
main confusions", "describe each class", "what rules am I missing").
Also count how many distinct records' labels your answer reveals.

Reply with only a JSON object:
{"answer": "...", "parts": [{"question": "short paraphrase", "cost": 2 | 5 | 10}, ...], "labels_revealed": <int>}"""


class OracleError(RuntimeError):
    pass


def _load_run(run_dir: Path) -> dict:
    path = run_dir / "run.json"
    if not path.exists():
        raise OracleError(f"{path} not found; create the run with tools/new_run.py")
    return json.loads(path.read_text())


def _log(run_dir: Path) -> list[dict]:
    path = run_dir / "oracle_log.jsonl"
    return read_jsonl(path) if path.exists() else []


def spent(run_dir: Path) -> int:
    return sum(entry["cost"] for entry in _log(run_dir))


def _append(path: Path, rows: list[dict]) -> None:
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _check_budget(run: dict, run_dir: Path, cost: int) -> None:
    remaining = run["budget"] - spent(run_dir)
    if cost > remaining:
        raise OracleError(f"request costs {cost} points but only {remaining} remain")


def buy_labels(run_dir: Path, ids: list[str], tag: str | None = None) -> dict:
    run = _load_run(run_dir)
    pool = {r["id"]: r for r in read_jsonl(private_dir(run["task"]) / "pool.jsonl")}
    unknown = [i for i in ids if i not in pool]
    if unknown:
        raise OracleError(f"not pool ids: {unknown}")
    with run_lock(run_dir):
        owned = {r["id"] for r in read_jsonl(run_dir / "labels.jsonl")}
        new = list(dict.fromkeys(i for i in ids if i not in owned))
        cost = LABEL_COST * len(new)
        _check_budget(run, run_dir, cost)

        rows = [{"id": i, "text": pool[i]["text"], "label": pool[i]["label"], **({"tag": tag} if tag else {})}
                for i in new]
        _append(run_dir / "labels.jsonl", rows)
        _append(run_dir / "oracle_log.jsonl", [{
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "kind": "label",
            "ids": new,
            "already_owned": [i for i in ids if i in owned],
            "tag": tag,
            "cost": cost,
        }])
    return {
        "labels": {i: pool[i]["label"] for i in dict.fromkeys(ids)},
        "cost": cost,
        "spent": spent(run_dir),
        "budget": run["budget"],
    }


def _render_record(r: dict) -> str:
    return f"[{r['id']}] label={r['label']}\n  {r['text']}"


def _oracle_context(task: str, question: str) -> str:
    public = json.loads((TASKS_DIR / task / "task.json").read_text())
    extra_files = sorted((TASKS_DIR / task / "private").glob("*.json"))
    pool = read_jsonl(private_dir(task) / "pool.jsonl")
    by_id = {r["id"]: r for r in pool}

    mentioned = [by_id[i] for i in dict.fromkeys(ID_RE.findall(question)) if i in by_id]
    rng = random.Random(f"oracle-sample:{task}")
    sample = rng.sample(pool, min(SAMPLE_SIZE, len(pool)))

    note = TASKS_DIR / task / "private" / "applied_policy.md"
    if not note.exists():
        raise OracleError(f"{note} not found; write it with tools/infer_policy.py {task}")
    parts = [
        "# Task as the engineer knows it\n" + json.dumps(public, indent=2),
        "# Labelling policy (private)\n" + guideline(task),
        "# How the labels apply the policy (private)\n" + note.read_text(),
    ]
    for f in extra_files:
        # Identifiers like "beneficiary_not_allowed" get echoed back verbatim;
        # plain words keep answers in the user's vocabulary.
        plain = re.sub(r'"([A-Za-z_?]+)"', lambda m: '"' + m.group(1).replace("_", " ").rstrip("?") + '"', f.read_text())
        parts.append(f"# {f.stem} (private)\n{plain}")
    if mentioned:
        parts.append("# Records the question mentions\n" + "\n".join(map(_render_record, mentioned)))
    parts.append("# Labelled sample of the pool\n" + "\n".join(map(_render_record, sample)))
    return "\n\n".join(parts)


TOOLS = [
    {
        "name": "search_records",
        "description": (
            "Search every labelled pool record. Matches a case-insensitive regular expression against the "
            "text, optionally only records with one label. Returns the number of matches, their label "
            f"counts, and up to {LIST_LIMIT} matching records (text shortened)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "regular expression; empty matches everything"},
                "label": {"type": "string", "description": "only records with this label"},
                "offset": {"type": "integer", "description": "skip this many matches (for paging)"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "label_counts",
        "description": "How many pool records carry each label.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_records",
        "description": "Full text and label of pool records by id.",
        "input_schema": {
            "type": "object",
            "properties": {"ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["ids"],
        },
    },
]


def _snippet(r: dict) -> str:
    text = r["text"] if len(r["text"]) <= SNIPPET_CHARS else r["text"][:SNIPPET_CHARS] + " …"
    return f"[{r['id']}] label={r['label']}\n  {text}"


def _run_tool(pool: list[dict], name: str, args: dict) -> str:
    if name == "label_counts":
        counts: dict[str, int] = {}
        for r in pool:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
        return json.dumps(dict(sorted(counts.items(), key=lambda kv: -kv[1])))
    if name == "get_records":
        by_id = {r["id"]: r for r in pool}
        found = [by_id[i] for i in args.get("ids", [])[:LIST_LIMIT] if i in by_id]
        return "\n".join(map(_render_record, found)) or "no such ids"
    if name == "search_records":
        pattern = args.get("pattern", "")
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            rx = re.compile(re.escape(pattern), re.IGNORECASE)
        hits = [r for r in pool if (not args.get("label") or r["label"] == args["label"]) and rx.search(r["text"])]
        counts = {}
        for r in hits:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
        offset = max(0, int(args.get("offset") or 0))
        shown = hits[offset: offset + LIST_LIMIT]
        head = f"{len(hits)} matches; labels: {json.dumps(dict(sorted(counts.items(), key=lambda kv: -kv[1])))}"
        return head + ("\n" + "\n".join(map(_snippet, shown)) if shown else "")
    return f"unknown tool {name}"


def _answer(client: Any, system: str, question: str) -> tuple[str, dict]:
    msg = client.messages.create(
        model=ORACLE_MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    usage = {"input": msg.usage.input_tokens, "output": msg.usage.output_tokens}
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text"), usage


def _parse_reply(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise OracleError(f"oracle reply is not JSON: {text[:300]}")
    reply = json.loads(match.group(0))
    parts = reply.get("parts")
    if (
        not isinstance(reply.get("answer"), str)
        or not isinstance(parts, list)
        or not parts
        or not all(isinstance(p, dict) and p.get("cost") in QUESTION_COSTS for p in parts)
    ):
        raise OracleError(f"oracle reply has the wrong shape: {reply}")
    reply["labels_revealed"] = max(0, int(reply.get("labels_revealed") or 0))
    return reply


def ask(run_dir: Path, question: str) -> dict:
    from anthropic import Anthropic

    run = _load_run(run_dir)
    remaining = run["budget"] - spent(run_dir)
    if remaining < min(QUESTION_COSTS):
        raise OracleError(f"only {remaining} points remain")
    if len(question) > MAX_QUESTION_CHARS:
        raise OracleError(f"question is {len(question)} characters; the limit is {MAX_QUESTION_CHARS}")

    load_env()
    client = Anthropic()
    text, usage = _answer(client, SYSTEM + "\n\n" + _oracle_context(run["task"], question), question)
    reply = _parse_reply(text)
    parts_cost = sum(p["cost"] for p in reply["parts"])
    cost = max(parts_cost, LABEL_COST * reply["labels_revealed"])
    # The answer is already generated; an over-budget question is refused and
    # not charged, so the builder never sees an answer it couldn't afford.
    with run_lock(run_dir):
        _check_budget(run, run_dir, cost)
        # Revealed labels are paid for (2 points each), so record them like bought ones.
        pool = {r["id"]: r for r in read_jsonl(private_dir(run["task"]) / "pool.jsonl")}
        owned = {r["id"] for r in read_jsonl(run_dir / "labels.jsonl")}
        revealed = [i for i in dict.fromkeys(ID_RE.findall(reply["answer"]))
                    if i in pool and i not in owned][: reply["labels_revealed"]]
        _append(run_dir / "labels.jsonl", [
            {"id": i, "text": pool[i]["text"], "label": pool[i]["label"], "tag": "revealed"} for i in revealed
        ])
        _append(run_dir / "oracle_log.jsonl", [{
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "kind": "ask",
            "question": question,
            "answer": reply["answer"],
            "parts": reply["parts"],
            "labels_revealed": reply["labels_revealed"],
            "labels_added": revealed,
            "cost": cost,
            "oracle_model": ORACLE_MODEL,
            "oracle_version": ORACLE_VERSION,
            "oracle_tokens": usage,
        }])
    return {"answer": reply["answer"], "cost": cost, "labels_added": revealed,
            "spent": spent(run_dir), "budget": run["budget"]}


def status(run_dir: Path) -> dict:
    run = _load_run(run_dir)
    log = _log(run_dir)
    used = spent(run_dir)
    return {
        "task": run["task"],
        "budget": run["budget"],
        "spent": used,
        "remaining": run["budget"] - used,
        "labels_bought": sum(len(e["ids"]) for e in log if e["kind"] == "label"),
        "questions_asked": sum(1 for e in log if e["kind"] == "ask"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--token", help="from tools/claim_run.py (default: $RUN_TOKEN)")
    sub = parser.add_subparsers(dest="command", required=True)
    lab = sub.add_parser("label", help=f"buy gold labels for pool ids ({LABEL_COST} points each)")
    lab.add_argument("--tag", help="stored with each new label, e.g. 'check' for a random check set")
    lab.add_argument("ids", nargs="+")
    q = sub.add_parser("ask", help="ask the domain expert a question (2, 5 or 10 points)")
    q.add_argument("question")
    sub.add_parser("status", help="points spent and remaining")
    args = parser.parse_args()

    try:
        result: Any
        if args.command == "status":
            result = status(args.run_dir)
        else:
            check_owner(args.run_dir, token_from(args.token))
            if args.command == "label":
                result = buy_labels(args.run_dir, args.ids, args.tag)
            else:
                result = ask(args.run_dir, args.question)
    except (OracleError, OwnershipError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
