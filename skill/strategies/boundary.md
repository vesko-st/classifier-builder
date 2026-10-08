# Strategy: work the boundary, triage confident errors, accept only real gains

For building from a labelled set. Follow this in place of reading
misclassified records one by one.

Why: a revision mostly moves the records near the decision boundary, the
correct ones as much as the wrong ones. Reading only errors shows what a rule
would fix, never what it would break. Errors far from the boundary are a
different problem: either a rule the definition is missing, or labels that
disagree with each other.

Use `tools/boundary.py` (see `--help`) on outputs over the **building set**,
with `--labels RUN_DIR/labels.jsonl --ids-file` a file of building ids. Keep
the development set for estimates only.

## Each round

1. **Read the boundary band.** `boundary.py band OUT.jsonl ...` lists the
   lowest-margin 15% of the building set, correct and wrong together, grouped
   by the pair of classes they sit between (use `--per-pair 20` or more on a
   binary task). For each large pair, read both sides and write in the journal
   what separates the records labelled A from those labelled B.
   - If you can state a general rule that separates them, sharpen the two
     options' descriptions (or split an option) along that rule.
   - If the gold labels split about evenly and nothing in the text separates
     them, declare the pair **ambiguous** in the journal and do not write a
     rule for it. At most, steady it with wording variants in an ensemble or a
     decision threshold fitted on the building set.
2. **Triage the confident errors.** `boundary.py confident OUT.jsonl ...`
   lists errors with margin >= 0.6, each with the most similar building record
   labelled the way the classifier predicted.
   - Where that record is near-identical (the tool flags high word overlap; on
     long inputs, judge by reading the two), the labels disagree: treat it as
     noise and do not write a rule for it.
   - Otherwise look for a group of confident errors with something in common:
     that is a rule the definition does not state. Add it as a general rule or
     a new option mapped to the right class.
3. **Accept only real gains.** Rerun the revision on the building set and run
   `boundary.py compare OLD.jsonl NEW.jsonl ...`. Keep the revision only if
   the verdict is ABOVE NOISE, or if the metric improves and the breaks are
   few and you can see why. When a revision is within noise, look at what it
   broke near the boundary, narrow it, and compare again, or revert it. Do not
   rescue a within-noise revision by checking the development set.
4. Snapshot each kept revision, with the development-set estimate.

## Stopping

Stop when every large pair in the band is either sharpened or declared
ambiguous, the confident errors left are mostly labelled the other way on
near-identical inputs, and the last two revisions were within noise. Score
the development set as rarely as you can; each look at it to choose between
versions makes the estimate optimistic.

In the journal, record per round: the band's pairs with their gold split and
your verdict (rule or ambiguous), the confident errors you triaged as noise or
as a missing rule, and each revision's compare line (fixed, broken, verdict)
and whether it was kept.
