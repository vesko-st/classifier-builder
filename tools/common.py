"""Paths and loaders shared by the project tools."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
DATA_DIR = ROOT / "data"
RUNS_DIR = ROOT / "runs"
ENV_FILE = ROOT.parent / ".env"


def load_env() -> None:
    """Load KEY=VALUE lines from ~/typesafe/.env without overriding the environment."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_jsonl_lenient(path: Path) -> tuple[list[dict], int]:
    """Rows that parse, and how many lines didn't (a file another process is still writing)."""
    rows, bad = [], 0
    for line in path.read_bytes().decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            bad += 1
    return rows, bad


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


@contextlib.contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Exclusive advisory lock on `path` (created if missing), held for the block."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def run_lock(run_dir: Path) -> contextlib.AbstractContextManager[None]:
    return file_lock(run_dir / ".lock")


# Run ownership: one builder per run. A builder claims the run and passes its
# token to every tool that spends points or writes a snapshot, so a second
# builder started on the same run is refused instead of interleaving with it.

OWNER_FILE = "owner.json"


class OwnershipError(RuntimeError):
    pass


def claim_run(run_dir: Path, takeover: bool = False) -> str:
    with run_lock(run_dir):
        path = run_dir / OWNER_FILE
        if path.exists() and not takeover:
            owner = json.loads(path.read_text())
            raise OwnershipError(
                f"run already claimed at {owner['claimed']}; another builder owns it. "
                "Stop and report this instead of continuing."
            )
        token = secrets.token_hex(4)
        path.write_text(json.dumps({"token": token, "claimed": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                    "takeover": takeover}) + "\n")
        return token


def check_owner(run_dir: Path, token: str | None) -> None:
    path = run_dir / OWNER_FILE
    if not path.exists():
        raise OwnershipError(f"run is not claimed; run: tools/claim_run.py {run_dir}")
    if not token:
        raise OwnershipError("missing token: pass --token (printed by claim_run.py) or set RUN_TOKEN")
    if token != json.loads(path.read_text())["token"]:
        raise OwnershipError(
            "wrong token: this run belongs to another builder. Stop and report this."
        )


def token_from(arg: str | None) -> str | None:
    return arg or os.environ.get("RUN_TOKEN")


def load_task(name: str) -> dict[str, Any]:
    """The public task definition, with `classes` resolved to {class: description|None}."""
    task_dir = TASKS_DIR / name
    task = json.loads((task_dir / "task.json").read_text())
    if isinstance(task["classes"], str):
        task["classes"] = json.loads((task_dir / task["classes"]).read_text())
    return task


def private_dir(name: str) -> Path:
    return DATA_DIR / name / "private"


def guideline(name: str) -> str:
    return (TASKS_DIR / name / "private" / "guideline.md").read_text()


def labels(name: str, split: str) -> dict[str, Any]:
    """Gold labels by id for a split: pool, val or test."""
    return {r["id"]: r["label"] for r in read_jsonl(private_dir(name) / f"{split}.jsonl")}
