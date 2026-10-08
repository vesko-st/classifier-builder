# Strategy: uncertainty sampling

Follow this in place of step 3 of the skill's workflow. Spend the budget on
labels for the pool records your current classifier is least sure about. Ask
no questions and buy no random labels.

Loop until the budget is spent:

1. Run the current classifier on the whole pool with `-o`.
2. For every record you have not bought, compute the **margin**: the top
   probability minus the second-highest (use `class_probabilities` when the
   classifier has a `map`, otherwise `probabilities`). Small margin = uncertain.
3. Pick a batch of **10** records with the smallest margins. Keep the batch
   diverse: skip a record if it is a near-paraphrase of one already in the
   batch, or of one you already bought, and take the next one instead.
4. Buy their labels in one `label` call.
5. Revise the classifier from what the labels show: fix option descriptions,
   add the bought texts as examples, split or merge options. Check the revision
   still agrees with all labels bought so far.
6. Snapshot the revision, then go back to 1 with the revised classifier, so the
   next batch is chosen by the new classifier's uncertainty.

In the journal, record each batch's margins (range) and how many of the 10 the
classifier had right before revising.
