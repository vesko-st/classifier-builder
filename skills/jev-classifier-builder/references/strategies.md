# Strategies for spending the user's time

Each strategy replaces step 3 of the workflow in `SKILL.md`. Pick by where the
missing knowledge lives. In our experiments (six tasks, 100 points of a
simulated user's time, about 50 labels' worth), the choice mattered most on
private mappings: on support-ticket routing, the strategies that asked about
the mapping scored 92–95% and uncertainty sampling 85–90%.

## Uncertainty with rules: when the meaning is in the text

Use when the class names and description say what the classes mean and the
difficulty is separating near-neighbours. It was the best label-only strategy,
and on a hate speech policy it matched the strategies that asked questions.

1. Run the classifier on the pool. Pick about 7 of the smallest-margin
   unlabelled records (`uncertain.py`) and ask the user to label them.
2. For each error, state the rule it suggests at the most general level
   consistent with *every* label so far, about meaning, not wording. Write it
   in `WORK/hypotheses.md` with the labels that support it, as `untested`.
3. Apply the rule, rerun, and list the unlabelled records it moves.
4. If it moves 3 or more records, test it: get a label on the moved record
   least like the supporting examples, or ask the user whether the rule holds.
   Mark it `confirmed`, `narrowed`, `broadened` or `rejected`.
5. When a label contradicts the plain meaning of its text and no rule explains
   it, mark it `suspected noise` rather than writing a rule for it.
6. Save the version and repeat.

Without step 2, plain uncertainty sampling swings the boundary with each
noisy batch; on a policy task it fell behind every other strategy.

## Policy, labels first: when the knowledge is a private mapping or policy

Use when the answer depends on a rule the user holds and the text cannot
reveal: which team handles which request, what counts under a house policy.
It was the best strategy on routing.

1. Read at least 100 inputs and list the **decisions** the policy must make:
   what is in scope, how each kind of input is handled, where two classes
   meet. For a mapping, list each kind of input with the class you would
   guess.
2. Ask about the decisions that affect the most inputs, in one message: state
   your reading as a rule and ask whether it holds and what the exceptions
   are. For a mapping, show the list with your guesses and ask for
   corrections.
3. Build a draft that mirrors the answers (criteria for a few classes; an
   option map for many) and save it.
4. Get 10 random labels and score the draft on them. If the errors go one way,
   the draft applies the policy more broadly or narrowly than the user's
   labels: loosen or tighten the rule responsible, or fit a threshold.
5. Ask about made-up edge cases only for a rule that labels have neither
   confirmed nor contradicted and that moves many inputs. When an answer
   contradicts a label, follow the label.
6. Continue with uncertainty with rules.

## Policy first: when the user can state the policy up front

Like the previous strategy, but spend more of the user's time on the policy
before any labels, including **minimal pairs**: two short made-up inputs that
differ only in the feature a rule depends on (the same insult aimed at a man
and at a woman; a statement and a quote of it), each labelled by the user.
Then build to mirror the policy and calibrate with 10 random labels. It works
when the user's account of the policy matches how they label; check that with
the random labels before trusting it on edge cases.

## Lean interview: a good default

1. Read at least 200 inputs. List the kinds of input you see and mark each
   **inferable** (its class follows from the description and the text) or
   **private** (it depends on a rule nobody has stated). Draft and save.
2. If private kinds cover many inputs, ask about them in one message, stating
   your reading of each as a rule. Skip this when everything important is
   inferable: a label settles one phrasing more reliably than a question.
3. Spend the rest on labels in batches of 6–10: uncertain records for the
   boundary, `sample.py --mode category` for options with no label yet or a
   suspected wrong mapping, and a targeted label to verify a new rule.
4. Turn errors into rules; label one record a revision moves before keeping
   a revision that moves 10 or more; keep it only if it fixes more labels
   than it breaks.

## When there is nothing to learn

When the label is an outcome nobody defines, or the first draft is already
close to what the user wants, building mostly adds risk. On two such tasks no
strategy beat the first classifier by much, and acting on the user's answers
about borderline cases lowered accuracy every time it was measured. Get a
random check sample, fix what it shows is clearly wrong, and stop.
