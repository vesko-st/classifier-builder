# Strategy: uncertainty sampling with general rules and hypothesis tests

Follow this in place of step 3 of the skill's workflow. Labels are found by
uncertainty, turned into the most general rules they support, and those rules
are tested before they are trusted.

Loop until the budget is spent:

1. **Run** the current classifier on the whole pool with `-o`.
2. **Pick uncertain records.** For every record you have not bought, compute
   the margin (top probability minus second; use `class_probabilities` when
   the classifier has a `map`). Take the smallest-margin records, skipping
   near-paraphrases of records in the batch or already bought. Buy them in one
   `label` call. Use about 7 per round, leaving room for tests (step 5).
3. **Write hypotheses, not patches.** For each label the classifier got wrong,
   state the rule it suggests at the most general level that is consistent
   with *every* label bought so far. Prefer rules about meaning ("a PIN
   question about a card the customer hasn't received yet") over the example's
   wording ("how do I find the PIN"). Avoid keyword rules unless the labels
   show the keyword itself is decisive. Record each hypothesis in
   `RUN_DIR/hypotheses.md` with: the rule, the labels supporting it, and
   status `untested`.
4. **Measure each hypothesis's reach.** Apply it to the classifier, rerun the
   pool, and list the unlabelled records whose prediction it changes.
5. **Test before trusting.** For every hypothesis that moves 3 or more
   records, test it:
   - buy the label of the moved record *least* similar to the supporting
     examples (the one most likely to break the rule); or
   - when the rule covers a whole group of messages, ask one 5-point policy
     question that states the rule and asks whether it holds.
   Then mark it `confirmed`, `narrowed` (rewrite it to exclude the failure and
   re-measure), `broadened`, or `rejected` (revert it).
6. **Suspected label noise.** When a label contradicts the plain meaning of its
   message and no general rule explains it, don't write a rule. Mark it
   `suspected noise` and at most add it as an example. If it matters (a
   paraphrase group of 3+ in the pool), test it by buying one paraphrase: if
   the paraphrase agrees, promote it to a rule.
7. **Snapshot** after each round's revision, then go back to 1.

The final classifier must agree with every label that isn't `suspected noise`.

In the journal, record per round: uncertainty labels bought and how many the
classifier had right, hypotheses written, tests run and their outcomes, and
pool predictions changed. Keep `hypotheses.md` current.
