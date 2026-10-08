# Strategy: policy first

Follow this in place of step 3 of the skill's workflow. Learn the labelling
policy from the owner before buying labels, test its boundaries with made-up
minimal pairs, build the classifier to mirror the policy, and use labels to
check and calibrate it.

## Phase 1: policy questions (about 25–35 points)

1. Read at least 100 pool records. List the **decisions** the policy must
   make: what is in scope, which targets or topics count, which forms (quoted,
   reported, sarcastic, joking, questions) count, and where two classes meet.
2. Ask the owner about the decisions that affect the most records, one
   5-point part each. State your current reading as a rule and ask whether it
   holds and what the exceptions are ("Is X labelled A even when Y? If not,
   what decides it?"). Ask before labels, while every answer can still shape
   the draft.

## Phase 2: minimal pairs (about 10–20 points)

3. For each rule whose boundary is still unclear, write a **minimal pair**:
   two short made-up messages in the pool's style that differ only in the
   feature the rule depends on (same insult aimed at a man vs a woman; a
   statement vs a quote of it; a policy opinion vs an attack on people). Ask
   the owner to label each ("Label each of these made-up messages: A: …
   B: …"). Each message is a 2-point part. One pair per unclear rule; stop
   when answers become predictable.

## Phase 3: build to mirror the policy

4. For binary or few-class tasks, use the `criteria` shape: one yes/no
   question per test the policy applies, and a `rule` that combines them the
   way the owner described (an OR of ANDs; `!name` for "not"). Each question
   should be one judgement Jev can make from meaning. For many-class tasks,
   use a `choice` with a `map` or `two_level`, and put the policy answers into
   the instructions and option descriptions.
   Snapshot it.

## Phase 4: check and calibrate (about 20 points)

5. Run the pool and buy **10 random labels** (`tools/sample.py --mode random`).
   Score the classifier on them. If the errors all go one way (for example 3
   or more false positives and no false negatives), fit a threshold with
   `tools/fit_threshold.py` and set `"decision"`, but move it only as far as
   those labels clearly support. Snapshot.

## Phase 5: remaining budget

6. Spend what is left as in the uncertainty-with-rules strategy: buy the
   smallest-margin records a few at a time, turn errors into general rules,
   and test any rule that moves 3 or more pool records (a label on a moved
   record, a minimal pair, or a policy question) before trusting it. Snapshot
   after each revision.

In the journal, record each question and minimal pair with the answer and the
rule it produced, the random-label score, the threshold decision, and how many
pool predictions each rule moved.
