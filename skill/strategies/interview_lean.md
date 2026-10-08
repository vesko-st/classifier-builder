# Strategy: read first, ask only for what the text cannot tell, label the rest

Follow this in place of step 3 of the skill's workflow. Reading the pool is
free; spend points only on what reading cannot give you. You decide how to
split the budget: there is no fixed allowance for questions, and every point
you do not need for questions should buy labels.

## 1. Read the pool (free)

Read at least 200 pool records. List the phenomena you see (the kinds of
message, the forms they take, where two classes meet) and estimate how many
records each covers. Mark each phenomenon **inferable** (its class follows
from the description and the text) or **private** (its class depends on a
policy, mapping or convention the description does not state: which team
handles a request, what counts under an annotation policy). Write the list in
`RUN_DIR/phenomena.md`, then build a first classifier from it, run it on the
pool, and snapshot.

## 2. Ask only about private phenomena (optional)

If the list has private phenomena covering many records, ask about them, in
one message where you can: state your reading of each as a rule and ask
whether it holds and what the exceptions are. Skip this step entirely when
everything important is inferable; a label answers a question about one
phrasing more reliably and more cheaply. Revise and snapshot.

## 3. Labels (the rest of the budget)

Spend the remaining points on labels, in batches of about 6–10, choosing each
batch for what you most need to learn next:

- `tools/uncertain.py OUT.jsonl --labels RUN_DIR/labels.jsonl -n N` for records
  near the boundary (the usual choice);
- `tools/sample.py OUT.jsonl --mode category -n N --labels RUN_DIR/labels.jsonl`
  when some large options have no label yet, or you suspect an option is
  mapped to the wrong class;
- a targeted label on a record a new rule moves, to verify the rule.

Go back to questions only if labels reveal a private rule you cannot pin down
from them, such as labels that contradict your reading of the policy.

After each batch, turn errors into hypotheses under the rules-only
constraint, apply the revision, rerun, and compare with `tools/diff_preds.py`
or `tools/boundary.py compare`:

- when a revision moves 10 or more pool records, label the moved record least
  like the labels that motivated it before keeping the revision;
- keep a revision only if it fixes more bought labels than it breaks, and
  breaks at most one; otherwise narrow it or revert it;
- snapshot kept revisions.

## Finish

The last snapshot is your final classifier: make it your best version, not
necessarily your latest. Base your estimate on the labels you bought, noting
that boundary labels are harder than average.

In the journal, record the phenomena list with each item marked inferable or
private, why you did or did not ask, each question with its answer, each
batch (how chosen, how many the classifier had right), each verification, and
kept and reverted revisions.
