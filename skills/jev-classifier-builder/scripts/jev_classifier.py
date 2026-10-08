#!/usr/bin/env python3
"""
Build and run TypeSafe Jev classifiers stored as JSON files.

A classifier file holds the static part of a Jev request: the question type,
the instructions, the options/levels (criteria), and a state template with
placeholders for the input. `run` fills the template once per input, calls
Jev, and writes one JSON result per line.

Classifier file:

    {
      "version": 1,
      "name": "support_team",
      "description": "Routes support tickets to a team.",   # optional, not sent
      "model": "jev-latest",
      "type": "choice",                                     # choice | noul | score
      "instructions": "Which team should handle this support ticket?",
      "criteria": {"billing": "charges, refunds", "none": "none of the above"},
      "state_template": "Support ticket:\\n{{input}}"
    }

  criteria by type:
    choice: {"option key": "description or null", ...}, 2-255 options
    score:  ["lowest level", ..., "highest level"], 2-10 levels
    noul:   optional {"true": "what yes means", "false": "what no means"}

  choice may also have "include": ["option key", ...]. Then P(yes) is the sum of
  those options' probabilities, the prediction is P(yes) >= --threshold, the top
  option is reported as "category", and labels are yes/no (or an option key).
  "include" is not sent to Jev.

  choice may instead have "map": {"option key": "class", ...}, a many-to-one map
  from options to output classes (unmapped options are their own class). Each
  class's probability is the sum of its options' probabilities; the prediction is
  the most likely class, the top option is reported as "category", and labels
  are class names. "map" is not sent to Jev.

  "type": "two_level" picks a group, then a class within the group, in a single
  request (all questions are asked together):

    {
      "type": "two_level",
      "name": "intents",
      "state_template": "Customer message:\\n{{input}}",
      "router": {"instructions": "Which area is this about?",
                 "criteria": {"cards": "...", "transfers": "...", "age": "..."}},
      "groups": {
        "cards":     {"instructions": "Which card issue?", "criteria": {...}, "map": {...}},
        "transfers": {"instructions": "Which transfer issue?", "criteria": {...}},
        "age":       {"class": "age_limit"}          # a group with a single class
      }
    }

  P(class) = sum over groups of P(group) * P(class's options | group), so a
  wrong router choice is recoverable. The prediction is the most likely class;
  "category" is the most likely group/option path, "group" the router's choice.
  Each group question costs input tokens, so requests cost more than a flat choice.

  "type": "criteria" asks several yes/no (noul) questions in one request and
  combines them with a rule, for tasks whose policy is a conjunction of tests:

    {
      "type": "criteria",
      "state_template": "Tweet:\\n{{input}}",
      "questions": {
        "target":    {"instructions": "Is the tweet about women or immigrants?"},
        "demeaning": {"instructions": "Does it demean or dehumanise them?",
                      "criteria": {"true": "...", "false": "..."}},
        "quoted":    {"instructions": "Is the author quoting or criticising someone else?"},
        "exclusion": {"instructions": "Does it call for immigrants to be expelled?"}
      },
      "rule": [["target", "demeaning", "!quoted"], ["exclusion"]],
      "positive": "hate",
      "negative": "not_hate"
    }

  "rule" is an OR of ANDs: the positive class holds when every question in some
  inner list is yes ("!name" means no). Questions are treated as independent:
  P(clause) = product of its P(yes)/P(no), P(positive) = 1 - product of
  (1 - P(clause)). "category" is the most likely clause, or "none". Results
  carry "criteria_p" (P(yes) per question) and "class_probabilities".

  "type": "ensemble" averages the class probabilities of several member
  classifiers (choice, choice with map, two_level or criteria), one Jev request
  per member:

    {"type": "ensemble", "name": "committee",
     "members": [{...classifier...}, {...classifier...}, {...}],
     "weights": [1, 1, 1]}                                  # optional

  Results carry "member_predictions" (a list of each member's predicted class,
  in member order, e.g. ["hate", "not_hate", "hate"]) and "disagreement"
  (members differ), and "category" is how many members agree with the
  ensemble's prediction ("2/3 agree").

  Classifiers that produce class probabilities (choice with map, two_level,
  criteria, ensemble) may set a decision threshold for one class:

    "decision": {"class": "hate", "threshold": 0.65}

  The prediction is that class when its probability is at least the threshold,
  otherwise the most likely other class. Results from these classifiers (and
  plain choice) carry "margin": 2 x the distance from the threshold when one is
  set, otherwise top class probability minus the second. It is stored in the file, so snapshots
  keep it (unlike --threshold, which applies to noul and include only).

  state_template can be a string or a JSON object/array. Placeholders:
    {{input}}          the whole input (JSON-encoded if it isn't a string)
    {{input.a.b}}      a field of a structured input
  A value that is exactly one placeholder keeps the input's JSON structure.
  `instructions` may also contain placeholders for per-input question data.

Examples:

    # Build
    python jev_classifier.py build --name support_team --type choice \\
        --instructions "Which team should handle this support ticket?" \\
        --option "billing=charges, refunds, invoices" \\
        --option "shipping=delivery, tracking, lost packages" \\
        --none-option "None of the above" \\
        --state-template 'Support ticket:\\n{{input}}' -o support_team.json

    python jev_classifier.py build --name urgent --type noul \\
        --instructions "Is the customer reporting money taken in error?" -o urgent.json

    python jev_classifier.py build --name frustration --type score \\
        --instructions "How frustrated is the customer?" \\
        --level "Calm" --level "Mildly annoyed" --level "Very angry" -o frustration.json

    # Check a hand-written classifier file
    python jev_classifier.py validate support_team.json

    # Run over a dataset (.jsonl, .json array, .csv, or .txt with one input per line)
    python jev_classifier.py run support_team.json tickets.jsonl \\
        --input-field text --label-field team -o results.jsonl

    python jev_classifier.py run urgent.json --text "I was charged twice!"
    python jev_classifier.py run support_team.json tickets.jsonl --dry-run --limit 2

Records without --input-field are passed whole, minus the id and label fields.
With labels, `run` reports accuracy, macro-F1, per-class scores, the most common
confusions, and accuracy by confidence bucket.
Needs TYPESAFE_API_KEY (read from the environment or a .env file in the working directory) unless
every request is cached or --dry-run is set.

`run --backend luna` (or CLASSIFIER_BACKEND=luna) answers the same classifier
file with OpenAI gpt-6-luna (low reasoning by default) instead of Jev, one call
per question restated as a prompt; it needs OPENAI_API_KEY. Luna states a
confidence in its answer, so the other options of a choice share the rest evenly.
`run --backend pplx` sends the same requests to Perplexity's Decisions API
(pplx-decider-v1-27b), which takes Jev's schema; it needs PERPLEXITY_API_KEY.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from common import load_env

API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
FORMAT_VERSION = 1
QUESTION_ID = "q"
USD_PER_INPUT_TOKEN = 0.042 / 1_000_000
DEFAULT_LUNA_MODEL = "gpt-6-luna"
LUNA_USD_PER_INPUT_TOKEN = 0.10 / 1_000_000
LUNA_USD_PER_OUTPUT_TOKEN = 0.50 / 1_000_000
DEFAULT_LUNA_CACHE_DIR = Path.home() / ".cache" / "luna-classifier"
PPLX_API_URL = "https://api.perplexity.ai/v1/decisions"
PPLX_MODEL = "pplx-decider-v1-27b"
PPLX_USD_PER_INPUT_TOKEN = 0.04 / 1_000_000
DEFAULT_CLAUDE_MODEL = "claude-sonnet-5"
CLAUDE_USD_PER_INPUT_TOKEN = 2.0 / 1_000_000
CLAUDE_USD_PER_OUTPUT_TOKEN = 10.0 / 1_000_000
DEFAULT_CLAUDE_CACHE_DIR = Path.home() / ".cache" / "claude-classifier"
DEFAULT_PPLX_CACHE_DIR = Path.home() / ".cache" / "pplx-decider"
MAX_CHOICE_OPTIONS = 255
MAX_SCORE_LEVELS = 10
RETRY_STATUSES = {429, 500, 502, 503, 504, 520, 529}
MAX_ATTEMPTS = 6
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "jev-classifier"
NONE_OPTION_KEY = "none_of_the_above"

PLACEHOLDER_RE = re.compile(r"\{\{\s*(input(?:\.[^{}\s]+)?)\s*\}\}")


class ClassifierError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Classifier definition
# ---------------------------------------------------------------------------


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return PLACEHOLDER_RE.search(value) is not None
    if isinstance(value, dict):
        return any(_contains_placeholder(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_placeholder(v) for v in value)
    return False


def _is_nonempty_text_or_struct(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, (dict, list)) and bool(value)


def _validate_two_level(clf: dict) -> dict:
    template = clf.get("state_template", "{{input}}")
    if not _is_nonempty_text_or_struct(template) or not _contains_placeholder(template):
        raise ClassifierError("invalid classifier: two_level state_template must contain an {{input}} placeholder")

    def sub(spec: Any, where: str) -> dict:
        if not isinstance(spec, dict):
            raise ClassifierError(f"invalid classifier: {where} must be an object")
        try:
            return validate_classifier({
                "type": "choice",
                "instructions": spec.get("instructions"),
                "criteria": spec.get("criteria"),
                **({"map": spec["map"]} if "map" in spec else {}),
                "state_template": template,
            })
        except ClassifierError as e:
            raise ClassifierError(f"{where}: {e}") from e

    router = sub(clf.get("router"), "router")
    groups = clf.get("groups")
    if not isinstance(groups, dict) or {k.strip() for k in groups} != set(router["criteria"]):
        raise ClassifierError("invalid classifier: groups must have exactly one entry per router option")
    normalized_groups: dict[str, dict] = {}
    for name, spec in groups.items():
        if isinstance(spec, dict) and set(spec) == {"class"} and isinstance(spec["class"], str) and spec["class"].strip():
            normalized_groups[name.strip()] = {"class": spec["class"].strip()}
            continue
        leaf = sub(spec, f"group {name!r}")
        normalized_groups[name.strip()] = {
            "instructions": leaf["instructions"],
            "criteria": leaf["criteria"],
            "map": leaf.get("map") or {k: k for k in leaf["criteria"]},
        }
    normalized = {
        "version": clf.get("version", FORMAT_VERSION),
        "name": clf.get("name") or "classifier",
        "model": clf.get("model") or DEFAULT_MODEL,
        "type": "two_level",
        "state_template": template,
        "router": {"instructions": router["instructions"], "criteria": router["criteria"]},
        "groups": normalized_groups,
    }
    if clf.get("description"):
        normalized["description"] = clf["description"]
    return normalized


def _validate_criteria(clf: dict) -> dict:
    template = clf.get("state_template", "{{input}}")
    if not _is_nonempty_text_or_struct(template) or not _contains_placeholder(template):
        raise ClassifierError("invalid classifier: criteria state_template must contain an {{input}} placeholder")
    questions = clf.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ClassifierError("invalid classifier: criteria needs a non-empty 'questions' object")
    normalized_questions: dict[str, dict] = {}
    for name, spec in questions.items():
        if not isinstance(spec, dict):
            raise ClassifierError(f"invalid classifier: question {name!r} must be an object")
        try:
            q = validate_classifier({
                "type": "noul",
                "instructions": spec.get("instructions"),
                **({"criteria": spec["criteria"]} if "criteria" in spec else {}),
                "state_template": template,
            })
        except ClassifierError as e:
            raise ClassifierError(f"question {name!r}: {e}") from e
        normalized_questions[name.strip()] = {k: q[k] for k in ("instructions", "criteria") if k in q}

    rule = clf.get("rule")
    if not isinstance(rule, list) or not rule or not all(isinstance(c, list) and c for c in rule):
        raise ClassifierError("invalid classifier: rule must be a non-empty list of non-empty lists")
    for clause in rule:
        for ref in clause:
            if not isinstance(ref, str) or ref.lstrip("!").strip() not in normalized_questions:
                raise ClassifierError(f"invalid classifier: rule refers to unknown question {ref!r}")
    positive, negative = clf.get("positive"), clf.get("negative")
    if not (isinstance(positive, str) and isinstance(negative, str) and positive.strip() and negative.strip()
            and positive.strip() != negative.strip()):
        raise ClassifierError("invalid classifier: criteria needs distinct 'positive' and 'negative' class names")

    normalized = {
        "version": clf.get("version", FORMAT_VERSION),
        "name": clf.get("name") or "classifier",
        "model": clf.get("model") or DEFAULT_MODEL,
        "type": "criteria",
        "state_template": template,
        "questions": normalized_questions,
        "rule": [[ref.strip() for ref in clause] for clause in rule],
        "positive": positive.strip(),
        "negative": negative.strip(),
    }
    if clf.get("description"):
        normalized["description"] = clf["description"]
    return normalized


def _validate_ensemble(clf: dict) -> dict:
    members = clf.get("members")
    if not isinstance(members, list) or len(members) < 2:
        raise ClassifierError("invalid classifier: ensemble needs at least 2 members")
    normalized_members = []
    for i, member in enumerate(members):
        if not isinstance(member, dict) or member.get("type") in ("ensemble", "noul", "score") or "include" in member:
            raise ClassifierError(
                f"invalid classifier: ensemble member {i} must be a choice, two_level or criteria classifier")
        if "decision" in member:
            raise ClassifierError(f"invalid classifier: ensemble member {i} may not set a decision; set it on the ensemble")
        try:
            normalized_members.append(validate_classifier(member))
        except ClassifierError as e:
            raise ClassifierError(f"ensemble member {i}: {e}") from e
    weights = clf.get("weights")
    if weights is not None and not (
        isinstance(weights, list) and len(weights) == len(members)
        and all(isinstance(w, (int, float)) and w > 0 for w in weights)
    ):
        raise ClassifierError("invalid classifier: weights must be one positive number per member")
    normalized = {
        "version": clf.get("version", FORMAT_VERSION),
        "name": clf.get("name") or "classifier",
        "type": "ensemble",
        "members": normalized_members,
    }
    if weights is not None:
        normalized["weights"] = weights
    if clf.get("description"):
        normalized["description"] = clf["description"]
    return normalized


def classes_of(clf: dict) -> set[str] | None:
    """Output classes of a normalized classifier, or None for noul/score/include."""
    qtype = clf["type"]
    if qtype == "two_level":
        out: set[str] = set()
        for spec in clf["groups"].values():
            if "class" in spec:
                out.add(spec["class"])
            else:
                out.update(spec["map"].values())
        return out
    if qtype == "criteria":
        return {clf["positive"], clf["negative"]}
    if qtype == "ensemble":
        return set().union(*(classes_of(m) or set() for m in clf["members"]))
    if qtype == "choice" and "map" in clf:
        return set(clf["map"].values())
    if qtype == "choice" and "include" not in clf:
        return set(clf["criteria"])
    return None


def _validate_decision(decision: Any, clf: dict) -> dict:
    if clf["type"] not in ("two_level", "criteria", "ensemble") and "map" not in clf:
        raise ClassifierError("invalid classifier: decision needs a choice with map, two_level, criteria or ensemble")
    if not isinstance(decision, dict) or set(decision) != {"class", "threshold"}:
        raise ClassifierError('invalid classifier: decision must be {"class": ..., "threshold": ...}')
    cls, threshold = decision["class"], decision["threshold"]
    if cls not in (classes_of(clf) or set()):
        raise ClassifierError(f"invalid classifier: decision class {cls!r} is not an output class")
    if not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
        raise ClassifierError("invalid classifier: decision threshold must be between 0 and 1")
    return {"class": cls, "threshold": float(threshold)}


def validate_classifier(clf: Any) -> dict:
    """Validate and normalize a classifier dict. Raises ClassifierError."""
    if not isinstance(clf, dict):
        raise ClassifierError("classifier must be a JSON object")
    validators = {"two_level": _validate_two_level, "criteria": _validate_criteria, "ensemble": _validate_ensemble}
    normalized = validators.get(clf.get("type"), _validate_single)(clf)
    if clf.get("decision") is not None:
        normalized["decision"] = _validate_decision(clf["decision"], normalized)
    return normalized


def _validate_single(clf: dict) -> dict:
    problems: list[str] = []
    qtype = clf.get("type")
    if qtype not in ("choice", "noul", "score"):
        problems.append(f"type must be 'choice', 'noul' or 'score', got {qtype!r}")

    if not _is_nonempty_text_or_struct(clf.get("instructions")):
        problems.append("instructions must be a non-empty string, object or array")

    template = clf.get("state_template", "{{input}}")
    if not (_is_nonempty_text_or_struct(template)):
        problems.append("state_template must be a non-empty string, object or array")
    elif not (_contains_placeholder(template) or _contains_placeholder(clf.get("instructions"))):
        problems.append("state_template (or instructions) must contain an {{input}} placeholder")

    criteria = clf.get("criteria")
    if qtype == "choice":
        if not isinstance(criteria, dict):
            problems.append("choice criteria must be an object of option -> description|null")
        else:
            stripped = [k.strip() for k in criteria]
            if len(criteria) < 2:
                problems.append("choice needs at least 2 options")
            if len(criteria) > MAX_CHOICE_OPTIONS:
                problems.append(f"choice allows at most {MAX_CHOICE_OPTIONS} options, got {len(criteria)}")
            if any(not k for k in stripped):
                problems.append("choice option keys must be non-empty")
            if len(set(stripped)) != len(stripped):
                problems.append("choice option keys must be unique after stripping whitespace")
            for k, v in criteria.items():
                if v is not None and not isinstance(v, (str, dict, list)):
                    problems.append(f"description for option {k!r} must be a string, object, array or null")
            if not problems:
                criteria = {k.strip(): v for k, v in criteria.items()}
    if qtype != "choice" and "include" in clf:
        problems.append("include is only valid for choice classifiers")
    if qtype != "choice" and "map" in clf:
        problems.append("map is only valid for choice classifiers")
    if "include" in clf and "map" in clf:
        problems.append("use either include or map, not both")

    option_map = clf.get("map")
    if qtype == "choice" and option_map is not None and isinstance(criteria, dict):
        if not isinstance(option_map, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in option_map.items()
        ):
            problems.append("map must be an object of option key -> non-empty class name")
        else:
            option_map = {k.strip(): v.strip() for k, v in option_map.items()}
            unknown = [k for k in option_map if k not in criteria]
            if unknown:
                problems.append(f"map lists keys that are not options: {unknown}")

    include = clf.get("include")
    if qtype == "choice" and include is not None and isinstance(criteria, dict):
        if not isinstance(include, list) or not all(isinstance(k, str) for k in include):
            problems.append("include must be an array of option keys")
        else:
            include = [k.strip() for k in include]
            unknown = [k for k in include if k not in criteria]
            if unknown:
                problems.append(f"include lists keys that are not options: {unknown}")
            if not include or len(set(include)) >= len(criteria):
                problems.append("include must name at least one option and leave at least one option out")

    if qtype == "score":
        if not isinstance(criteria, list):
            problems.append("score criteria must be an ordered array of level descriptions")
        elif not 2 <= len(criteria) <= MAX_SCORE_LEVELS:
            problems.append(f"score needs 2-{MAX_SCORE_LEVELS} levels, got {len(criteria)}")
        elif not all(_is_nonempty_text_or_struct(level) for level in criteria):
            problems.append("score levels must be non-empty descriptions")
    elif qtype == "noul" and criteria is not None:
        if not isinstance(criteria, dict) or not set(criteria) <= {"true", "false"}:
            problems.append("noul criteria must be an object with optional 'true'/'false' keys")

    if problems:
        raise ClassifierError("invalid classifier:\n  - " + "\n  - ".join(problems))

    normalized = {
        "version": clf.get("version", FORMAT_VERSION),
        "name": clf.get("name") or "classifier",
        "model": clf.get("model") or DEFAULT_MODEL,
        "type": qtype,
        "instructions": clf["instructions"],
        "state_template": template,
    }
    if clf.get("description"):
        normalized["description"] = clf["description"]
    if criteria is not None:
        normalized["criteria"] = criteria
    if qtype == "choice" and include is not None:
        normalized["include"] = include
    if qtype == "choice" and option_map is not None:
        normalized["map"] = {k: option_map.get(k, k) for k in criteria}
    return normalized


def load_classifier(path: str) -> dict:
    try:
        raw = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise ClassifierError(f"{path} is not valid JSON: {e}") from e
    return validate_classifier(raw)


# ---------------------------------------------------------------------------
# Template rendering and payloads
# ---------------------------------------------------------------------------


def _lookup(item: Any, ref: str) -> Any:
    value = item
    for part in ref.split(".")[1:]:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise KeyError(f"placeholder {{{{{ref}}}}} not found in input")
    return value


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def render(template: Any, item: Any) -> Any:
    if isinstance(template, str):
        whole = PLACEHOLDER_RE.fullmatch(template)
        if whole:
            return _lookup(item, whole.group(1))
        return PLACEHOLDER_RE.sub(lambda m: _as_text(_lookup(item, m.group(1))), template)
    if isinstance(template, dict):
        return {k: render(v, item) for k, v in template.items()}
    if isinstance(template, list):
        return [render(v, item) for v in template]
    return template


def _group_question_ids(clf: dict) -> dict[str, str]:
    return {g: f"g{i}" for i, g in enumerate(clf["groups"]) if "class" not in clf["groups"][g]}


def _criteria_question_ids(clf: dict) -> dict[str, str]:
    return {name: f"c{i}" for i, name in enumerate(clf["questions"])}


# Types whose interpret() takes the whole answers dict rather than one answer.
MULTI_QUESTION_TYPES = ("two_level", "criteria")


def build_payload(clf: dict, item: Any) -> dict:
    if clf["type"] == "ensemble":
        return {"members": [build_payload(m, item) for m in clf["members"]]}
    if clf["type"] == "criteria":
        questions = {}
        for name, qid in _criteria_question_ids(clf).items():
            spec = clf["questions"][name]
            questions[qid] = {"type": "noul", "instructions": render(spec["instructions"], item)}
            if "criteria" in spec:
                questions[qid]["criteria"] = spec["criteria"]
        return {"model": clf["model"], "state": render(clf["state_template"], item), "questions": questions}
    if clf["type"] == "two_level":
        questions = {"router": {
            "type": "choice",
            "instructions": render(clf["router"]["instructions"], item),
            "criteria": clf["router"]["criteria"],
        }}
        for group, qid in _group_question_ids(clf).items():
            spec = clf["groups"][group]
            questions[qid] = {
                "type": "choice",
                "instructions": render(spec["instructions"], item),
                "criteria": spec["criteria"],
            }
        return {"model": clf["model"], "state": render(clf["state_template"], item), "questions": questions}
    question: dict[str, Any] = {
        "type": clf["type"],
        "instructions": render(clf["instructions"], item),
    }
    if "criteria" in clf:
        question["criteria"] = clf["criteria"]
    return {
        "model": clf["model"],
        "state": render(clf["state_template"], item),
        "questions": {QUESTION_ID: question},
    }


# ---------------------------------------------------------------------------
# API client with retries and cache
# ---------------------------------------------------------------------------


class ServiceError(RuntimeError):
    """Jev could not answer (network, rate limit, 5xx, or rejected request)."""


@dataclass
class Call:
    response: dict
    latency_ms: float | None
    cached: bool


class JevClient:
    """Calls Jev, or another System One endpoint with the same request schema
    (Perplexity's Decisions API) when given its URL, key name and model."""

    def __init__(self, api_key: str | None, cache_dir: Path | None, timeout: float,
                 url: str = API_URL, key_name: str = "TYPESAFE_API_KEY", model: str | None = None):
        self.api_key = api_key
        self.url = url
        self.key_name = key_name
        self.model = model
        self.cache_dir = cache_dir
        self.http = httpx.Client(timeout=timeout)
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _prepare(self, payload: dict) -> dict:
        return {**payload, "model": self.model} if self.model else payload

    def _cache_path(self, payload: dict) -> Path | None:
        if not self.cache_dir:
            return None
        payload = self._prepare(payload)
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def is_cached(self, payload: dict) -> bool:
        path = self._cache_path(payload)
        return bool(path and path.exists())

    @staticmethod
    def _write_cache(path: Path, body: dict) -> None:
        # Identical inputs in one run race on the same cache entry, so each
        # writer needs its own temp file.
        tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            tmp.write_text(json.dumps(body))
            tmp.replace(path)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            print(f"warning: could not cache response: {e}", file=sys.stderr)

    def call(self, payload: dict) -> Call:
        path = self._cache_path(payload)
        if path and path.exists():
            return Call(json.loads(path.read_text()), None, True)
        if not self.api_key:
            raise ServiceError(f"{self.key_name} not set")
        payload = self._prepare(payload)

        delay = 1.0
        last_error = ""
        for attempt in range(MAX_ATTEMPTS):
            start = time.monotonic()
            try:
                resp = self.http.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            except httpx.HTTPError as e:
                last_error = f"{type(e).__name__}: {e}"
            else:
                latency_ms = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    body = resp.json()
                    if path:
                        self._write_cache(path, body)
                    return Call(body, latency_ms, False)
                last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                if resp.status_code not in RETRY_STATUSES:
                    raise ServiceError(last_error)
                retry_after = resp.headers.get("retry-after", "")
                if retry_after.replace(".", "", 1).isdigit():
                    delay = max(delay, float(retry_after))
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
        raise ServiceError(f"gave up after {MAX_ATTEMPTS} attempts: {last_error}")


class LunaClient:
    """Answers Jev request payloads with an OpenAI model, one call per question.

    Each question is restated as a prompt (the rendered state as context, the
    instructions as the question, the options with their descriptions) and the
    model answers in JSON with a verbalized 0-1 confidence, as in the sales
    benchmark. Responses come back in Jev's shape so interpret() is unchanged: a
    choice gives the chosen option the stated confidence and spreads the rest
    evenly over the other options.
    """

    REASONING_MAX_OUTPUT = {"none": 256, "low": 8192, "medium": 16384, "high": 32768}
    KEY_NAME = "OPENAI_API_KEY"

    def __init__(self, model: str, reasoning: str, cache_dir: Path | None, timeout: float, workers: int = 16):
        from openai import OpenAI

        self.model = model
        self.reasoning = reasoning
        self.cache_dir = cache_dir
        key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key, timeout=timeout, max_retries=MAX_ATTEMPTS) if key else None
        self.pool = ThreadPoolExecutor(max_workers=workers)
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, prompt: str) -> Path | None:
        if not self.cache_dir:
            return None
        blob = json.dumps({"model": self.model, "reasoning": self.reasoning, "prompt": prompt}, sort_keys=True)
        return self.cache_dir / f"{hashlib.sha256(blob.encode()).hexdigest()}.json"

    def is_cached(self, payload: dict) -> bool:
        return all(
            (p := self._cache_path(self._prompt(payload["state"], q)[0])) is not None and p.exists()
            for q in payload["questions"].values()
        )

    @staticmethod
    def _text(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)

    def _prompt(self, state: Any, q: dict) -> tuple[str, list[str]]:
        head = f"CONTEXT:\n{self._text(state)}\n\nQUESTION: {self._text(q['instructions'])}\n\n"
        criteria = q.get("criteria")
        if q["type"] == "noul":
            meaning = ""
            if isinstance(criteria, dict):
                meaning = "".join(
                    f"{'Yes' if k == 'true' else 'No'} means: {v}\n" for k, v in criteria.items() if v
                )
            return head + meaning + (meaning and "\n") + (
                'Answer with JSON only: {"answer": "yes" or "no", '
                '"confidence": a number 0-1 for how sure you are}.'
            ), ["yes", "no"]
        if q["type"] == "score":
            levels = "\n".join(f"{i}: {level}" for i, level in enumerate(criteria))
            return head + (
                f"Rate on this ordered scale:\n{levels}\n\n"
                'Answer with JSON only: {"level": <integer index>, "confidence": 0-1}.'
            ), [str(i) for i in range(len(criteria))]
        opts = "\n".join(f"- {k}" + (f": {v}" if v else "") for k, v in criteria.items())
        return head + (
            f"Choose exactly one option:\n{opts}\n\n"
            'Answer with JSON only: {"choice": "<one option name verbatim, without its description>", '
            '"confidence": a number 0-1}.'
        ), list(criteria)

    def _ask(self, state: Any, q: dict) -> tuple[dict, dict, bool, float | None]:
        prompt, keys = self._prompt(state, q)
        path = self._cache_path(prompt)
        if path and path.exists():
            body = json.loads(path.read_text())
            return body["answer"], body["usage"], True, None
        if self.client is None:
            raise ServiceError(f"{self.KEY_NAME} not set")
        schema = self._schema(q["type"], keys)
        start = time.monotonic()
        try:
            text, usage = self._complete(prompt, schema)
        except Exception as e:
            raise ServiceError(f"{type(e).__name__}: {e}") from e
        latency_ms = (time.monotonic() - start) * 1000
        answer = self._answer(q["type"], keys, text)
        if path:
            JevClient._write_cache(path, {"answer": answer, "usage": usage, "text": text})
        return answer, usage, False, latency_ms

    @staticmethod
    def _schema(qtype: str, keys: list[str]) -> dict:
        field = {"noul": "answer", "score": "level"}.get(qtype, "choice")
        return {
            "type": "object",
            "properties": {field: {"type": "string", "enum": keys}, "confidence": {"type": "number"}},
            "required": [field, "confidence"],
            "additionalProperties": False,
        }

    def _complete(self, prompt: str, schema: dict) -> tuple[str, dict]:
        resp = self.client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=self.REASONING_MAX_OUTPUT[self.reasoning],
            reasoning={"effort": self.reasoning},
            text={"format": {"type": "json_schema", "name": "answer", "strict": True, "schema": schema}},
        )
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        return resp.output_text or "", usage

    @staticmethod
    def _match_option(raw: str, keys: list[str]) -> str | None:
        # The model often writes a key as words ("task related inquiry" for
        # task_related_inquiry) or prefixes it with its description.
        def norm(x: str) -> str:
            return re.sub(r"[^a-z0-9]+", " ", x.lower()).strip()

        by_norm = {norm(k): k for k in keys}
        for candidate in (raw, raw.split(":")[0]):
            if norm(candidate) in by_norm:
                return by_norm[norm(candidate)]
        return None

    @staticmethod
    def _answer(qtype: str, keys: list[str], text: str) -> dict:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        try:
            obj = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            obj = None
        if not isinstance(obj, dict):
            raise ServiceError(f"no JSON answer: {text[:200]!r}")
        try:
            c = min(1.0, max(0.0, float(obj.get("confidence", 1.0))))
        except (TypeError, ValueError):
            c = 1.0
        if qtype == "noul":
            word = str(obj.get("answer", "")).strip().lower()
            if word not in ("yes", "no"):
                raise ServiceError(f"bad yes/no answer: {text[:200]!r}")
            p_yes = c if word == "yes" else 1.0 - c
            return {"noul": p_yes, "confidence": c}
        if qtype == "score":
            raw = str(obj.get("level", "")).strip()
            if raw not in keys:
                raise ServiceError(f"bad level: {text[:200]!r}")
            chosen = raw
        else:
            raw = str(obj.get("choice", "")).strip()
            chosen = raw if raw in keys else LunaClient._match_option(raw, keys)
            if chosen is None:
                raise ServiceError(f"choice not in options: {raw[:120]!r}")
        rest = (1.0 - c) / (len(keys) - 1)
        probs = {k: (c if k == chosen else rest) for k in keys}
        # A stated confidence below one half on two options favours the other one;
        # report that option so plain choice agrees with mapped classifiers.
        if len(keys) == 2 and rest > c:
            chosen = next(k for k in keys if k != chosen)
        if qtype == "score":
            return {"score": float(chosen), "confidence": c, "probabilities": probs}
        return {"choice": chosen, "confidence": c, "probabilities": probs}

    def call(self, payload: dict) -> Call:
        state, questions = payload["state"], payload["questions"]
        futures = {qid: self.pool.submit(self._ask, state, q) for qid, q in questions.items()}
        answers, input_tokens, output_tokens, cached, latencies = {}, 0, 0, True, []
        for qid, fut in futures.items():
            answer, usage, hit, latency_ms = fut.result()
            answers[qid] = answer
            if not hit:
                input_tokens += usage["input_tokens"]
                output_tokens += usage["output_tokens"]
            cached = cached and hit
            if latency_ms is not None:
                latencies.append(latency_ms)
        response = {"answers": answers, "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}}
        return Call(response, max(latencies) if latencies else None, cached)


class ClaudeClient(LunaClient):
    """The Luna prompt answered by a Claude model with thinking disabled.

    The answer comes back as the input of a forced `answer` tool whose schema
    restricts the option to the question's keys.
    """

    KEY_NAME = "ANTHROPIC_API_KEY"

    def __init__(self, model: str, cache_dir: Path | None, timeout: float, workers: int = 8):
        from anthropic import Anthropic

        self.model = model
        self.reasoning = "none"
        self.cache_dir = cache_dir
        key = os.environ.get("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=key, timeout=timeout, max_retries=MAX_ATTEMPTS) if key else None
        self.pool = ThreadPoolExecutor(max_workers=workers)
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def request_params(self, prompt: str, schema: dict) -> dict:
        return {
            "model": self.model,
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{"name": "answer", "description": "Record your answer.", "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": "answer"},
        }

    @staticmethod
    def parse_message(msg: Any) -> tuple[str, dict]:
        tool_input = next((b.input for b in msg.content if getattr(b, "type", None) == "tool_use"), None)
        usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens}
        return json.dumps(tool_input) if tool_input is not None else "", usage

    def pending(self, payload: dict) -> list[tuple[Path, dict, str, list[str]]]:
        """Uncached questions of a payload as (cache path, request params, question type, option keys)."""
        out = []
        for q in payload["questions"].values():
            prompt, keys = self._prompt(payload["state"], q)
            path = self._cache_path(prompt)
            if path and not path.exists():
                out.append((path, self.request_params(prompt, self._schema(q["type"], keys)), q["type"], keys))
        return out

    def store(self, path: Path, qtype: str, keys: list[str], text: str, usage: dict) -> None:
        JevClient._write_cache(path, {"answer": self._answer(qtype, keys, text), "usage": usage, "text": text})

    def _complete(self, prompt: str, schema: dict) -> tuple[str, dict]:
        return self.parse_message(self.client.messages.create(**self.request_params(prompt, schema)))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass
class Example:
    id: Any
    input: Any
    label: Any = None


def _read_records(path: str) -> list[Any]:
    if path == "-":
        text, suffix = sys.stdin.read(), ".jsonl"
    else:
        text, suffix = Path(path).read_text(), Path(path).suffix.lower()

    if suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ClassifierError(f"{path}: a .json inputs file must contain an array")
        return data
    if suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if suffix == ".csv":
        return list(csv.DictReader(text.splitlines()))
    return [line for line in text.splitlines() if line.strip()]


def load_examples(
    path: str | None,
    texts: list[str],
    input_field: str | None,
    label_field: str | None,
    id_field: str,
) -> list[Example]:
    records: list[Any] = list(texts)
    if path:
        records.extend(_read_records(path))

    examples = []
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            examples.append(Example(id=idx, input=rec))
            continue
        label = rec.get(label_field) if label_field else None
        ex_id = rec.get(id_field, idx)
        if input_field:
            if input_field not in rec:
                raise ClassifierError(f"record {idx} has no field {input_field!r}")
            value = rec[input_field]
        else:
            value = {k: v for k, v in rec.items() if k not in (label_field, id_field)}
        examples.append(Example(id=ex_id, input=value, label=label))
    return examples


# ---------------------------------------------------------------------------
# Answers and scoring
# ---------------------------------------------------------------------------

TRUE_STRINGS = {"true", "yes", "y", "1", "t"}
FALSE_STRINGS = {"false", "no", "n", "0", "f"}


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in TRUE_STRINGS:
            return True
        if v in FALSE_STRINGS:
            return False
    return None


def _parse_level(value: Any, levels: list) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if v.lstrip("-").isdigit():
            return int(v)
        for i, level in enumerate(levels):
            if isinstance(level, str) and level.strip() == v:
                return i
    return None


def _decide(clf: dict, class_probs: dict[str, float]) -> str:
    decision = clf.get("decision")
    if decision:
        cls = decision["class"]
        if class_probs.get(cls, 0.0) >= decision["threshold"]:
            return cls
        others = {c: p for c, p in class_probs.items() if c != cls}
        if others:
            return max(others, key=lambda c: others[c])
        rest = sorted((classes_of(clf) or set()) - {cls})
        return rest[0] if rest else cls
    return max(class_probs, key=lambda c: class_probs[c])


def _margin(clf: dict, class_probs: dict[str, float]) -> float:
    """How far the record is from flipping: 2 x distance from a stored decision
    threshold, else top class probability minus the second (equal for a binary
    task at threshold 0.5)."""
    decision = clf.get("decision")
    if decision:
        return round(2 * abs(class_probs.get(decision["class"], 0.0) - decision["threshold"]), 4)
    top = sorted(class_probs.values(), reverse=True) + [0.0]
    return round(top[0] - top[1], 4)


def interpret(clf: dict, answer: dict, gold: Any, threshold: float) -> dict:
    qtype = clf["type"]
    out: dict[str, Any] = {}
    if qtype == "criteria":
        # `answer` is the whole answers dict: one noul answer per question.
        p_yes = {name: answer[qid]["noul"] for name, qid in _criteria_question_ids(clf).items()}
        clause_probs = []
        for clause in clf["rule"]:
            p = 1.0
            for ref in clause:
                name = ref.lstrip("!")
                p *= (1.0 - p_yes[name]) if ref.startswith("!") else p_yes[name]
            clause_probs.append(p)
        p_none = 1.0
        for p in clause_probs:
            p_none *= 1.0 - p
        class_probs = {clf["positive"]: 1.0 - p_none, clf["negative"]: p_none}
        best = _decide(clf, class_probs)
        top = max(range(len(clause_probs)), key=lambda i: clause_probs[i])
        out["prediction"] = best
        out["confidence"] = class_probs[best]
        out["category"] = "&".join(clf["rule"][top]) if clause_probs[top] >= 0.5 else "none"
        out["criteria_p"] = {name: round(p, 4) for name, p in p_yes.items()}
        out["class_probabilities"] = {c: round(p, 4) for c, p in class_probs.items()}
        out["margin"] = _margin(clf, class_probs)
        if gold is not None:
            out["gold"] = str(gold).strip()
            out["correct"] = out["gold"] == best
    elif qtype == "two_level":
        # `answer` is the whole answers dict: the router plus every group's question.
        p_group = answer["router"]["probabilities"]
        qids = _group_question_ids(clf)
        class_probs: dict[str, float] = {}
        paths: dict[str, float] = {}
        for group, spec in clf["groups"].items():
            pg = p_group.get(group, 0.0)
            if "class" in spec:
                class_probs[spec["class"]] = class_probs.get(spec["class"], 0.0) + pg
                paths[group] = pg
                continue
            for option, q in answer[qids[group]]["probabilities"].items():
                cls = spec["map"].get(option, option)
                class_probs[cls] = class_probs.get(cls, 0.0) + pg * q
                paths[f"{group}/{option}"] = pg * q
        best = _decide(clf, class_probs)
        out["prediction"] = best
        out["confidence"] = min(1.0, class_probs[best])
        out["category"] = max(paths, key=lambda k: paths[k])
        out["group"] = answer["router"]["choice"]
        out["group_probabilities"] = {g: p for g, p in p_group.items() if p > 0}
        out["class_probabilities"] = {c: round(p, 4) for c, p in class_probs.items() if p >= 0.001}
        out["margin"] = _margin(clf, class_probs)
        if gold is not None:
            out["gold"] = str(gold).strip()
            out["correct"] = out["gold"] == best
    elif qtype == "choice" and "include" in clf:
        probs = answer["probabilities"]
        p = min(1.0, sum(probs.get(k, 0.0) for k in clf["include"]))
        out["prediction"] = p >= threshold
        out["p_yes"] = p
        out["confidence"] = max(p, 1 - p)
        out["category"] = answer["choice"]
        out["probabilities"] = probs
        if gold is not None:
            g = _parse_bool(gold)
            if g is None and str(gold).strip() in clf["criteria"]:
                g = str(gold).strip() in clf["include"]
            if g is not None:
                out["gold"] = g
                out["correct"] = out["prediction"] == g
                out["sq_error"] = (p - float(g)) ** 2
    elif qtype == "choice" and "map" in clf:
        probs = answer["probabilities"]
        class_probs: dict[str, float] = {}
        for option, cls in clf["map"].items():
            class_probs[cls] = class_probs.get(cls, 0.0) + probs.get(option, 0.0)
        best = _decide(clf, class_probs)
        out["prediction"] = best
        out["confidence"] = min(1.0, class_probs[best])
        out["category"] = answer["choice"]
        out["class_probabilities"] = {c: round(p, 4) for c, p in class_probs.items()}
        out["margin"] = _margin(clf, class_probs)
        out["probabilities"] = probs
        if gold is not None:
            out["gold"] = str(gold).strip()
            out["correct"] = out["gold"] == best
    elif qtype == "choice":
        out["prediction"] = answer["choice"]
        out["confidence"] = answer.get("confidence")
        out["probabilities"] = answer.get("probabilities")
        out["margin"] = _margin(clf, answer.get("probabilities") or {})
        if gold is not None:
            out["gold"] = str(gold).strip()
            out["correct"] = out["gold"] == answer["choice"]
    elif qtype == "noul":
        p = answer["noul"]
        out["prediction"] = p >= threshold
        out["p_yes"] = p
        out["confidence"] = max(p, 1 - p)
        if gold is not None:
            g = _parse_bool(gold)
            if g is not None:
                out["gold"] = g
                out["correct"] = out["prediction"] == g
                out["sq_error"] = (p - float(g)) ** 2
    else:
        s = answer["score"]
        out["prediction"] = round(s)
        out["score"] = s
        out["confidence"] = answer.get("confidence")
        out["probabilities"] = answer.get("probabilities")
        if gold is not None:
            g = _parse_level(gold, clf["criteria"])
            if g is not None:
                out["gold"] = g
                out["correct"] = out["prediction"] == g
                out["abs_error"] = abs(s - g)
    return out


def _interpret_ensemble(clf: dict, answers: list[dict], gold: Any, threshold: float) -> dict:
    outs = [interpret(m, a, None, threshold) for m, a in zip(clf["members"], answers)]
    weights = clf.get("weights") or [1.0] * len(outs)
    total = sum(weights)
    class_probs: dict[str, float] = {}
    for w, o in zip(weights, outs):
        for c, p in (o.get("class_probabilities") or o.get("probabilities") or {}).items():
            class_probs[c] = class_probs.get(c, 0.0) + w * p / total
    best = _decide(clf, class_probs)
    votes = [str(o["prediction"]) for o in outs]
    out: dict[str, Any] = {
        "prediction": best,
        "confidence": min(1.0, class_probs[best]),
        "category": f"{sum(v == best for v in votes)}/{len(votes)} agree",
        "class_probabilities": {c: round(p, 4) for c, p in class_probs.items() if p >= 0.001},
        "margin": _margin(clf, class_probs),
        "member_predictions": votes,
        "disagreement": len(set(votes)) > 1,
    }
    if gold is not None:
        out["gold"] = str(gold).strip()
        out["correct"] = out["gold"] == best
    return out


def classify(client: JevClient, clf: dict, ex: Example, threshold: float) -> dict:
    record: dict[str, Any] = {"id": ex.id, "input": ex.input}
    if ex.label is not None:
        record["label"] = ex.label
    members = clf["members"] if clf["type"] == "ensemble" else [clf]
    try:
        payloads = [build_payload(m, ex.input) for m in members]
    except KeyError as e:
        record["error"] = {"kind": "template", "message": str(e.args[0])}
        return record
    try:
        calls = [client.call(p) for p in payloads]
        answers = [
            c.response["answers"] if m["type"] in MULTI_QUESTION_TYPES else c.response["answers"][QUESTION_ID]
            for m, c in zip(members, calls)
        ]
        if clf["type"] == "ensemble":
            record.update(_interpret_ensemble(clf, answers, ex.label, threshold))
        else:
            record.update(interpret(clf, answers[0], ex.label, threshold))
    except ServiceError as e:
        record["error"] = {"kind": "service", "message": str(e)}
        return record
    except (KeyError, TypeError, ValueError) as e:
        record["error"] = {"kind": "bad_response", "message": f"{type(e).__name__}: {e}"}
        return record
    except Exception as e:
        record["error"] = {"kind": "unexpected", "message": f"{type(e).__name__}: {e}"}
        return record
    if len(calls) == 1:
        record["usage"] = calls[0].response.get("usage")
    else:
        record["usage"] = {
            k: sum((c.response.get("usage") or {}).get(k, 0) for c in calls) for k in ("input_tokens", "output_tokens")
        }
    latencies = [c.latency_ms for c in calls if c.latency_ms is not None]
    record["latency_ms"] = round(sum(latencies), 1) if latencies else None
    record["cached"] = all(c.cached for c in calls)
    return record


CONFIDENCE_BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
TOP_CONFUSIONS = 15


def class_metrics(labeled: list[dict]) -> dict:
    """Macro-F1 over the gold classes, per-class precision/recall/F1, and top confusions."""
    gold = [str(r["gold"]) for r in labeled]
    pred = [str(r["prediction"]) for r in labeled]
    per_class = {}
    f1s = []
    for cls in sorted(set(gold)):
        tp = sum(g == cls and p == cls for g, p in zip(gold, pred))
        n_pred = sum(p == cls for p in pred)
        n_gold = sum(g == cls for g in gold)
        precision = tp / n_pred if n_pred else 0.0
        recall = tp / n_gold
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        per_class[cls] = {"n": n_gold, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    confusions: dict[tuple[str, str], int] = {}
    for g, p in zip(gold, pred):
        if g != p:
            confusions[(g, p)] = confusions.get((g, p), 0) + 1
    top = sorted(confusions.items(), key=lambda kv: -kv[1])[:TOP_CONFUSIONS]
    return {
        "macro_f1": round(sum(f1s) / len(f1s), 4),
        "per_class": per_class,
        "top_confusions": [{"gold": g, "predicted": p, "n": n} for (g, p), n in top],
    }


def summarize(clf: dict, results: list[dict], backend: str = "jev") -> dict:
    ok = [r for r in results if "error" not in r]
    errors: dict[str, int] = {}
    for r in results:
        if "error" in r:
            errors[r["error"]["kind"]] = errors.get(r["error"]["kind"], 0) + 1

    input_tokens = sum((r.get("usage") or {}).get("input_tokens", 0) for r in ok if not r.get("cached"))
    output_tokens = sum((r.get("usage") or {}).get("output_tokens", 0) for r in ok if not r.get("cached"))
    if backend == "luna":
        cost = input_tokens * LUNA_USD_PER_INPUT_TOKEN + output_tokens * LUNA_USD_PER_OUTPUT_TOKEN
    elif backend == "pplx":
        cost = input_tokens * PPLX_USD_PER_INPUT_TOKEN
    elif backend == "claude":
        cost = input_tokens * CLAUDE_USD_PER_INPUT_TOKEN + output_tokens * CLAUDE_USD_PER_OUTPUT_TOKEN
    else:
        cost = input_tokens * USD_PER_INPUT_TOKEN
    latencies = sorted(r["latency_ms"] for r in ok if r.get("latency_ms") is not None)

    summary: dict[str, Any] = {
        "classifier": clf["name"],
        "type": clf["type"],
        "backend": backend,
        "total": len(results),
        "answered": len(ok),
        "errors": errors,
        "cached": sum(1 for r in ok if r.get("cached")),
        "input_tokens_billed": input_tokens,
        "output_tokens_billed": output_tokens,
        "est_cost_usd": round(cost, 6),
    }
    if latencies:
        summary["latency_ms_p50"] = latencies[len(latencies) // 2]
        summary["latency_ms_p95"] = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]

    counts: dict[str, int] = {}
    for r in ok:
        key = str(r["prediction"])
        counts[key] = counts.get(key, 0) + 1
    summary["prediction_counts"] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    grouped = "include" in clf
    if grouped or "map" in clf or clf["type"] in ("two_level", "criteria", "ensemble"):
        categories: dict[str, int] = {}
        for r in ok:
            categories[r["category"]] = categories.get(r["category"], 0) + 1
        summary["category_counts"] = dict(sorted(categories.items(), key=lambda kv: -kv[1]))

    labeled = [r for r in ok if "correct" in r]
    if labeled:
        summary["labeled"] = len(labeled)
        summary["accuracy"] = round(sum(r["correct"] for r in labeled) / len(labeled), 4)
        summary.update(class_metrics(labeled))
        if clf["type"] == "noul" or grouped:
            summary["brier"] = round(sum(r["sq_error"] for r in labeled) / len(labeled), 4)
        if clf["type"] == "score":
            summary["mae"] = round(sum(r["abs_error"] for r in labeled) / len(labeled), 4)
        buckets = []
        for lo, hi in CONFIDENCE_BUCKETS:
            inside = [r for r in labeled if r.get("confidence") is not None and lo <= r["confidence"] < hi]
            if inside:
                buckets.append({
                    "confidence": f"[{lo:.1f}, {min(hi, 1.0):.1f}{']' if hi > 1 else ')'}",
                    "n": len(inside),
                    "accuracy": round(sum(r["correct"] for r in inside) / len(inside), 4),
                })
        summary["accuracy_by_confidence"] = buckets
    return summary


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _parse_json_or_text(text: str) -> Any:
    stripped = text.strip()
    if stripped[:1] in ("{", "["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    return text


def _read_arg_or_file(value: str | None, file: str | None) -> Any:
    if file:
        return _parse_json_or_text(Path(file).read_text())
    if value is None:
        return None
    return _parse_json_or_text(value.replace("\\n", "\n"))


def cmd_build(args: argparse.Namespace) -> int:
    clf: dict[str, Any] = {
        "version": FORMAT_VERSION,
        "name": args.name,
        "model": args.model,
        "type": args.type,
        "instructions": _read_arg_or_file(args.instructions, args.instructions_file),
        "state_template": _read_arg_or_file(args.state_template, args.state_template_file) or "{{input}}",
    }
    if args.description:
        clf["description"] = args.description

    if args.type == "choice":
        options: dict[str, Any] = {}
        if args.options_file:
            loaded = json.loads(Path(args.options_file).read_text())
            options.update(loaded if isinstance(loaded, dict) else {str(o): None for o in loaded})
        for opt in args.option or []:
            key, sep, desc = opt.partition("=")
            options[key.strip()] = desc.strip() if sep and desc.strip() else None
        if args.none_option:
            options[NONE_OPTION_KEY] = args.none_option
        clf["criteria"] = options
    elif args.type == "score":
        levels = list(args.level or [])
        if args.levels_file:
            levels.extend(json.loads(Path(args.levels_file).read_text()))
        clf["criteria"] = levels
    elif args.yes or args.no:
        clf["criteria"] = {k: v for k, v in (("true", args.yes), ("false", args.no)) if v}

    clf = validate_classifier(clf)
    text = json.dumps(clf, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    clf = load_classifier(args.classifier)
    print(json.dumps(clf, indent=2, ensure_ascii=False))
    return 0


def log_cost(args: argparse.Namespace, summary: dict) -> None:
    """Append this run's System 1 spend to $CLASSIFIER_COST_LOG, if set."""
    path = os.environ.get("CLASSIFIER_COST_LOG")
    if not path:
        return
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "phase": os.environ.get("CLASSIFIER_COST_PHASE"),
        "classifier": args.classifier,
        "inputs": args.inputs,
        **{k: summary.get(k) for k in ("backend", "luna", "total", "answered", "cached",
                                      "input_tokens_billed", "output_tokens_billed", "est_cost_usd")},
    }
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        print(f"warning: could not log cost: {e}", file=sys.stderr)


def cmd_run(args: argparse.Namespace) -> int:
    clf = load_classifier(args.classifier)
    examples = load_examples(args.inputs, args.text or [], args.input_field, args.label_field, args.id_field)
    if args.limit:
        examples = examples[: args.limit]
    if not examples:
        raise ClassifierError("no inputs: pass an inputs file and/or --text")

    if args.dry_run:
        for ex in examples:
            try:
                payload = build_payload(clf, ex.input)
            except KeyError as e:
                payload = {"error": str(e.args[0])}
            print(json.dumps({"id": ex.id, "label": ex.label, "payload": payload}, ensure_ascii=False))
        return 0

    if args.backend == "luna":
        cache_dir = None if args.no_cache else Path(args.cache_dir or DEFAULT_LUNA_CACHE_DIR)
        client = LunaClient(args.luna_model, args.luna_reasoning, cache_dir, args.timeout)
        api_key_missing = client.client is None
    elif args.backend == "claude":
        cache_dir = None if args.no_cache else Path(args.cache_dir or DEFAULT_CLAUDE_CACHE_DIR)
        client = ClaudeClient(args.claude_model, cache_dir, args.timeout)
        api_key_missing = client.client is None
    elif args.backend == "pplx":
        cache_dir = None if args.no_cache else Path(args.cache_dir or DEFAULT_PPLX_CACHE_DIR)
        client = JevClient(os.environ.get("PERPLEXITY_API_KEY"), cache_dir, args.timeout,
                           url=PPLX_API_URL, key_name="PERPLEXITY_API_KEY", model=PPLX_MODEL)
        api_key_missing = not client.api_key
    else:
        cache_dir = None if args.no_cache else Path(args.cache_dir or DEFAULT_CACHE_DIR)
        client = JevClient(os.environ.get("TYPESAFE_API_KEY"), cache_dir, args.timeout)
        api_key_missing = not client.api_key
    key_name = {"luna": "OPENAI_API_KEY", "pplx": "PERPLEXITY_API_KEY", "claude": "ANTHROPIC_API_KEY"}.get(args.backend, "TYPESAFE_API_KEY")
    if api_key_missing:
        for ex in examples:
            try:
                payload = build_payload(clf, ex.input)
                needs_api = not all(client.is_cached(p) for p in payload.get("members", [payload]))
            except KeyError:
                continue
            if needs_api:
                raise ClassifierError(f"{key_name} not set and some requests are not cached")
    # Results go to a private temp file renamed into place at the end, so two
    # runs writing the same -o path each leave a whole file, never interleaved lines.
    tmp = Path(f"{args.output}.tmp-{os.getpid()}") if args.output else None
    out = tmp.open("w") if tmp else sys.stdout

    results: list[dict] = []
    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(classify, client, clf, ex, args.threshold) for ex in examples]
            for i, fut in enumerate(as_completed(futures), 1):
                record = fut.result()
                results.append(record)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                if args.output and not args.quiet:
                    print(f"\r{i}/{len(examples)}", end="", file=sys.stderr, flush=True)
        if args.output and not args.quiet:
            print(file=sys.stderr)
        if tmp:
            out.close()
            os.replace(tmp, args.output)
    finally:
        if tmp:
            out.close()
            tmp.unlink(missing_ok=True)

    summary = summarize(clf, results, args.backend)
    if args.backend == "luna":
        summary["luna"] = {"model": args.luna_model, "reasoning": args.luna_reasoning}
    elif args.backend == "claude":
        summary["claude"] = {"model": args.claude_model, "thinking": "disabled"}
    log_cost(args, summary)
    if args.summary_output:
        Path(args.summary_output).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 1 if summary["errors"] and not summary["answered"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and run TypeSafe Jev classifiers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="write a classifier JSON file")
    b.add_argument("--name", required=True)
    b.add_argument("--type", required=True, choices=["choice", "noul", "score"])
    b.add_argument("--instructions", help="the judgment; a JSON object/array string is parsed")
    b.add_argument("--instructions-file")
    b.add_argument("--state-template", help="default '{{input}}'; a JSON object/array string is parsed")
    b.add_argument("--state-template-file")
    b.add_argument("--option", action="append", metavar="KEY[=DESCRIPTION]", help="choice option (repeat)")
    b.add_argument("--options-file", help="JSON object of option -> description, or array of keys")
    b.add_argument("--none-option", metavar="DESCRIPTION", help=f"add a '{NONE_OPTION_KEY}' escape option")
    b.add_argument("--level", action="append", metavar="DESCRIPTION", help="score level, lowest first (repeat)")
    b.add_argument("--levels-file", help="JSON array of score levels, lowest first")
    b.add_argument("--yes", help="noul: what a yes means")
    b.add_argument("--no", help="noul: what a no means")
    b.add_argument("--description", help="human note stored in the file, not sent to Jev")
    b.add_argument("--model", default=DEFAULT_MODEL)
    b.add_argument("-o", "--output", help="output path (default stdout)")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate", help="check a classifier JSON file and print it normalized")
    v.add_argument("classifier")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="run a classifier over inputs")
    r.add_argument("classifier")
    r.add_argument("inputs", nargs="?", help=".jsonl, .json array, .csv, .txt (one per line), or '-' for JSONL stdin")
    r.add_argument("--text", action="append", help="an inline input (repeat)")
    r.add_argument("--input-field", help="record field to use as the input (default: whole record)")
    r.add_argument("--label-field", default="label", help="record field with the gold answer (default 'label')")
    r.add_argument("--id-field", default="id", help="record field with the example id (default 'id')")
    r.add_argument("--threshold", type=float, default=0.5, help="noul: P(yes) at or above this counts as yes")
    r.add_argument("--limit", type=int, help="only run the first N inputs")
    r.add_argument("--concurrency", type=int, default=8)
    r.add_argument("--timeout", type=float, default=60.0)
    r.add_argument("--backend", choices=["jev", "luna", "pplx", "claude"], default=os.environ.get("CLASSIFIER_BACKEND", "jev"),
                   help="System One that answers the questions (default jev, or $CLASSIFIER_BACKEND)")
    r.add_argument("--luna-model", default=DEFAULT_LUNA_MODEL, help="OpenAI model for --backend luna")
    r.add_argument("--claude-model", default=DEFAULT_CLAUDE_MODEL, help="Anthropic model for --backend claude")
    r.add_argument("--luna-reasoning", choices=list(LunaClient.REASONING_MAX_OUTPUT), default="low",
                   help="reasoning effort for --backend luna (default low)")
    r.add_argument("--cache-dir", help=f"default {DEFAULT_CACHE_DIR} (jev) or {DEFAULT_LUNA_CACHE_DIR} (luna)")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--dry-run", action="store_true", help="print the request payloads without calling Jev")
    r.add_argument("-o", "--output", help="results JSONL path (default stdout)")
    r.add_argument("--summary-output", help="also write the summary JSON here")
    r.add_argument("-q", "--quiet", action="store_true")
    r.set_defaults(func=cmd_run)

    args = parser.parse_args()
    load_env()
    try:
        return args.func(args)
    except ClassifierError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
