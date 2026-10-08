# Strategy: policy with labels first

Follow this in place of step 3 of the skill's workflow. Learn the labelling
policy from the owner, but check it against real labels before testing its
edges. The owner's answers about made-up edge cases describe the policy as
written; the labels show how it was applied, and the test set is scored on
the labels. When the two disagree, the labels win.

## Phase 1: policy questions (about 20–25 points)

1. Read at least 100 pool records. List the **decisions** the policy must
   make: what is in scope, which targets or topics count, which forms (quoted,
   reported, sarcastic, joking, questions) count, and where two classes meet.
2. Ask the owner about the decisions that affect the most records, one
   5-point part each. State your current reading as a rule and ask whether it
   holds and what the exceptions are.

## Phase 2: draft, then random labels (20 points)

3. Build a draft that mirrors the policy. For binary or few-class tasks, use
   the `criteria` shape (one yes/no question per test, combined with a
   `rule`); for many-class tasks, use a `choice` with a `map` or `two_level`.
   Snapshot it.
4. Run the pool and buy **10 random labels** (`tools/sample.py --mode random`,
   `label --tag check`). Score the draft on them (`tools/score.py --tag
   check`). For each error, write down which policy rule produced it.
5. If the errors go one way (for example 3 or more false positives and no
   false negatives), the draft applies the policy more broadly or narrowly
   than the labellers did. Loosen or tighten the rule responsible, or fit a
   threshold with `tools/fit_threshold.py`, and re-score. Keep the change only
   if the check score does not drop. Snapshot.

## Phase 3: minimal pairs, only where labels leave a doubt (at most 10 points)

6. Write a minimal pair only for a rule that the random labels neither
   confirmed nor contradicted and that moves many pool records. Do not add a
   rule, or tighten one, on the strength of a minimal-pair answer alone: first
   check that it does not break any bought label, and prefer a label on a pool
   record the rule would move. If the owner's answer contradicts a bought
   label, follow the label.

## Phase 4: remaining budget

7. Spend what is left as in the uncertainty-with-rules strategy: buy the
   smallest-margin records a few at a time (`tools/uncertain.py`), turn errors
   into general rules, and test any rule that moves 3 or more pool records
   before trusting it. After each revision, re-score on all bought labels and
   keep it only if it fixes more labels than it breaks (`tools/diff_preds.py`
   shows what moved). Snapshot after each kept revision.

In the journal, record each question and minimal pair with its answer, the
check-label score of each draft, every case where an owner answer and a label
disagreed and which you followed, and how many pool predictions each rule
moved.
