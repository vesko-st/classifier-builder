# Banking77 intent labels (private)

The labels are the 77 Banking77 intents, assigned by the dataset's annotators.
Intent names are the only official definition; the labelled records you are
shown are the ground truth for where boundaries fall.

Boundaries that commonly matter, as seen in the labelled data:

- `pending_*` (still processing) vs `declined_*` / `failed_transfer` (rejected)
  vs `*_not_recognised` (customer doesn't recognise it) vs `reverted_*`.
- Fee intents (`*_fee_charged`, `*_charge`) are about a fee being applied;
  `exchange_rate` / `exchange_charge` are general FX questions;
  `*_wrong_exchange_rate*` is a complaint about a specific transaction.
- `card_arrival` (my card hasn't come) vs `card_delivery_estimate` (how long
  will it take); `get_physical_card` (get the physical version of an existing
  card) vs `order_physical_card` (ordering one).
- `verify_my_identity` (how to verify) vs `why_verify_identity` (why it's
  needed) vs `unable_to_verify_identity` (it isn't working).
- `topping_up_by_card` (how/problems topping up by card) vs `top_up_by_card_charge`
  (fee for it) vs `top_up_failed` / `pending_top_up` / `top_up_reverted`.

Answer from the labelled records when a question concerns specific wording.
