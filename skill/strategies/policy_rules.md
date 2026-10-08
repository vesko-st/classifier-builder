# Strategy: policy draft, then tested rules

Follow this in place of step 3 of the skill's workflow. Learn the main policy
lines from the owner, build a classifier that mirrors them, then refine it
with uncertain labels under strict rules for what a label may change.

## Phase 1: policy questions (at most 20 points)

1. Read at least 100 pool records. List the decisions the classifier must
   make (what is in scope, which targets or topics count, which forms count,
   where two classes meet) and roughly how many pool records each affects.
2. Ask about the decisions that affect the most records, one 5-point part
   each, at most 20 points in total. State your reading as a rule and ask
   whether it holds and what the exceptions are. Don't ask about single
   phrasings: labels answer those more reliably.

## Phase 2: build to mirror the policy

3. For binary or few-class tasks, use `criteria`: one yes/no question per test
   the owner described, combined by a `rule`. For many classes, use a
   `choice` (with a `map` if finer options help) and put the answers into the
   instructions and option descriptions. Snapshot.

## Phase 3: check set (20 points)

4. Run the pool and buy **10 random labels** with `label --tag check`
   (`tools/sample.py OUT.jsonl --mode random -n 10`). Score with
   `tools/score.py OUT.jsonl --labels RUN_DIR/labels.jsonl --tag check`.
   These labels choose the final snapshot at the end. Don't use them to judge
   each revision, never paste their texts into the classifier, and never
   write a rule from them.

## Phase 4: tested rules (the rest of the budget)

5. Loop until the budget is spent:
   - run the pool; buy about **6** records from
     `tools/uncertain.py OUT.jsonl --labels RUN_DIR/labels.jsonl -n 6`;
   - for each error, write the most general rule consistent with every
     non-check label, about meaning rather than wording, in
     `RUN_DIR/hypotheses.md`;
   - **two labels before a rule**: a rule enters the classifier only when two
     agreeing labels support it. An owner's answer does not count as the
     second label: on edge cases owners reason from the policy and can
     disagree with their own labels. A single unexplained label stays pending
     until another label agrees (write the rule) or contradicts it (mark it
     suspected noise);
   - when a rule would move 3 or more pool records, buy the label of the moved
     record least like its supporting examples before keeping it;
   - apply the revision, rerun, and compare with `tools/diff_preds.py`: keep it
     only if it breaks no bought non-check label, or fixes at least two for
     each it breaks. Otherwise narrow or revert it;
   - snapshot kept revisions.

## Finish

Score all snapshots on the check set. The last snapshot should be the latest
version, unless an earlier one gets **2 or more** more check labels right; then
snapshot that one again as the last. Base your estimate on the check set.

In the journal, record each question with its answer and the rule it
produced, per round the labels bought and how many the classifier had right,
hypotheses with their status, kept or reverted revisions, and each snapshot's
check-set score.
