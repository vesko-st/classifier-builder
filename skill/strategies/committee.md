# Strategy: committee of classifiers

Follow this in place of step 3 of the skill's workflow. You build several
classifiers that differ in shape and wording, combine them into an `ensemble`,
and buy labels where they disagree. Wording noise that flips one classifier's
borderline records gets outvoted, and disagreement points at real ambiguity.

## Setup

1. **Build 3 members** from the task description alone, each a genuinely
   different reading of the task, not a copy with small edits:
   - a flat `choice` with fine-grained options and a `map`;
   - a `two_level` classifier (route by topic, then decide within it);
   - for binary or few-class tasks, a `criteria` classifier: one yes/no
     question per test in the policy, combined by a rule; for many-class
     tasks, a second flat choice written independently (different option
     split, different descriptions).
   See `tools/jev_classifier.py --help` for the `ensemble`, `two_level` and
   `criteria` formats. Put them in one ensemble file; snapshot it.

## Loop until the budget is spent

2. **Run** the ensemble on the pool with `-o`.
3. **Pick disagreements.** `tools/uncertain.py OUT.jsonl --by disagreement
   --labels RUN_DIR/labels.jsonl -n 25` lists records where members disagree,
   most evenly split first. Buy **10**, skipping near-paraphrases of each other
   or of records already bought. When members agree almost everywhere, take
   the smallest ensemble margins instead.
4. **Fix the members that were wrong, and only those.** For each label, change
   the member(s) that voted against it, in their own style. Keep the members
   different: do not copy one member's wording into another. Describe
   patterns in words rather than pasting every bought text as an example.
5. **Check every member** on all bought labels (run the ensemble on
   `labels.jsonl` and read `member_predictions`). If one member is clearly
   worse than the others (fewer than two-thirds as many labels right), lower
   its weight with `"weights"` or rebuild it.
6. **Snapshot** the ensemble, then go back to 2.

In the journal, record per round: how many pool records the members disagree
on, the 10 picks and how many the ensemble had right, which members you
changed, and each member's accuracy on the bought labels.
