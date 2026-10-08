"""Answer classifier questions with Claude through the Message Batches API (half price).

    claude_batch.py submit CLASSIFIER INPUTS [CLASSIFIER INPUTS ...] [--dry-run]
    claude_batch.py collect          # poll; write finished results into the Claude cache
    claude_batch.py status

`submit` gathers the uncached questions of every (classifier, inputs) pair, with the
same prompts and request parameters as `jev_classifier.py run --backend claude`, and
submits them in batches. `collect` writes each answer into the Claude cache, so a
later `run --backend claude` (or `score_test.py --backend claude`) finds every
question cached and makes no calls. Batch spend is logged to
runs/_harness/claude_batches/costs.jsonl because those cached runs report zero cost.
"""
import argparse
import json
import time
from pathlib import Path

from common import load_env
import jev_classifier as jc

BATCH_DIR = Path(__file__).resolve().parent.parent / "runs" / "_harness" / "claude_batches"
BATCH_DISCOUNT = 0.5
MAX_REQUESTS = 50_000
MAX_BYTES = 150_000_000


def client(args) -> jc.ClaudeClient:
    return jc.ClaudeClient(args.claude_model, jc.DEFAULT_CLAUDE_CACHE_DIR, timeout=600)


def gather(cc: jc.ClaudeClient, pairs: list[tuple[str, str]]) -> dict[str, tuple[Path, dict, str, list[str]]]:
    pending = {}
    for clf_path, inputs in pairs:
        clf = jc.load_classifier(clf_path)
        n = 0
        for ex in jc.load_examples(inputs, [], "text", None, None):
            payload = jc.build_payload(clf, ex.input)
            for p in payload.get("members", [payload]):
                for path, params, qtype, keys in cc.pending(p):
                    if path.stem not in pending:
                        pending[path.stem] = (path, params, qtype, keys)
                        n += 1
        print(f"{clf_path} on {inputs}: {n} new questions")
    return pending


def cmd_submit(args) -> None:
    if len(args.pairs) % 2:
        raise SystemExit("pass CLASSIFIER INPUTS pairs")
    cc = client(args)
    pending = gather(cc, list(zip(args.pairs[::2], args.pairs[1::2])))
    print(f"{len(pending)} questions to submit")
    if args.dry_run or not pending:
        return
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    chunk, size = [], 0
    items = list(pending.items())
    for i, (cid, (path, params, qtype, keys)) in enumerate(items):
        req = {"custom_id": cid, "params": params}
        chunk.append((req, str(path), qtype, keys))
        size += len(json.dumps(req))
        if len(chunk) == MAX_REQUESTS or size > MAX_BYTES or i == len(items) - 1:
            batch = cc.client.messages.batches.create(requests=[c[0] for c in chunk])
            manifest = {"batch_id": batch.id, "model": cc.model, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "requests": {c[0]["custom_id"]: [c[1], c[2], c[3]] for c in chunk}}
            (BATCH_DIR / f"{batch.id}.json").write_text(json.dumps(manifest))
            print(f"submitted {batch.id}: {len(chunk)} requests, {size / 1e6:.0f} MB")
            chunk, size = [], 0


def cmd_collect(args) -> None:
    cc = client(args)
    for mpath in sorted(BATCH_DIR.glob("msgbatch_*.json")):
        manifest = json.loads(mpath.read_text())
        if manifest.get("collected"):
            continue
        batch = cc.client.messages.batches.retrieve(manifest["batch_id"])
        if batch.processing_status != "ended":
            c = batch.request_counts
            print(f"{batch.id}: {batch.processing_status} (processing {c.processing}, succeeded {c.succeeded}, errored {c.errored})")
            continue
        stored, failed, tin, tout = 0, {}, 0, 0
        for entry in cc.client.messages.batches.results(batch.id):
            path, qtype, keys = manifest["requests"][entry.custom_id]
            if entry.result.type != "succeeded":
                failed[entry.result.type] = failed.get(entry.result.type, 0) + 1
                continue
            text, usage = cc.parse_message(entry.result.message)
            tin, tout = tin + usage["input_tokens"], tout + usage["output_tokens"]
            try:
                cc.store(Path(path), qtype, keys, text, usage)
                stored += 1
            except jc.ServiceError as e:
                failed[str(e)[:60]] = failed.get(str(e)[:60], 0) + 1
        cost = BATCH_DISCOUNT * (tin * jc.CLAUDE_USD_PER_INPUT_TOKEN + tout * jc.CLAUDE_USD_PER_OUTPUT_TOKEN)
        entry = {"batch_id": batch.id, "model": manifest["model"], "requests": len(manifest["requests"]),
                 "stored": stored, "failed": failed, "input_tokens": tin, "output_tokens": tout,
                 "est_cost_usd": round(cost, 4)}
        with open(BATCH_DIR / "costs.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
        manifest["collected"] = entry
        mpath.write_text(json.dumps(manifest))
        print(json.dumps(entry))


def cmd_status(args) -> None:
    for mpath in sorted(BATCH_DIR.glob("msgbatch_*.json")):
        m = json.loads(mpath.read_text())
        print(m["batch_id"], len(m["requests"]), "collected" if m.get("collected") else "pending",
              m.get("collected", {}).get("est_cost_usd", ""))


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude-model", default=jc.DEFAULT_CLAUDE_MODEL)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("pairs", nargs="+")
    s.add_argument("--dry-run", action="store_true")
    sub.add_parser("collect")
    sub.add_parser("status")
    args = parser.parse_args()
    {"submit": cmd_submit, "collect": cmd_collect, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()
