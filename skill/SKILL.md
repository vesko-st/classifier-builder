---
name: jev-classifier-builder
description: >
  Build an accurate TypeSafe Jev classifier for a new task from a task
  description, class list and unlabelled examples, buying labels and asking the
  task owner questions only when they are worth their cost. Use when given a
  classifier-builder run directory.
---

# Build a Jev classifier with minimal supervision

You are given a run directory (`RUN_DIR`) holding a task description, the output
classes, about 1,000 unlabelled examples, and a point budget for asking the task
owner. Your job: produce the most accurate classifier you can within the
budget.

## Objective

Your final classifier is scored on a hidden test set by the task's `metric` in
`task.json` (accuracy, or macro-F1: the average of per-class F1, which rewards
getting the minority class right as much as the majority). The test set comes
from the same source as the pool but may not match its distribution exactly. Reach the highest accuracy you can within
the budget. Points spent are recorded at every snapshot to chart accuracy
against information, so spend them where they help most: early points that
buy big gains make the curve better. Stop when nothing you could buy would
still improve accuracy, or when the budget is spent.

## What you have

```
RUN_DIR/task.json       description, input format, classes (what the owner told you)
RUN_DIR/pool.jsonl      unlabelled examples: {"id", "text"}
RUN_DIR/labels.jsonl    labels you have bought: {"id", "text", "label"}
RUN_DIR/classifiers/    your snapshots (written by snapshot.py)
RUN_DIR/journal.md      your working log (you write it)
```

Tools (run from the project root, `~/typesafe/classifier-builder`, with
`PY=../.venv/bin/python`):

**First, claim the run:** `$PY tools/claim_run.py RUN_DIR` prints a token.
Commands that spend points or save snapshots need it (`--token T`, or
`export RUN_TOKEN=T`); write it at the top of your journal so you keep it
(`RUN_DIR/owner.json` holds only the claim; it has no task information). If
the claim is refused, another builder owns the run: stop and report it.

| Command | Cost |
|---|---|
| `$PY tools/jev_classifier.py run CLF.json RUN_DIR/pool.jsonl --input-field text -o OUT.jsonl` | free (Jev is cheap and cached) |
| `$PY tools/jev_classifier.py run CLF.json RUN_DIR/labels.jsonl --input-field text` | free; reports accuracy, per-class scores, confusions |
| `$PY tools/ask_oracle.py RUN_DIR --token T label [--tag TAG] ID [ID ...]` | 2 points per new label; `--tag check` marks a random check set |
| `$PY tools/ask_oracle.py RUN_DIR --token T ask "QUESTION"` | 2, 5 or 10 points, priced by the owner after answering |
| `$PY tools/ask_oracle.py RUN_DIR status` | free |
| `$PY tools/snapshot.py RUN_DIR CLF.json --token T --estimate 0.85 --note "..."` | free; saves a numbered version (estimate in the task's metric) |
| `$PY tools/score.py OUT.jsonl --labels RUN_DIR/labels.jsonl [--tag check \| --exclude-tag check]` | free; scores pool results on bought labels (or a tagged subset), with a 90% interval and per-member scores for ensembles |
| `$PY tools/uncertain.py OUT.jsonl --labels RUN_DIR/labels.jsonl -n 20 [--by disagreement]` | free; least certain unlabelled records (or where ensemble members disagree), near-duplicates skipped |
| `$PY tools/sample.py OUT.jsonl --mode random\|category -n 10 --labels RUN_DIR/labels.jsonl` | free; random picks, or picks spread over the classifier's categories |
| `$PY tools/fit_threshold.py OUT.jsonl --labels LABELS.jsonl --class C` | free; best decision threshold for class C on labelled records |
| `$PY tools/diff_preds.py OLD.jsonl NEW.jsonl --labels RUN_DIR/labels.jsonl` | free; what changed between versions, which bought labels each gets wrong |

Question prices are per part: every case, phrasing or class you want a
separate verdict on is its own part (examples that only illustrate one rule
question are not), and a message costs the sum of its parts. A part costs
**2** for one record or message type or a yes/no fact; **5** for a policy
question about a group of messages or a rule; **10** for an open-ended question
needing a view across many examples (answered in about 100 words). A message
also costs at least 2 per record whose label it reveals. Questions are limited
to 1,500 characters; over-budget requests are refused.

`run` without `-o` prints every result line before the summary; pass
`-o FILE.jsonl` to keep output short. Results with an `"error"` field are
failed Jev calls: rerun (answered records are cached) rather than analysing
them.

`tools/jev_classifier.py --help` documents the classifier file format. The
`typesafe-ai` skill (`~/.agents/skills/typesafe-ai/SKILL.md`) and the docs at
<https://docs.typesafe.ai/llms.txt> cover how to write good Jev questions.

## Rules

- Learn about the labels only through `ask_oracle.py`. Do not read anything
  under `data/`, `tasks/`, `baselines/`, or other runs; they hold hidden labels.
- Snapshot every classifier you would be willing to ship, including the first
  one, with your honest accuracy estimate. The last snapshot is your answer;
  if an earlier version was better, snapshot it again at the end.
- Keep `RUN_DIR/journal.md` current: a short entry per step saying what you did,
  why, what you learned, and points spent. Start each entry with `## ` and a
  one-line title.

## Jev facts that shape the design

- `choice` returns a probability per option (up to 255 options); `noul` returns
  P(yes). Answers are deterministic.
- Jev judges meaning well and surface patterns poorly. It struggles with long
  flat lists of vague options, and with rules it has no way to infer.
- A classifier can have more options than output classes: `"map": {"option":
  "class"}` sums option probabilities into classes. Fine-grained, concrete
  options mapped to coarse classes often beat a few abstract classes.
- Instructions and option descriptions can be structured JSON (definitions,
  inclusions, exclusions, examples).
- Other shapes: `two_level` (route to a group, then choose within it),
  `criteria` (several yes/no questions combined by a rule, for policies that
  are a conjunction of tests), and `ensemble` (average of several
  classifiers). Classifiers with class probabilities can store a decision
  threshold (`"decision"`). See `tools/jev_classifier.py --help`.
- Small wording changes can flip records near 50/50. Judge a revision by the
  labels it fixes and breaks, not by how many pool predictions moved.
- **Wording-variant ensembles damp that jitter.** When revisions start breaking
  about as many labels as they fix, switch to an `ensemble` of 2–3 variants of
  the same classifier: the same options, rules and examples, with the
  instructions and descriptions phrased differently. Apply every later rule to
  all variants. Each variant misses different near-ties, so the average is
  steadier and a revision has to move it, not one phrasing. `score.py` scores
  each member too. It costs one Jev request per member.
- Every result has a `margin`: how far it is from flipping, measured from the
  stored decision threshold if there is one. `uncertain.py` ranks by it.
- The distribution of predictions over the pool and the per-record confidence
  are free signals: a class that never appears, or a band of low-confidence
  records, tells you where the classifier is unsure.

## Workflow

1. **Read** `task.json` and a few dozen pool records. Write down what you think
   each class means and where you expect ambiguity.
2. **Draft** a classifier from the description alone; run it on the pool;
   snapshot it. Look at the class distribution and at low-confidence records.
3. **Decide what you don't know.** For each uncertainty, estimate how many pool
   records it affects and pick the cheapest way to resolve it:
   - a policy question (5) when a whole group of records hinges on one rule;
   - a single-record question or label (2) when one example settles it;
   - labels for a small random sample when you need an unbiased accuracy
     estimate;
   - an open question (10) only when you are lost about the task.
   The owner is a person: their answers about general rules are reliable, but
   on edge-case phrasings they reason from the policy and can disagree with
   their own labels. The labels are what you are scored on, so when an answer
   about an edge case would change many predictions, confirm it with a label
   or two first.
   Labels you pick because they are hard are a biased accuracy estimate; say
   so in your estimate, or buy a few random ones if the estimate matters.
4. **Revise** the classifier: instructions, option descriptions, finer options
   with a map, or a different question shape. Rerun on the pool and on your
   bought labels; check that fixes didn't break other records.
5. **Snapshot** each improvement with an accuracy estimate.
6. **Stop** when the budget is spent, or when you can find nothing left to buy
   that would change predictions: revisions no longer move predictions and
   your bought labels agree with the classifier.

## Final answer

Reply with: the final snapshot path, your estimated accuracy, points spent
(labels vs questions), and the three decisions that mattered most.
