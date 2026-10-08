# Constraint: rules, not examples

This applies on top of the workflow and any strategy, and overrides them where
they differ: where the skill or a strategy says to add examples, write a rule
instead.

Labels are evidence for rules, never content of the classifier. The classifier
must work on test records you have never seen, and a pasted record only
describes itself.

## What may not go into the classifier

- No text from a pool record, whole or in part, in the instructions, rules or
  option descriptions: no labelled messages, no quoted phrases taken from
  them, no lightly edited copies.
- No lists of real messages as illustrations ("e.g. '...'").
- A short phrase you invent yourself to name a pattern is allowed when the
  surrounding rule already states the pattern in words (for example "a
  question that introduces a fact about the charity, such as 'did you know
  ...?'"). It must not be copied from a record.

## How to use a label

For every error, or every record the classifier got right only narrowly:

1. Say what the record has in common with the records it should be grouped
   with, and what separates it from the class it was confused with. State
   this as a rule about meaning (who acts, what is asked or claimed, the
   speaker's intent, the condition that decides the class), not about its
   words.
2. Write the hypothesis in `RUN_DIR/hypotheses.md` with the ids of the labels
   that motivated it.
3. Test it before keeping it: find other pool records the rule should cover
   and should leave alone (search the pool by meaning, not by the record's
   words), apply the revision, rerun, and read the records it moves. Buy a
   label for a moved record when you are unsure it moved the right way.
4. Keep the rule only if it holds beyond the record that prompted it. A rule
   that fixes only that one record is an example in disguise: make it more
   general or drop it.

If you cannot state a rule without quoting the record, leave the hypothesis
pending until more labels show the pattern.

## Check before every snapshot

Run `../.venv/bin/python tools/copy_check.py CLASSIFIER.json --pool RUN_DIR/pool.jsonl`
and rewrite every passage it reports as a rule in your own words. Snapshot
only when it reports nothing.

In the journal, record each hypothesis with its supporting label ids, how you
tested it (records checked, records moved) and whether it was kept.
