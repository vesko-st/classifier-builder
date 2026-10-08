# Classifier builder

Code and paper for *Building System 1: How Language Agents Construct and Use Classifiers Under an Information Budget*. A coding agent (System 2) builds natural-language classifiers that a small judgement model, [Jev](https://docs.typesafe.ai), runs (System 1). The agent starts from a task description and unlabelled data and spends a budget of a simulated user's time on labels and questions, or receives every training label.

## Layout

| Path | Contents |
| --- | --- |
| `skill/` | The classifier-builder skill the agent reads, with the building strategies (`strategies/`) and the rules-only constraint (`constraints/`). |
| `tools/` | Builder tools (run, label, ask, score, uncertain, sample, diff, threshold, snapshot), the simulated user (`ask_oracle.py`), the headless runner (`run_builder.py`), task preparation, baselines and scoring. |
| `tasks/` | Task descriptions given to the builder, and the private guideline and note on how the labels apply it (`applied_policy.md`, written by `tools/infer_policy.py`) held by the simulated user. |
| `baselines/` | Zero-shot classifiers and baseline score summaries. |
| `results/` | Every run's final classifier (`classifier.json`), its settings, points spent and the test score of each snapshot on each System 1 model (`run.json`), and an index of all runs (`runs.csv`), whose `simulated_user_version` column marks the runs that asked questions of an earlier simulated user; the paper reports only version 4 and runs that asked nothing. Written by `tools/export_results.py`. |
| `paper/` | The paper (`acl/paper.tex`, `acl/references.bib`) and the Markdown draft it was converted from (`paper.md`, `md_to_acl.py`). |

## Setup

Python 3.11+ with `httpx`, `anthropic`, `claude-agent-sdk`, `datasets`, `pandas`, `openpyxl` and, for the RoBERTa baseline, `transformers` and `torch`. The tools expect the interpreter at `../.venv/bin/python` relative to the project root.

API keys are read from the environment, or from `../.env` as `KEY=VALUE` lines: `TYPESAFE_API_KEY` (Jev), `ANTHROPIC_API_KEY` (builders and the simulated user), and optionally `OPENAI_API_KEY` (GPT-6 Luna) and `PERPLEXITY_API_KEY` (Perplexity's decision model).

## Running

```bash
PY=../.venv/bin/python
$PY tools/prepare_tasks.py                      # build data/ splits from the public datasets
$PY tools/zero_shot.py banking77_routing        # zero-shot baseline
$PY tools/infer_policy.py banking77_routing     # the simulated user's note on its labels (once per task)
$PY tools/new_run.py banking77_routing --budget 100 --strategy policy_first --run-id demo
$PY tools/run_builder.py runs/demo --model claude-opus-5-5 --effort high --score
```

Scores of every snapshot are written to `runs/_harness/<run-id>/`. The conversation tasks download their corpora from the primary sources into `data/raw/` (`tools/conversation_corpora.py`). At the time of writing, the CodaLab server that hosts CraigslistBargain serves an expired TLS certificate; if the download fails, place the corpus's `train.json` and `validation.json` (`parsed.json` from each bundle) in `data/raw/craigslist/`.

## Building the paper

```bash
cd paper/acl && latexmk -pdf paper.tex
```

## Licence

Code is released under the [Apache License 2.0](LICENSE). The datasets keep their own licences; this repository does not redistribute them, apart from short excerpts that builders quoted in their classifiers, and `tools/prepare_tasks.py` downloads them from their sources.
