"""Loaders shared by the classifier-builder scripts."""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_env() -> None:
    """Load KEY=VALUE lines from ./.env without overriding the environment."""
    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
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
