# Strategy: read, ask, cover, then verify

Follow this in place of step 3 of the skill's workflow. Learn what the pool
contains before spending anything, ask the user about what the text cannot
tell you, ground every option in a label, and only then refine near the
boundary, verifying each rule before keeping it.

## Phase 1: read the pool (free)

1. Read at least 200 pool records. List the phenomena you see: the kinds of
   message, the forms they take, the cases where two classes meet, and
   anything whose class depends on a policy or mapping the description does
   not state. Estimate how many pool records each phenomenon covers. Write
   the list in `RUN_DIR/phenomena.md`.
2. Build a first classifier from the description and the list: fine options
   for the phenomena, mapped to classes. Run it on the pool and snapshot.

## Phase 2: ask about what the text cannot tell you (at most 30 points)

3. Ask about the phenomena whose class you cannot infer and that cover the
   most records, and about any private policy or mapping (which team handles
   which kind of request, what counts under the policy). Group them into one
   or two messages, one part per decision, stating your current reading as a
   rule and asking whether it holds and what the exceptions are. Don't ask
   about single phrasings: labels answer those more reliably. Revise and
   snapshot.

## Phase 3: check set (16 points)

4. Buy **8 random labels** with `label --tag check`
   (`tools/sample.py OUT.jsonl --mode random -n 8`). Score with
   `tools/score.py OUT.jsonl --labels RUN_DIR/labels.jsonl --tag check`.
   These labels choose the final snapshot at the end. Never write a rule
   from them and never use them to judge a revision.

## Phase 4: coverage labels (about 20 points)

5. Buy about **10** labels spread over the classifier's options
   (`tools/sample.py OUT.jsonl --mode category -n 10 --labels RUN_DIR/labels.jsonl`),
   so that every large option is grounded in at least one label. An option
   whose label disagrees with its mapped class is a sign of a wrong rule or a
   wrong mapping, not just of one hard record: find out which before
   revising.

## Phase 5: boundary refinement (the rest of the budget)

6. Loop until the budget is spent:
   - run the pool; buy about **6** records from
     `tools/uncertain.py OUT.jsonl --labels RUN_DIR/labels.jsonl -n 6`;
   - turn each error into a hypothesis under the rules-only constraint;
   - **verify rules that reach far**: when a revision moves 10 or more pool
     records (`tools/diff_preds.py`), buy the label of the moved record least
     like the labels that motivated the rule, or ask a 5-point question that
     states the rule, before keeping it;
   - keep a revision only if, on the non-check labels, it breaks none or
     fixes at least two for each one it breaks (`tools/boundary.py compare
     OLD.jsonl NEW.jsonl --labels RUN_DIR/labels.jsonl`, excluding the check
     ids with `--ids-file`). Otherwise narrow it or revert it;
   - snapshot kept revisions.

## Finish

Score all snapshots on the check set. The last snapshot should be the latest
version, unless an earlier one gets **2 or more** more check labels right;
then snapshot that one again as the last. Base your estimate on the check
set.

In the journal, record the phenomena list, each question with its answer and
the rule it produced, the coverage labels and what they changed, each
verification (rule, record bought, outcome), kept and reverted revisions, and
each snapshot's check-set score.
