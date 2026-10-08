# How the Banking77 labels apply the policy: notes from the 1,000-record pool

## Overall picture
I searched every class. Each class has 3 to 19 records. The rarest are contactless_not_working (3), virtual_card_not_working (4), card_swallowed and card_acceptance (6 each). Labels mostly follow the obvious keyword in the message, and nearly every class is internally coherent. I estimate that about 2–4% of records are clearly mislabelled, with no pattern to them.

Two label strings are written oddly and must be matched exactly: `reverted_card_payment?` (with the question mark) and `Refund_not_showing_up` (capital R).

## Biggest departure: get_physical_card means PIN questions
All 11 get_physical_card records ask about the card's PIN: "I haven't received my PIN", "where do I find my PIN", "can I set my own PIN". None asks for a physical card.

Requests for an actual card go to **order_physical_card**: "I'd like a physical card", "how do I order a card", "is the physical card free", "do you ship cards anywhere".

This contradicts the written policy's gloss. I am highly confident about it.

## PIN classes
- **pin_blocked**: PIN blocked or locked after wrong attempts.
- **change_pin**: changing, updating or setting a new PIN.

"Set up a new PIN" went to change_pin, but "set my physical card PIN" went to get_physical_card. One message about a card frozen after too many wrong PINs was labelled declined_cash_withdrawal.

## Pending, declined, failed and reverted
**Pending.** Any message containing "pending" goes to the matching pending_* class by transaction type (card payment, transfer, top-up, cash). This holds in about 95% of cases. The exception is a small £1/$1 pending charge, which goes to extra_charge_on_statement. Pending classes also take "hasn't gone through yet" and "money is stuck".

**Card payments that don't go through** are split:
- declined_card_payment: "card declined" or "not accepted in a shop".
- card_not_working: vaguer "my card doesn't work". Two "declined at a restaurant" messages also went here.
- declined_transfer: some messages that say "declined" while buying online. Roughly 3 of 13 declined_transfer records are really card purchases.

**Transfers that don't go through** are split three ways with no reliable cue:
- declined_transfer: the word "declined".
- failed_transfer: "failed", "error", "not approved", and flat or mortgage payment errors.
- beneficiary_not_allowed: anything about a beneficiary, plus about half of the generic "I can't transfer / not possible / keeps erroring" messages, and one crypto purchase being blocked.

My confidence here is only moderate.

**`reverted_card_payment?`** covers: payment returned to the account, payment cancelled, "merchant refused payment", and even "my payment wasn't accepted" or "didn't work". So it also absorbs some messages that read like declines.

## Top-ups
- **pending_top_up**: still pending or slow, and also "not sure it went through" or "funds not available yet".
- **top_up_failed**: didn't work, denied, or the card was declined for the top-up.
- **top_up_reverted**: reverted, returned, cancelled, or "money was there and now it's gone". One "app declined my top-up" message also went here.
- **topping_up_by_card**: how to top up by card or "transfer money with my credit card". It also takes "I topped up by card and the money disappeared"; when a card is mentioned, these go here rather than to top_up_reverted.
- **top_up_by_card_charge**: card top-up fees, especially for US- or EU-issued cards.
- **top_up_by_bank_transfer_charge**: bank-transfer top-up fees. It also takes every SWIFT/SEPA question even with no fee mentioned ("can I use SWIFT?"), plus "why do you charge for transfers" and "how much would a transfer cost".
- Generic "are there top-up fees" questions are split between the two charge classes.
- **supported_cards_and_currencies**: which cards or currencies can be used to add money, including American Express.
- **apple_pay_or_google_pay**: any message naming Apple Pay, Google Pay or Apple Watch. This wins over other cues, including Amex in Apple Pay.
- **transfer_into_account**: how to add money from another bank account.
- **top_up_by_cash_or_cheque**: depositing cash or cheques.
- **automatic_top_up**, **top_up_limits**, **verify_top_up** (verification code and why a top-up needs verifying): all consistent.

## Fees and charges
Vague complaints are where these classes blur. My confidence is moderate.
- **transfer_fee_charged**: transfer fees. It also takes bare "why was I charged", "will I get extra charges", and fees for "banking abroad", including one online purchase from abroad.
- **card_payment_fee_charged**: fees for using the card, and vague "hidden fee" or "too many fees" complaints.
- **cash_withdrawal_charge**: ATM or withdrawal fees, including general "is there an ATM fee?" questions, not only complaints.
- **extra_charge_on_statement**: almost always an extra £1, $1 or €1. This holds even when the customer doesn't recognise it or it is pending, at about 90%.

## Unrecognised transactions
- **card_payment_not_recognised**: wording about a "payment" or "purchase" the customer didn't make.
- **direct_debit_payment_not_recognised**: anything naming a direct debit. It also takes many vague ones ("unknown charge", "unauthorised charge", "dispute a charge"). About 5 of its 18 records never mention a direct debit.
- **cash_withdrawal_not_recognised**: cash or ATM withdrawals not made by the customer. It also has two strays: a generic "charge I didn't make" and someone buying flights with the card.
- **compromised_card**: "someone may be using my card" or "my details were stolen". Overlaps with the above when specific transactions are cited.
- **lost_or_stolen_card**: lost, stolen, missing card, or "freeze my card now".
- **lost_or_stolen_phone**: lost or stolen phone, including "left my phone at the hotel".

## Exchange rates
- **exchange_rate**: general questions about rates and how they are set.
- **exchange_charge**: FX fees and volume discounts.
- **exchange_via_app**: how to exchange, and which currency pairs.
- **fiat_currency_support**: which currencies can be held or exchanged. It overlaps with exchange_via_app, for example "which currencies are available for exchange" went to via_app.
- **wrong_exchange_rate_for_cash_withdrawal**: unlike the policy, this also takes general questions about rates and fees when getting cash abroad ("what rate do I get at a foreign ATM?", "can I withdraw abroad without fees?"). It also takes "the rate was wrong when I was abroad" with no transaction type stated.
- **card_payment_wrong_exchange_rate**: purchase-rate complaints, plus any generic "the rate is wrong / bad / a rip-off" and even "what was the rate on my last transaction".

## Card delivery and card management
- **card_arrival**: card not received, and all tracking-number requests.
- **card_delivery_estimate**: how long or when, express delivery, and "how will I get my card". It sometimes also takes "ordered weeks ago, when can I expect it?".
- **card_about_to_expire**: expiring cards, including the cost and speed of the replacement. One message about shipping to China also landed here.
- **country_support**: supported countries, and also "can the card be mailed to Europe".
- **getting_spare_card**: second or extra cards, their fees, and card-count limits.
- **card_linking**: linking or adding a card in the app, and also reactivating a card that was lost and then found.
- **activate_my_card**: activation, including "can't activate".
- **atm_support**: where to find ATMs, and which accept the card.
- **card_acceptance**: which merchants accept the card.
- **card_swallowed**: card kept by an ATM.
- **visa_or_mastercard**: any Visa or Mastercard preference or question.
- **getting_virtual_card**: covers both ordering a virtual card and not having received one.
- **get_disposable_virtual_card**: how disposable cards work and how to get one.
- **disposable_card_limits**: restrictions and how many disposable cards are allowed.
- **virtual_card_not_working**: a virtual card that doesn't work or is rejected.
- **contactless_not_working**: contactless failures.

## Identity and verification
These follow the policy at roughly 85%:
- **verify_my_identity**: how to verify and which documents are accepted.
- **why_verify_identity**: why verification is needed, and also "can I use my account before verification finishes".
- **unable_to_verify_identity**: verification failing, "app doesn't recognise me", and also "how long will verification take".

There are strays: "I can't do the verification" went to why_verify_identity, and "what do I need to bring for identification" went to unable_to_verify_identity.

**verify_source_of_funds** is mostly literal ("where did my money come from") but also takes "can I see my available money" and "what security protects my money".

## Cash withdrawals
- **declined_cash_withdrawal**: ATM refused or "won't give cash", including "first time using my card, is it working?".
- **pending_cash_withdrawal**: pending withdrawal, or ATM failed but the transaction shows as in progress.
- **wrong_amount_of_cash_received**: got less, or more, than requested.

## Transfers: timing and arrival
- **transfer_timing**: general "how long do transfers take", especially incoming from the US or Europe.
- **pending_transfer**: an outgoing transfer is pending, or the customer has waited long.
- **transfer_not_received_by_recipient**: the named recipient (friend, landlord, son) hasn't got it, plus some generic "taking too long" messages.
- **balance_not_updated_after_bank_transfer**: balance unchanged after a transfer, and the recurring "how long does a UK account transfer take, it isn't showing" wording.
- **balance_not_updated_after_cheque_or_cash_deposit**: a cheque or cash deposit isn't showing.

The boundary between pending_transfer and transfer_not_received_by_recipient is soft; I'd put it at about 75% predictable.

## Refunds, cancellations and duplicates
- **request_refund**: wanting a refund, return policy, cancelling a purchase, and "how long does a refund take".
- **Refund_not_showing_up**: a refund already requested or expected but missing. This boundary is consistent at about 95%.
- **cancel_transfer**: cancel or "revert" a transaction, or money sent to the wrong account.
- **transaction_charged_twice**: duplicate charges. One message asking for "a transaction reversed" also landed here.

## Account
These are all consistent:
- **edit_personal_details**: changing personal details, including a new address.
- **terminate_account**: closing or deleting the account, including dissatisfied customers.
- **passcode_forgotten**: app passcode or login code.
- **age_limit**: age limits, including opening accounts for children.
- **receiving_money**: getting money from friends or salary.

## Apparent noise
These records look mislabelled. Don't treat them as rules:
- "any charges for a new card?" labelled contactless_not_working
- "can I get support?" labelled country_support
- "how do I get disposable cards" labelled disposable_card_limits
- "security for everyday purchases" labelled get_disposable_virtual_card
- "can I use my virtual card for memberships" labelled virtual_card_not_working
