# Strategy: category audit with a held-out check set

Follow this in place of step 3 of the skill's workflow. Labels go where the
classifier's structure can be wrong (its categories), a small random check set
guards every revision, and no single label becomes a rule on its own.

## Setup

1. **Check set.** Before revising the first draft, run it on the pool and buy
   **10 random labels** (`tools/sample.py OUT.jsonl --mode random -n 10`),
   bought with `label --tag check`. Score versions on them with
   `tools/score.py OUT.jsonl --labels RUN_DIR/labels.jsonl --tag check`, and on
   the rest with `--exclude-tag check`. These labels are only for judging
   versions:
   - never add a check-set text to the classifier as an example;
   - never write a rule from check-set labels.
   Record the draft's score on them (right out of 10).

## Loop until the budget is spent

2. **Run** the current classifier on the pool with `-o`.
3. **Audit categories.** Buy about **8 labels** from
   `tools/sample.py OUT.jsonl --mode category -n 8 --labels RUN_DIR/labels.jsonl`.
   The picks are spread over the classifier's top options (or paths/clauses),
   weighted by size, so a large option mapped to the wrong class shows up
   quickly even when the classifier is confident. Once the categories look
   clean (every audited category right twice), switch these picks to
   `tools/uncertain.py` margins.
4. **Two agreeing labels before a rule.** A rule, an option change or an
   example enters the classifier only when two agreeing non-check labels
   support it, or one label plus an owner's answer. A single label that no
   current rule explains goes on the **pending** list in
   `RUN_DIR/hypotheses.md` with its id; revisit it when a later label agrees
   (then write the rule) or contradicts it (then mark it suspected noise).
   Describe patterns in words; add at most one short example per rule rather
   than pasting every bought text.
   When one pending item would move many records, you may buy one paraphrase
   from the pool, or ask one 5-point policy question, to settle it.
5. **Guard the revision.** Score the revision on the check set and on all
   other bought labels. Keep it only if it gets no more check labels wrong
   than the best version so far and fits more of the other labels. Otherwise
   narrow or revert the change.
6. **Snapshot** kept revisions with an estimate based on the check set, then
   go back to 2.

## Finish

Your final snapshot must be your best version by the check set (break ties
with the other labels). If an earlier version was better, snapshot it again
as the last one.

In the journal, record per round: audit picks and how many the classifier had
right per category, pending items added or resolved, check-set score of the
revision, and whether it was kept.
