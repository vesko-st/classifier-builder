# Strategy: triage, then specialise

Follow this in place of step 3 of the skill's workflow. Spend a little first
to learn what kind of task this is, then commit to the approach that suits
it: learning the policy from the owner, or learning from labels.

## Step 1: diagnose (about 20 points)

1. Draft from the description, run it on the pool, snapshot it.
2. Buy **10 random labels** as a check set:
   `tools/sample.py OUT.jsonl --mode random -n 10`, bought with
   `label --tag check`. Score with
   `tools/score.py OUT.jsonl --labels RUN_DIR/labels.jsonl --tag check`.
   Check labels judge versions; never paste a check text into the classifier
   or write a rule from one alone.
3. Decide the branch and write the evidence in the journal:
   - **Policy branch** when the label is a judgement under a policy you
     can't see: few classes, and the description leaves open what counts
     (which targets, which forms, where the line is), or the check-set errors
     mostly go one way (e.g. several false positives and no false negatives).
   - **Label branch** when the classes are many and mostly self-explanatory
     topics or intents, and the check-set errors are scattered across class
     pairs rather than one systematic mistake.
   If unsure, prefer the label branch for more than 5 classes and the policy
   branch otherwise.

## Step 2a: policy branch

4. Ask the owner about the decisions that affect the most pool records, one
   5-point part each, up to about 25 points: state your reading as a rule and
   ask whether it holds and what the exceptions are.
5. Rebuild to mirror the answers: for binary or few-class tasks a `criteria`
   classifier (one yes/no question per test, combined by a `rule`); otherwise
   put the answers into instructions and option descriptions. Snapshot.
6. Spend the rest as in step 2b, but test any owner answer about an edge case
   with one label before it moves many records.

## Step 2b: label branch (and the rest of the policy branch)

7. Loop until the budget is spent:
   - run the pool; buy about **8** records from
     `tools/uncertain.py OUT.jsonl --labels RUN_DIR/labels.jsonl -n 8`
     (it already skips repeats of the same confusion);
   - for each error, write the most general rule consistent with every
     non-check label so far, about meaning rather than wording;
   - apply the revision, rerun, and compare with `tools/diff_preds.py`: keep
     it only if it breaks no bought label, or fixes at least two for each it
     breaks; otherwise narrow or revert it;
   - snapshot kept revisions.

## Finish

Score your snapshots on the check set. The last snapshot should be the latest
version, unless an earlier one gets **2 or more** more check labels right; then
snapshot that one again as the last. (Ten labels are noisy: a one-label gap
means nothing.) Base your final estimate on the check set, not on the labels
you picked because they were hard.

In the journal, record the branch decision and its evidence, each question
and answer, per round the labels bought and how many the classifier had
right, which revisions were kept or reverted, and the check-set score of each
snapshot.
