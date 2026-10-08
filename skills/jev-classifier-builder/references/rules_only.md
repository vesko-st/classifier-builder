# Rules, not examples

Labels are evidence for rules, never content of the classifier. The classifier
has to work on inputs it has never seen, and a pasted input only describes
itself. In our experiments, classifiers built this way contained no copied
text and scored the same as or better than those that pasted labelled
examples.

## What stays out of the classifier

- No text from the user's data, whole or in part, in instructions, rules or
  option descriptions: no labelled inputs, no phrases taken from them, no
  lightly edited copies.
- No lists of real inputs as illustrations.
- A short phrase you invent to name a pattern is fine when the rule around it
  already states the pattern in words ("a question that introduces a fact
  about the charity, such as 'did you know ...?'").

## How to use a label

For every error, or every input the classifier got right only narrowly:

1. Say what the input shares with the inputs it belongs with, and what
   separates it from the class it was confused with, as a rule about meaning:
   who acts, what is asked or claimed, the intent, the condition that decides
   the class.
2. Test the rule on other inputs it should cover and should leave alone:
   apply it, rerun, and read the inputs it moves. Ask for a label when you are
   unsure a moved input moved the right way.
3. Keep the rule only if it holds beyond the input that prompted it. A rule
   that fixes only that one input is an example in disguise: generalise it or
   drop it.

If you cannot state a rule without quoting the input, wait until more labels
show the pattern.

Before saving a version, run `python $S/copy_check.py CLF.json --pool
WORK/pool.jsonl` and rewrite anything it reports in your own words.
