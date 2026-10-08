#!/usr/bin/env python3
"""
Claim a run directory before working in it. Prints a token.

    python tools/claim_run.py RUN_DIR

Pass the token to every command that spends points or saves a snapshot
(`--token TOKEN`, or `export RUN_TOKEN=TOKEN`). A run can be claimed once; if
the claim is refused, another builder owns the run: stop and report it.

    python tools/claim_run.py RUN_DIR --takeover    # harness only: replace a dead builder
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import OwnershipError, claim_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--takeover", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not (args.run_dir / "run.json").exists():
        parser.error(f"{args.run_dir} is not a run directory")
    try:
        token = claim_run(args.run_dir, takeover=args.takeover)
    except OwnershipError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
