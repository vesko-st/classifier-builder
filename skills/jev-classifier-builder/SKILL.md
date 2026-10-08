---
name: jev-classifier-builder
description: >
  Build, test and revise a natural-language classifier that TypeSafe Jev runs,
  from a task description and unlabelled examples, asking the user for labels
  and rules only where they pay off. Use when the user wants to classify,
  route, tag, filter or triage many texts (messages, tickets, emails,
  dialogues) the same way, or wants a fast, cheap classifier instead of
  calling a large model on every item.
---

# Build a Jev classifier

A Jev classifier is a JSON file: one or more questions, with options and their
descriptions, that the Jev model answers about each input. You write it, run
it over the user's data, and revise it until it does what the user means. It
is plain text, so the user can read it and change a rule by editing a
sentence.

The user's time is the scarce resource. Running the classifier is cheap
(under $0.50 per 1,000 inputs) and cached, so read and run as much as
you like, and ask the user only for what you cannot work out yourself.

## Setup

- `TYPESAFE_API_KEY` in the environment, or in a `.env` file in the working
  directory. Keys: <https://typesafe.ai>.
- Python 3.10+ with `httpx` (`pip install httpx`).
- `S` below is this skill's `scripts/` directory.

Make a working directory (`WORK`) for the task:

```
WORK/pool.jsonl      the inputs to learn from: {"id", "text"}, a few hundred to a few thousand
WORK/labels.jsonl    labels you have: {"id", "text", "label"}, optional "tag": "check"
WORK/classifiers/    v01.json, v02.json, ...: every version you would ship
WORK/journal.md      what you did, why, what you learned, per step
```

Convert the user's data to `pool.jsonl` (the runner also reads CSV and
one-input-per-line text). If the user already has labelled examples, put them
in `labels.jsonl`, and hold out a random fifth with `"tag": "check"` to
estimate accuracy honestly.

## Tools

| Command | What it does |
|---|---|
| `python $S/jev_classifier.py run CLF.json WORK/pool.jsonl --input-field text -o OUT.jsonl` | run a classifier; each result has the prediction, class probabilities and a `margin` (how far it is from flipping) |
| `python $S/jev_classifier.py run CLF.json WORK/labels.jsonl --input-field text` | run on labelled records: accuracy, per-class scores, confusions |
| `python $S/score.py OUT.jsonl --labels WORK/labels.jsonl [--tag check \| --exclude-tag check]` | score pool results on your labels, with a 90% interval |
| `python $S/uncertain.py OUT.jsonl --labels WORK/labels.jsonl -n 10` | unlabelled records closest to flipping, near-duplicates skipped |
| `python $S/sample.py OUT.jsonl --mode random\|category -n 10 --labels WORK/labels.jsonl` | random records, or records spread over the predicted options |
| `python $S/diff_preds.py OLD.jsonl NEW.jsonl --labels WORK/labels.jsonl` | what a revision changed, and which labels it fixed and broke |
| `python $S/fit_threshold.py OUT.jsonl --labels WORK/labels.jsonl --class C` | best decision threshold for class C |
| `python $S/copy_check.py CLF.json --pool WORK/pool.jsonl` | flags text copied from the pool into the classifier |

`python $S/jev_classifier.py --help` documents the classifier format. Results
with an `"error"` field are failed calls: rerun (answered inputs are cached).
For writing good Jev questions, see <https://docs.typesafe.ai/llms.txt>.

## Classifier shapes

- **Flat choice:** one `choice` question whose options are the classes.
- **Option map:** more options than classes, mapped many to one with
  `"map": {"option": "class"}`. Concrete, fine-grained options usually beat a
  few abstract ones; for routing, one option per kind of request mapped to its
  team makes the mapping itself readable.
- **Two-level:** pick a group, then a class within it, in one request.
- **Criteria:** several yes/no questions combined by a rule, for a policy
  that is a conjunction of tests.
- **Ensemble:** the average of 2–3 rewordings of the same classifier. Use it
  once revisions start breaking about as many labels as they fix: each
  wording misses different near-ties, so the average is steadier.

Any shape with class probabilities can store a decision threshold. Jev judges
meaning well and surface patterns poorly; write options and rules about what
a message means or asks for, not the words it uses.

## Workflow

1. **Read** the user's description and at least 100 inputs. Write down what
   each class means and where you expect trouble.
2. **Draft** a classifier from the description and what you read, run it on
   the pool, and save it as `v01.json`. Look at the spread of predictions and
   at the records with the smallest margins.
3. **Decide where the missing knowledge lives**, and pick a strategy from
   [references/strategies.md](references/strategies.md) for it:
   - *In the text* (the class names say what they mean; the hard part is
     near-synonyms): label uncertain records in small batches and turn each
     error into a general rule.
   - *In a private policy or mapping* (which team handles what, house rules):
     ask the user directly, one group at a time, stating your guess. Do not
     rely on labelling uncertain records: a whole group sent to the wrong
     class with confidence never looks uncertain.
   - *In an annotation policy that the labels show* (what counts as abuse,
     spam, a complaint): either ask about the policy or derive rules from
     labels; both work.
   - *Nowhere*: the label is an outcome nobody defines (will they buy, did it
     resolve), or the first draft is already good. Build little, change only
     what labels prove wrong, and stop early.
4. **Revise** from what you learn. Every rule goes into the classifier as a
   statement about meaning, never as a pasted example
   ([references/rules_only.md](references/rules_only.md)). Rerun, compare with
   `diff_preds.py`, and keep a revision only if it fixes clearly more labels
   than it breaks: fixes − breaks > 2·√(fixes + breaks) is a good bar.
   Save each kept version.
5. **Stop** when revisions only trade errors near the boundary, or the user's
   labels agree with the classifier. Most of the gain comes from the first
   draft and the first round of answers; more labels on a task that is
   already right mostly add the risk of moving it.

## Asking the user

- **Batch questions and make them concrete.** One message, each question a
  rule you propose with a yes/no answer and one or two short examples:
  "I'm treating requests to change a PIN as Cards, not Security. Right?"
  Ask open-ended questions ("what are the main confusions?") only when you
  are lost.
- **Labels:** show 5–15 numbered inputs at a time and ask for the class of
  each; write the answers to `labels.jsonl`. Pick them with `uncertain.py`
  near the boundary, with `sample.py --mode category` for options with no
  label yet, or with `sample.py --mode random` for an honest estimate (save
  those with `"tag": "check"` and score on them with `score.py --tag check`). Records chosen because they are hard give a pessimistic
  estimate; say so.
- **Trust rules, check edge cases.** Users are reliable about their general
  rules, but on borderline cases they reason from how the rule is written and
  can disagree with how they actually label. Before an answer about an edge
  case changes many predictions, confirm it with a label on one of the
  records it would move. Answers about borderline cases can also move a
  boundary that was already right: re-score on your labels after acting on
  one.

## Deliver

Give the user: the final classifier file, the command to run it, your
accuracy estimate and what it rests on (check labels or hand-picked ones),
the rules that mattered most, in plain words, and the records it still finds
hard. Tell them how to change it: edit the option description or rule, rerun
on their labels, and compare with `diff_preds.py`.

Keep the classifier working after delivery: rerun it on new data, check a
small random sample now and then, and when the user changes a rule, edit the
sentence that states it rather than adding examples.
