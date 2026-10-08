#!/usr/bin/env python3
"""
Run a builder agent headlessly on an existing run, through the Claude Agent SDK.

    python tools/run_builder.py runs/<run_id> --model claude-opus-5-5 [--effort high] [--max-turns 400] [--score]

Create the run first with tools/new_run.py. The builder gets tools/builder_prompt.md
with the run, budget, metric and strategy filled in, works from the project root,
and loads no user or project settings. A PreToolUse hook confines it to its run
directory, the skill, the tools it may run, /tmp, and the TypeSafe docs; denied
calls are returned to the builder as errors and logged.

Writes runs/_harness/<run_id>/:
    prompt.md        the prompt as sent
    builder.jsonl    every message of the session
    denials.jsonl    tool calls the hook blocked, with the reason
    summary.json     model, turns, cost, duration, stop reason, final reply
With --score, runs tools/score_test.py on the run when the builder finishes.

The hook is a guard against accidents and casual peeking, not a security
boundary: a builder can still reach hidden files through code that builds paths
at run time. Audit builder.jsonl after each run.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, ResultMessage, query

from common import ROOT, RUNS_DIR, load_env

HARNESS_DIR = RUNS_DIR / "_harness"
TYPESAFE_SKILL = Path.home() / ".agents" / "skills" / "typesafe-ai"
PROMPT_TEMPLATE = ROOT / "tools" / "builder_prompt.md"
PROMPT_TEMPLATE_ALL_LABELS = ROOT / "tools" / "builder_prompt_all_labels.md"
METRIC_NAMES = {"accuracy": "accuracy", "macro_f1": "macro-F1"}

# Builders may run ask_oracle.py but not read it; the rest are harness-only.
RUN_ONLY_TOOLS = {"ask_oracle.py"}
HIDDEN_TOOLS = {"watch_run.py", "score_test.py", "prepare_tasks.py", "run_builder.py", "compare_models.py", "collect_runs.py",
                "finetune_baseline.py"}
HIDDEN_ROOTS = [
    ROOT / "data", ROOT / "tasks", ROOT / "baselines", ROOT / "paper", ROOT / "PLAN.md",
    ROOT.parent / "sales-benchmark", ROOT.parent / "datasets",
    Path.home() / ".cursor", Path.home() / ".claude",
]
# Bare words that are path names here but rarely anything else in a command.
BARE_PATH_WORDS = {"runs", "baselines", "PLAN.md"}
FETCH_RE = re.compile(
    r"\b(curl|wget|git\s+clone|pip\s+install|load_dataset|hf_hub_download|snapshot_download)\b"
    r"|huggingface|hf\.co|kaggle",
    re.IGNORECASE,
)
TOKEN_SPLIT_RE = re.compile(r"[\s'\"`=;|&()<>,\[\]{}]+")
TMP_ROOTS = [Path("/tmp"), Path("/private/tmp")]
VENV_PREFIXES = tuple("../" * n + ".venv/bin/" for n in range(1, 5))
# Claude Code saves long tool outputs here and tells the builder to read them.
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


def _resolve(raw: str, base: Path) -> Path:
    path = Path(raw).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def _under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


class Guard:
    def __init__(self, run_dir: Path, log_path: Path) -> None:
        self.run_dir = run_dir.resolve()
        self.log_path = log_path
        self.read_roots = [self.run_dir, ROOT / "skill", ROOT / "tools", TYPESAFE_SKILL, *TMP_ROOTS]
        self.write_roots = [self.run_dir, *TMP_ROOTS]
        self.session_id: str | None = None

    def _own_tool_result(self, path: Path) -> bool:
        if not self.session_id or not _under(path, CLAUDE_PROJECTS):
            return False
        parts = path.relative_to(CLAUDE_PROJECTS).parts
        return len(parts) >= 3 and parts[1] == self.session_id and parts[2] == "tool-results"

    def _path_problem(self, path: Path) -> str | None:
        if self._own_tool_result(path):
            return None
        if path.name.startswith(".env"):
            return "environment files hold API keys"
        if _under(path, RUNS_DIR) and not _under(path, self.run_dir):
            return "other runs and the harness directory are hidden"
        for root in HIDDEN_ROOTS:
            if _under(path, root):
                return f"{root} is hidden from builders"
        if path.parent == ROOT / "tools" and path.name in HIDDEN_TOOLS | RUN_ONLY_TOOLS:
            return f"the source of tools/{path.name} is hidden"
        return None

    def check_file(self, tool: str, raw: str | None, write: bool) -> str | None:
        if not raw:
            return f"{tool} needs an explicit path inside RUN_DIR, skill/ or tools/"
        if ".." in Path(raw).parts:
            return "paths with '..' are not allowed"
        path = _resolve(raw, ROOT)
        problem = self._path_problem(path)
        if problem:
            return problem
        if not write and self._own_tool_result(path):
            return None
        roots = self.write_roots if write else self.read_roots
        if not any(_under(path, root) for root in roots):
            where = "RUN_DIR or /tmp" if write else "RUN_DIR, skill/, tools/, the TypeSafe skill or /tmp"
            return f"{tool} is limited to {where}"
        return None

    def check_bash(self, command: str) -> str | None:
        if FETCH_RE.search(command):
            return "downloading data or packages is not allowed"
        tokens = [t for t in TOKEN_SPLIT_RE.split(command) if t]
        for i, token in enumerate(tokens):
            if "/" not in token and not token.startswith((".", "~")) and token not in BARE_PATH_WORDS:
                continue
            if "://" in token:
                continue
            if ".." in Path(token).parts and not token.startswith(VENV_PREFIXES):
                return "paths with '..' are not allowed (other than ../.venv/bin/python)"
            path = _resolve(token, ROOT)
            if path.parent == ROOT / "tools" and path.name in RUN_ONLY_TOOLS:
                if i > 0 and re.search(r"python[\d.]*$", tokens[i - 1]):
                    continue
                return f"tools/{path.name} may only be run with python, not read"
            problem = self._path_problem(path)
            if problem:
                return problem
        return None

    def check(self, tool: str, tool_input: dict[str, Any]) -> str | None:
        if tool == "Bash":
            if tool_input.get("run_in_background"):
                # A headless session gets no completion notice: a builder that waits
                # on a background command ends its session instead.
                return ("background commands are not available here; run it in the foreground "
                        "with a timeout of up to 1200000 ms")
            return self.check_bash(str(tool_input.get("command", "")))
        if tool in ("BashOutput", "KillShell", "KillBash"):
            return "background commands are not available here"
        if tool in ("Read", "Write", "Edit", "MultiEdit"):
            return self.check_file(tool, tool_input.get("file_path"), write=tool != "Read")
        if tool == "NotebookEdit":
            return self.check_file(tool, tool_input.get("notebook_path"), write=True)
        if tool in ("Glob", "Grep"):
            pattern = str(tool_input.get("pattern", "")) + str(tool_input.get("glob", ""))
            if ".." in pattern or pattern.startswith(("/", "~")):
                return f"{tool} patterns must be relative to an allowed path"
            return self.check_file(tool, tool_input.get("path"), write=False)
        if tool == "WebFetch":
            url = str(tool_input.get("url", ""))
            if not url.startswith("https://docs.typesafe.ai"):
                return "web access is limited to https://docs.typesafe.ai"
            return None
        if tool in ("TodoWrite", "ToolSearch", "BashOutput", "KillBash", "KillShell", "TaskOutput", "TaskStop"):
            return None
        return f"{tool} is not available to builders"

    async def hook(self, hook_input: Any, tool_use_id: str | None, context: Any) -> dict[str, Any]:
        tool = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {}) or {}
        self.session_id = hook_input.get("session_id") or self.session_id
        problem = self.check(tool, tool_input)
        if problem is None:
            return {}
        with self.log_path.open("a") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": tool,
                                "input": tool_input, "reason": problem}, ensure_ascii=False) + "\n")
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Blocked by the harness: {problem}.",
        }}


def build_prompt(run_dir: Path) -> str:
    run = json.loads((run_dir / "run.json").read_text())
    task = json.loads((run_dir / "task.json").read_text())
    strategy = run.get("strategy", "free")
    clause = "." if strategy == "free" else (
        f", using the strategy in {ROOT}/skill/strategies/{strategy}.md in place of workflow "
        "step 3. Follow the strategy closely."
    )
    note = "" if strategy == "free" else (
        f" Analyse errors and decide which revisions to keep with the strategy in "
        f"{ROOT}/skill/strategies/{strategy}.md. Follow it closely."
    )
    constraints = "".join(
        f" Throughout, also follow the constraint in {ROOT}/skill/constraints/{name}.md; where it differs "
        "from the skill or strategy, the constraint wins."
        for name in run.get("constraints", [])
    )
    clause += constraints
    note += constraints
    template = PROMPT_TEMPLATE_ALL_LABELS if run.get("mode") == "all_labels" else PROMPT_TEMPLATE
    return template.read_text().format(
        root=ROOT, run_dir=run_dir, budget=run["budget"], strategy_clause=clause, strategy_note=note,
        metric=METRIC_NAMES.get(task.get("metric", ""), task.get("metric", "score")),
        typesafe_skill=TYPESAFE_SKILL / "SKILL.md",
        n_labels=f"{sum(1 for _ in (run_dir / 'labels.jsonl').open()):,}",
    )


def _message_record(message: Any) -> dict[str, Any]:
    body = dataclasses.asdict(message) if dataclasses.is_dataclass(message) else {"repr": repr(message)}
    return {"type": type(message).__name__, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), **body}


async def run(args: argparse.Namespace, run_dir: Path, out_dir: Path) -> ResultMessage | None:
    prompt = build_prompt(run_dir)
    (out_dir / "prompt.md").write_text(prompt)
    guard = Guard(run_dir, out_dir / "denials.jsonl")
    options = ClaudeAgentOptions(
        model=args.model,
        cwd=str(ROOT),
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=[],
        permission_mode="bypassPermissions",
        disallowed_tools=["Task", "Agent", "WebSearch"],
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[guard.hook])]},
        max_turns=args.max_turns,
        max_budget_usd=args.max_usd,
        effort=args.effort,
        env={
            "BASH_DEFAULT_TIMEOUT_MS": "600000", "BASH_MAX_TIMEOUT_MS": "1200000",
            "CLASSIFIER_COST_LOG": str(out_dir / "system1_costs.jsonl"), "CLASSIFIER_COST_PHASE": "build",
        },
        stderr=lambda line: print(f"[cli] {line}", file=sys.stderr),
    )
    result = None
    with (out_dir / "builder.jsonl").open("a") as log:
        async for message in query(prompt=prompt, options=options):
            log.write(json.dumps(_message_record(message), ensure_ascii=False, default=str) + "\n")
            log.flush()
            if isinstance(message, ResultMessage):
                result = message
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--model", required=True, help="e.g. claude-opus-5-5, claude-sonnet-5-5, claude-haiku-4-5-20251001")
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--max-turns", type=int, default=400)
    parser.add_argument("--max-usd", type=float, default=40.0, help="stop the session past this API cost")
    parser.add_argument("--score", action="store_true", help="score every snapshot on the test set afterwards")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    if not (run_dir / "run.json").exists() or run_dir.parent != RUNS_DIR:
        parser.error(f"{run_dir} is not a run directory under {RUNS_DIR}; create it with tools/new_run.py")
    out_dir = HARNESS_DIR / run_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "builder.jsonl").exists():
        parser.error(f"{out_dir}/builder.jsonl exists: this run already had a builder")

    load_env()
    started = time.time()
    result = asyncio.run(run(args, run_dir, out_dir))
    summary = {
        "run_id": run_dir.name,
        "model": args.model,
        "effort": args.effort,
        "wall_seconds": round(time.time() - started),
        "denials": sum(1 for _ in (out_dir / "denials.jsonl").open()) if (out_dir / "denials.jsonl").exists() else 0,
    }
    if result is not None:
        summary.update({
            "subtype": result.subtype, "is_error": result.is_error, "num_turns": result.num_turns,
            "total_cost_usd": result.total_cost_usd, "stop_reason": result.stop_reason,
            "terminal_reason": result.terminal_reason, "usage": result.usage, "reply": result.result,
        })
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("usage", "reply")}, default=str))

    if args.score:
        subprocess.run([sys.executable, str(ROOT / "tools" / "score_test.py"), run_dir.name], check=False)
    return 0 if result is not None and not result.is_error else 1


if __name__ == "__main__":
    sys.exit(main())
