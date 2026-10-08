#!/usr/bin/env python3
"""
Harness-only: supervised baseline. Fine-tunes an encoder on a task's pool labels
(the labels an all-labels builder receives), picks the epoch with the best
validation score, and scores it on the sealed test set.

    python tools/finetune_baseline.py banking77_intents_fullpool [--model roberta-base]
        [--n-train 50] [--epochs 5] [--seed 0] [--max-length 128]

--n-train N trains on a stratified sample of N pool records (e.g. the ~50
labels a 100-point builder buys). Inputs longer than --max-length are
truncated from the left, so a dialogue keeps its final turns.
Writes baselines/<task>/<name>_test_summary.json with accuracy and macro-F1.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from common import ROOT, load_task, private_dir, read_jsonl
from jev_classifier import class_metrics

BASELINES_DIR = ROOT / "baselines"


def stratified(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    by_label: dict[str, list[dict]] = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)
    for group in by_label.values():
        rng.shuffle(group)
    picked, i = [], 0
    while len(picked) < n and any(by_label.values()):
        for group in by_label.values():
            if i < len(group) and len(picked) < n:
                picked.append(group[i])
        i += 1
    return picked


def predict(model, tok, rows: list[dict], classes: list[str], args, device) -> list[str]:
    model.eval()
    preds: list[str] = []
    with torch.no_grad():
        for start in range(0, len(rows), args.batch_size * 2):
            batch = rows[start:start + args.batch_size * 2]
            enc = tok([r["text"] for r in batch], truncation=True, max_length=args.max_length,
                      padding=True, return_tensors="pt").to(device)
            logits = model(**enc).logits
            preds.extend(classes[i] for i in logits.argmax(-1).tolist())
    return preds


def score(rows: list[dict], preds: list[str], metric: str) -> tuple[float, dict]:
    m = class_metrics([{"gold": r["label"], "prediction": p} for r, p in zip(rows, preds)])
    m["accuracy"] = sum(r["label"] == p for r, p in zip(rows, preds)) / len(rows)
    return (m["accuracy"] if metric == "accuracy" else m["macro_f1"]), m


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task")
    parser.add_argument("--model", default="roberta-base")
    parser.add_argument("--n-train", type=int)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    task = load_task(args.task)
    metric = task.get("metric", "accuracy")
    classes = sorted(task["classes"])
    index = {c: i for i, c in enumerate(classes)}
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    train = read_jsonl(private_dir(args.task) / "pool.jsonl")
    if args.n_train:
        train = stratified(train, args.n_train, rng)
    val = read_jsonl(private_dir(args.task) / "val.jsonl")
    test = read_jsonl(private_dir(args.task) / "test.jsonl")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.model)
    tok.truncation_side = "left"
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=len(classes)).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps_per_epoch = (len(train) + args.batch_size - 1) // args.batch_size
    sched = get_linear_schedule_with_warmup(optim, int(0.1 * steps_per_epoch * args.epochs),
                                            steps_per_epoch * args.epochs)

    best_val, best_state, best_epoch = -1.0, None, 0
    started = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = list(range(len(train)))
        rng.shuffle(order)
        for start in range(0, len(order), args.batch_size):
            batch = [train[i] for i in order[start:start + args.batch_size]]
            enc = tok([r["text"] for r in batch], truncation=True, max_length=args.max_length,
                      padding=True, return_tensors="pt").to(device)
            labels = torch.tensor([index[r["label"]] for r in batch], device=device)
            loss = model(**enc, labels=labels).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            sched.step()
            optim.zero_grad()
        val_score, _ = score(val, predict(model, tok, val, classes, args, device), metric)
        print(f"epoch {epoch}: val {metric} {val_score:.4f} ({time.time() - started:.0f}s)", flush=True)
        if val_score > best_val:
            best_val, best_epoch = val_score, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    test_score, metrics = score(test, predict(model, tok, test, classes, args, device), metric)
    name = f"{args.model.split('/')[-1]}_n{args.n_train or len(train)}_s{args.seed}"
    out = BASELINES_DIR / args.task / f"{name}_test_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "model": args.model, "n_train": len(train), "epochs": args.epochs, "best_epoch": best_epoch,
        "lr": args.lr, "max_length": args.max_length, "seed": args.seed, "val": best_val,
        "accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"], "total": len(test),
        "train_seconds": round(time.time() - started),
    }, indent=2) + "\n")
    print(f"{args.task} {name}: test accuracy {metrics['accuracy']:.4f} macro-F1 {metrics['macro_f1']:.4f} "
          f"(best epoch {best_epoch}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
