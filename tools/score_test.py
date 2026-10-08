"""Harness-only: score a run's snapshots on the sealed test split.

Skips versions already scored. Prints one line per version with the task's metric.
The backend defaults to the run's own ("backend" in run.json, else jev); scoring
with another backend writes `<version>_<backend>_test_*` files beside the Jev ones.
"""

import argparse
import json
import os
import subprocess
import sys

from common import DATA_DIR, ROOT, RUNS_DIR, file_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--backend", choices=["jev", "luna", "pplx", "claude"])
    parser.add_argument("--final-only", action="store_true", help="score only the last snapshot")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    out_dir = RUNS_DIR / "_harness" / args.run_id
    with file_lock(out_dir / ".score_test.lock"):
        score(run_dir, out_dir, args.backend, args.final_only)


def score(run_dir, out_dir, backend=None, final_only=False):
    run = json.loads((run_dir / "run.json").read_text())
    own = run.get("backend", "jev")
    backend = backend or own
    suffix = "" if backend == own else f"_{backend}"
    test = DATA_DIR / run["task"] / "private" / "test.jsonl"

    clfs = sorted((run_dir / "classifiers").glob("v*.json"))
    for clf in clfs[-1:] if final_only else clfs:
        summary_path = out_dir / f"{clf.stem}{suffix}_test_summary.json"
        if not summary_path.exists():
            subprocess.run(
                [sys.executable, str(ROOT / "tools" / "jev_classifier.py"), "run", str(clf), str(test),
                 "--input-field", "text", "--backend", backend, "--concurrency", "8" if backend == "pplx" else "32",
                 "-o", str(out_dir / f"{clf.stem}{suffix}_test_results.jsonl"),
                 "--summary-output", str(summary_path), "-q"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={**os.environ, "CLASSIFIER_COST_LOG": str(out_dir / "system1_costs.jsonl"),
                     "CLASSIFIER_COST_PHASE": f"test:{clf.stem}"},
            )
        s = json.loads(summary_path.read_text())
        per_class = "" if len(s["per_class"]) > 5 else " ".join(
            f"{k}: P {v['precision']:.2f} R {v['recall']:.2f}" for k, v in s["per_class"].items()
        )
        print(f"{clf.stem}{suffix}: macro-F1 {s['macro_f1']:.4f} acc {s['accuracy']:.4f} "
              f"errors {sum(s['errors'].values())} | {per_class}")


if __name__ == "__main__":
    main()
