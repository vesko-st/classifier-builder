"""Harness-only: what every run cost, split by who spent it.

    python tools/cost_report.py [--json OUT] [run_id ...]

Columns (USD):
  builder   the builder agent's API cost (summary.json; pilot subagent runs have none)
  user      the simulated user (oracle_log.jsonl tokens at the rates of the model that answered)
  s1_build  System 1 calls the builder made while building. From
            system1_costs.jsonl when the run logged it; otherwise rebuilt from
            the uncached records of the result files in the run's work dir,
            marked '>=' because overwritten result files are lost.
  test_jev  scoring every snapshot on the test set with Jev
  test_luna re-scoring with Luna
Also prints the baselines' test costs and RoBERTa training time.
"""

import argparse
import json
from pathlib import Path

from common import ROOT, RUNS_DIR

HARNESS = RUNS_DIR / "_harness"
# USD per 1M input / output tokens; log entries without a model are from the Sonnet 5 simulated user.
USER_RATES = {"claude-sonnet-5": (2.0, 10.0), "claude-opus-5-5": (5.0, 25.0)}
JEV_RATE = 0.042  # USD per 1M input tokens


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def user_cost(run: str) -> float:
    total = 0.0
    for e in read_jsonl(RUNS_DIR / run / "oracle_log.jsonl"):
        t = e.get("oracle_tokens") or {}
        rate_in, rate_out = USER_RATES[e.get("oracle_model", "claude-sonnet-5")]
        total += t.get("input", 0) / 1e6 * rate_in + t.get("output", 0) / 1e6 * rate_out
    return total


def build_cost(run: str) -> tuple[float, bool]:
    logged = [e for e in read_jsonl(HARNESS / run / "system1_costs.jsonl") if e.get("phase") == "build"]
    if logged:
        return sum(e.get("est_cost_usd") or 0 for e in logged), True
    tokens = 0
    for f in (RUNS_DIR / run / "work").rglob("*.jsonl"):
        for r in read_jsonl(f):
            if isinstance(r, dict) and "usage" in r and not r.get("cached"):
                tokens += (r.get("usage") or {}).get("input_tokens", 0)
    return tokens / 1e6 * JEV_RATE, False


def test_costs(run: str) -> tuple[float, float]:
    jev = luna = 0.0
    for f in (HARNESS / run).glob("v*_test_summary.json"):
        cost = json.loads(f.read_text()).get("est_cost_usd") or 0
        if "_luna_" in f.name:
            luna += cost
        else:
            jev += cost
    return jev, luna


def run_row(run: str) -> dict:
    summary_path = HARNESS / run / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    meta = json.loads((RUNS_DIR / run / "run.json").read_text())
    s1, exact = build_cost(run)
    test_jev, test_luna = test_costs(run)
    return {
        "run": run, "task": meta.get("task"), "strategy": meta.get("strategy"),
        "mode": meta.get("mode", "budget"), "model": summary.get("model"),
        "minutes": round(summary["wall_seconds"] / 60, 1) if "wall_seconds" in summary else None,
        "builder": summary.get("total_cost_usd"), "user": user_cost(run),
        "s1_build": s1, "s1_build_exact": exact, "test_jev": test_jev, "test_luna": test_luna,
    }


def baseline_rows() -> list[dict]:
    rows = []
    for d in sorted((ROOT / "baselines").iterdir()):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*_test_summary.json")):
            s = json.loads(f.read_text())
            rows.append({"task": d.name, "file": f.name, "est_cost_usd": s.get("est_cost_usd"),
                         "train_seconds": s.get("train_seconds")})
    return rows


def fmt(x, prefix=""):
    return "—" if x is None else f"{prefix}{x:.2f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="*")
    parser.add_argument("--json", help="also write every row here")
    args = parser.parse_args()

    runs = args.runs or sorted(p.parent.name for p in RUNS_DIR.glob("*/run.json"))
    rows = [run_row(r) for r in runs]
    print(f"{'run':34} {'model':26} {'min':>5} {'builder':>8} {'user':>6} {'s1_build':>9} {'test_jev':>8} {'test_luna':>9}")
    for r in rows:
        print(f"{r['run']:34} {str(r['model']):26} {str(r['minutes'] or '—'):>5} {fmt(r['builder']):>8} "
              f"{fmt(r['user']):>6} {fmt(r['s1_build'], '' if r['s1_build_exact'] else '>='):>9} "
              f"{fmt(r['test_jev']):>8} {fmt(r['test_luna']):>9}")
    totals = {k: sum(r[k] or 0 for r in rows) for k in ("builder", "user", "s1_build", "test_jev", "test_luna")}
    print("TOTAL", "  ".join(f"{k} {v:.2f}" for k, v in totals.items()), f"all {sum(totals.values()):.2f}")

    base = baseline_rows()
    print("\nbaselines:")
    for b in base:
        extra = f" train {b['train_seconds']}s" if b["train_seconds"] else ""
        print(f"  {b['task']:28} {b['file']:44} {fmt(b['est_cost_usd'])}{extra}")
    if args.json:
        Path(args.json).write_text(json.dumps({"runs": rows, "totals": totals, "baselines": base}, indent=2) + "\n")


if __name__ == "__main__":
    main()
