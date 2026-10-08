#!/usr/bin/env python3
"""Write a task's applied-policy note: how the gold labels apply the written guideline.

Claude Opus 5.5 reads the guideline and explores every labelled pool record with
the simulated user's search tools, then writes a note on how the labels actually
draw each boundary: where they follow the guideline, where they are looser or
stricter, and where they are inconsistent. The simulated user answers questions
from the guideline and this note (tools/ask_oracle.py), so every builder on a task
talks to the same user.

    python tools/infer_policy.py TASK [--force]

Writes tasks/TASK/private/applied_policy.md and a log of the session next to it.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time

from ask_oracle import ORACLE_MODEL, TOOLS, _render_record, _run_tool
from common import TASKS_DIR, guideline, load_env, private_dir, read_jsonl

MAX_ROUNDS = 60
SAMPLE_SIZE = 150

SYSTEM = """\
You own a text classification task and its labelled data. The labels were \
produced by annotators following the written policy below, but annotators apply \
a policy in their own way: in places they are looser or stricter than the text, \
they settle cases it does not cover, and on some kinds of message they are \
inconsistent.

Your job is to work out how the labels actually apply the policy, so that you can \
later answer an engineer's questions about the task truthfully without looking \
at the data again. Explore the labelled pool with your tools until you \
understand every class boundary: search for each kind of message the policy \
mentions, for kinds it does not mention, and for near-miss cases on both sides of \
each boundary, and check how they are labelled. Use many searches; the pool is \
the only evidence that counts.

Then write the note, in plain prose with short headings, at most about 1,200 \
words. For each class or boundary, state the rule as the labels apply it, how \
confident you are, and roughly how consistent the labels are (for example "about \
three in four such messages are labelled X"). Say explicitly where the labels \
depart from the written policy. Describe kinds of message, with short invented \
examples where they help; do not cite record ids and do not quote records. Reply \
with the note only."""


def _context(task: str, pool: list[dict]) -> str:
    public = json.loads((TASKS_DIR / task / "task.json").read_text())
    extra = sorted((TASKS_DIR / task / "private").glob("*.json"))
    sample = random.Random(f"policy-sample:{task}").sample(pool, min(SAMPLE_SIZE, len(pool)))
    parts = [
        "# Task as the engineer knows it\n" + json.dumps(public, indent=2),
        "# Written labelling policy\n" + guideline(task),
        *(f"# {f.stem}\n{f.read_text()}" for f in extra),
        f"# Pool: {len(pool)} labelled records. A random sample to start from:\n"
        + "\n".join(map(_render_record, sample)),
    ]
    return "\n\n".join(parts)


def infer(task: str) -> tuple[str, dict]:
    from anthropic import Anthropic

    load_env()
    client = Anthropic()
    pool = read_jsonl(private_dir(task) / "pool.jsonl")
    messages: list[dict] = [{"role": "user", "content": _context(task, pool)}]
    usage = {"input": 0, "output": 0, "tool_calls": 0, "rounds": 0}
    for round_ in range(MAX_ROUNDS + 1):
        msg = client.messages.create(
            model=ORACLE_MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=SYSTEM,
            tools=TOOLS,
            tool_choice={"type": "none"} if round_ == MAX_ROUNDS else {"type": "auto"},
            messages=messages,
        )
        usage["input"] += msg.usage.input_tokens
        usage["output"] += msg.usage.output_tokens
        usage["rounds"] = round_ + 1
        uses = [b for b in msg.content if getattr(b, "type", None) == "tool_use"]
        if not uses:
            return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip(), usage
        usage["tool_calls"] += len(uses)
        messages.append({"role": "assistant", "content": msg.content})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": _run_tool(pool, b.name, dict(b.input))}
            for b in uses
        ]})
    raise RuntimeError("no note after the last round")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task")
    parser.add_argument("--force", action="store_true", help="overwrite an existing note")
    args = parser.parse_args()

    out = TASKS_DIR / args.task / "private" / "applied_policy.md"
    if out.exists() and not args.force:
        sys.exit(f"{out} exists; pass --force to rewrite it")
    started = time.time()
    note, usage = infer(args.task)
    out.write_text(note + "\n")
    log = {"task": args.task, "model": ORACLE_MODEL, "seconds": round(time.time() - started), **usage}
    out.with_suffix(".log.json").write_text(json.dumps(log, indent=2) + "\n")
    print(json.dumps(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
