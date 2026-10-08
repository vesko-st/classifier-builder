# Classifier builder

An [Agent Skill](https://agentskills.io) that lets a coding agent build fast, cheap text classifiers for you. Describe the task and give it unlabelled examples; the agent drafts a natural-language classifier, runs it with [Jev](https://docs.typesafe.ai), asks you for the few labels and rules it needs, and revises it until it does what you mean. The result is a readable JSON file: to change a rule, you edit a sentence.

Use it when you need to classify, route, tag, filter or triage many texts the same way (support tickets, emails, messages, dialogues) and would rather not call a large model on every item. Running a finished classifier costs under $0.50 per 1,000 inputs.

## Install

Copy the skill into your agent's skills directory:

```bash
cp -r skills/jev-classifier-builder ~/.claude/skills/    # Claude Code
cp -r skills/jev-classifier-builder ~/.cursor/skills/    # Cursor
```

It needs Python 3.10+ with `httpx` (`pip install httpx`) and a `TYPESAFE_API_KEY` from [typesafe.ai](https://typesafe.ai), in the environment or in a `.env` file in the working directory.

## Use

Ask your agent for a classifier and point it at your data, for example:

> Build a classifier that routes our support tickets to billing, technical or account. The tickets are in `tickets.csv`, column `body`.

The agent reads a sample of your data, writes a first classifier from your description, and then asks you questions in the chat: whether a rule it inferred is right, or the class of a handful of examples. If you already have labelled examples, give it those too and it will hold some out to estimate accuracy. When it is done, it hands you the classifier file, the command to run it, its accuracy estimate and the rules that mattered most.

What the skill tells the agent, in brief:

- **Find where the missing knowledge lives.** If the class names say what they mean, the agent labels the examples the classifier is least sure about and turns each error into a rule. If the answer depends on a policy or mapping only you know (which team handles what), it asks you directly, because a whole group sent to the wrong class with confidence never looks uncertain.
- **Rules, not examples.** Labels become general rules about meaning, never pasted examples, so the classifier works on inputs it has not seen.
- **Know when to stop.** When the first draft is already right, or the label is an outcome nobody defines, more building mostly adds risk.

The skill's files: [`SKILL.md`](skills/jev-classifier-builder/SKILL.md) (the workflow), [`references/strategies.md`](skills/jev-classifier-builder/references/strategies.md) (how to spend your time on each kind of task), [`references/rules_only.md`](skills/jev-classifier-builder/references/rules_only.md) and the scripts in `scripts/`, which also run on their own (`python scripts/jev_classifier.py --help`).

## The paper

The skill comes from *Building System 1: How Language Agents Construct and Use Classifiers Under an Information Budget*. In the paper, a coding agent (System 2) builds natural-language classifiers that Jev runs (System 1). Given every training label, an Opus builder matches or beats RoBERTa fine-tuned on them on six tasks. Without labels, spending a budget of a simulated user's time on labels and questions, it beats zero-shot wherever the user has something to teach, and the best strategy depends on where the missing knowledge lies. The skill's strategies are the ones that worked, rewritten for a real user in place of the simulated one and its point budget.

### Layout

| Path | Contents |
| --- | --- |
| `skills/jev-classifier-builder/` | The skill for your own tasks (above). |
| `skill/` | The experiment version of the skill, as the paper's builders read it: run directories, a point budget and the simulated user, with every strategy tried (`strategies/`) and the rules-only constraint (`constraints/`). |
| `tools/` | Builder tools (run, label, ask, score, uncertain, sample, diff, threshold, snapshot), the simulated user (`ask_oracle.py`), the headless runner (`run_builder.py`), task preparation, baselines and scoring. |
| `tasks/` | Task descriptions given to the builder, and the private guideline and note on how the labels apply it (`applied_policy.md`, written by `tools/infer_policy.py`) held by the simulated user. |
| `baselines/` | Zero-shot classifiers and baseline score summaries. |
| `results/` | Every run's final classifier (`classifier.json`), its settings, points spent and the test score of each snapshot on each System 1 model (`run.json`), and an index of all runs (`runs.csv`), whose `simulated_user_version` column marks the runs that asked questions of an earlier simulated user; the paper reports only version 4 and runs that asked nothing. Written by `tools/export_results.py`. |
| `paper/` | The paper (`acl/paper.tex`, `acl/references.bib`) and the Markdown draft it was converted from (`paper.md`, `md_to_acl.py`). |

### Reproducing the experiments

Python 3.11+ with `httpx`, `anthropic`, `claude-agent-sdk`, `datasets`, `pandas`, `openpyxl` and, for the RoBERTa baseline, `transformers` and `torch`. The tools expect the interpreter at `../.venv/bin/python` relative to the project root.

API keys are read from the environment, or from `../.env` as `KEY=VALUE` lines: `TYPESAFE_API_KEY` (Jev), `ANTHROPIC_API_KEY` (builders and the simulated user), and optionally `OPENAI_API_KEY` (GPT-6 Luna) and `PERPLEXITY_API_KEY` (Perplexity's decision model).

```bash
PY=../.venv/bin/python
$PY tools/prepare_tasks.py                      # build data/ splits from the public datasets
$PY tools/zero_shot.py banking77_routing        # zero-shot baseline
$PY tools/infer_policy.py banking77_routing     # the simulated user's note on its labels (once per task)
$PY tools/new_run.py banking77_routing --budget 100 --strategy policy_first --run-id demo
$PY tools/run_builder.py runs/demo --model claude-opus-5-5 --effort high --score
```

Scores of every snapshot are written to `runs/_harness/<run-id>/`. The conversation tasks download their corpora from the primary sources into `data/raw/` (`tools/conversation_corpora.py`). At the time of writing, the CodaLab server that hosts CraigslistBargain serves an expired TLS certificate; if the download fails, place the corpus's `train.json` and `validation.json` (`parsed.json` from each bundle) in `data/raw/craigslist/`.

### Building the paper

```bash
cd paper/acl && latexmk -pdf paper.tex
```

## Licence

Code is released under the [Apache License 2.0](LICENSE). The datasets keep their own licences; this repository does not redistribute them, apart from short excerpts that builders quoted in their classifiers, and `tools/prepare_tasks.py` downloads them from their sources.
