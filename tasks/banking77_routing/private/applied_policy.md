# How the labels route messages: banking77_routing

## Overall picture

The labels follow the intent-to-team mapping closely. Most boundaries are applied with near-perfect consistency. Three places are noisy:
- Generic "my card keeps getting declined" messages are split between two teams.
- Questions about exchange rates or fees for cash withdrawals abroad usually go to disputes, even when they are worded as general questions.
- A few vague "transfer not possible" or "purchase not going through" messages go to account_and_compliance.

The label is set by the intent the message came from, not by its surface wording. A refund request about an unknown payment still goes to fraud, and "I shouldn't have been charged this fee" still goes to pricing.

## fraud_and_security

**Rule as applied:** the customer has lost control of a credential, card or phone, or does not recognise a transaction. Confidence is high and the labels are about 100% consistent.

- **Changing a PIN:** changing, resetting, unblocking, forgetting or "rejected" PINs, and "can I change my PIN at an ATM", all go here (about 21 of 21).
- **Getting a first PIN goes to cards.** Messages like "where's my PIN?", "how do I set the PIN on my new card?" or "does the PIN come separately?" are labelled cards (about 15 of 15). The written policy does not draw this line; the labels do. A card refused at an ATM even though the right PIN was used is also cards.
- **Passcodes and logins:** forgotten passcodes, password resets, "I can't log in" and "locked out of the app" all go here (13 of 13).
- **Swallowed cards:** a card kept by an ATM always goes here (about 9 of 9), including "I need a new card because the ATM took mine".
- **Lost or stolen cards, phones and wallets:** these go here, including "my phone is at a hotel, can I still use the app?" Exceptions:
  - "I found the card I reported lost, can I reactivate it?" goes to cards.
  - "I lost my card, will a replacement cost me?" goes to cards (one case).
- **Unrecognised transactions:** unknown card payments, cash withdrawals or direct debits go here even when the customer asks for a refund, wants to "dispute" the payment or asks to cancel it. "What is this direct debit?" and "there's an unknown charge on my account" also go here. "There's money in my account I didn't put there" is also labelled fraud.

## disputes_and_refunds

**Rule as applied:** money was taken wrongly or should come back. Confidence is high.

- **Refunds:** refund requests, refund policy, refunds not showing yet, and items never delivered.
- **Duplicate charges:** charged twice, including "declined once, then charged twice".
- **Small unexplained charges:** an extra £1 or $1 charge, or "what is this extra fee on my statement?" All of these go to disputes. Contrast: a fee the customer links to a card payment, transfer or ATM use goes to pricing (see below). Wording like "unknown charge" or "a charge I didn't make" goes to fraud.
- **Wrong amount of cash:** getting less, more or the wrong amount of cash from an ATM, and "I haven't received my cash yet".
- **Cancelled or reverted card payments:** "my card payment was cancelled", "payment returned to my account" and "under what conditions does a payment revert?"
- **Wrong exchange rates:** a complaint that the wrong rate was applied to a purchase or withdrawal goes here (about 20 cases, all consistent). The labels go further than the written policy in two ways:
  - Complaints that a currency exchange "cost too much" or that exchange charges "aren't right" go here, not to pricing (3 of 3).
  - Questions about rates or fees for cash withdrawals abroad mostly go here, even when they read as general questions. Examples are "what are the exchange rates for getting cash?", "what are weekend rates for cash?" and "are there extra fees for withdrawing in another country?" (about 5 cases). Confidence on this is moderate. An engineer would expect these to be pricing questions.

## pricing_and_fx

**Rule as applied:** fees, rates and supported currencies or cards, in general or for one specific charge. Confidence is high.

- **Fees already charged:** a fee on a card payment, transfer, ATM withdrawal or top-up goes here, even when the customer says it shouldn't have been charged and asks for it to be fixed (about 40 cases, with essentially one exception). The written policy might suggest disputes for some of these; the labels say pricing. This includes "the recipient got less than I sent". The one exception: "I was overcharged at the ATM and nothing mentioned a fee" went to disputes.
- **General questions:** how rates are set, the rate for EUR, the cost of exchanging, how to exchange currencies in the app, and which fiat currencies can be held.
- **Cards and currencies for top-ups:** which cards or currencies can top up an account, and whether American Express or "my credit card" is accepted for top-ups. SWIFT or SEPA availability and fees also go here.
- **What goes to cards instead:** questions about choosing Visa or Mastercard. Fees for getting a physical card, extra cards or express delivery also go to cards (all consistent).

## cards

**Rule as applied:** getting, delivering, activating, linking and using cards; Apple Pay and Google Pay; where cards are accepted; declined or pending card payments and withdrawals. Confidence is high, except for declines.

- **Pending or missing withdrawals and payments:** a pending card payment, or a cash withdrawal that is still pending or hasn't come off the balance, goes here. One ATM deposit that "hasn't cleared" also went here.
- **Top-ups through Apple Pay or Google Pay:** these go to cards (8 of 8), even "top-up isn't working with my Amex in Apple Pay".
- **Disposable and virtual card limits** go here. Top-up limits do not (see payments).
- **Cards sent abroad:** "Will you send a new card to China?" goes to cards, not to country support.
- **Declines (noisy):** a decline at a shop, restaurant or ATM goes to cards. A generic "my card keeps getting declined" is labelled cards about two times in three and payments_and_transfers about one time in three. Those payments cases come from top-up failures, such as "declined at online checkout" or "you keep denying my transfers". One "my card won't let me purchase" message went to account_and_compliance.

## payments_and_transfers

**Rule as applied:** top-ups and bank transfers (any status), receiving money, deposits and balance updates. Confidence is high.

- **Top-ups:** pending, failed, declined or reverted top-ups; top-ups by card, cash or cheque; automatic top-up; and top-up limits. A generic "daily limit on my card" also went here.
- **Transfers:** timing, pending, declined or failed transfers; cancelling a transfer; money sent to the wrong account; and a recipient who hasn't received the money.
- **Receiving money:** salary in another currency, friends topping up the account, and moving money in from other accounts.
- **Deposits:** cash or cheque deposits not showing, and a balance not updated after a transfer.
- **Crypto top-ups** that failed, where the money then vanished, go here.

## account_and_compliance

**Rule as applied:** identity verification, source of funds, age limits, personal details, closing the account, blocked beneficiaries, top-up verification and supported countries. Confidence is high.

- **Top-up verification** goes here (10 of 10): verification codes and "how do I verify my top-up card?"
- **Supported countries** go here (8 of 8), including "can I use this all over the world?" and "do you give cards to people outside the UK?"
- **Beneficiaries not allowed:** this rule is applied more broadly than written. Any transfer the customer is told is "not allowed" or "not possible" goes here, including transfers to a crypto exchange, "why can't I transfer to an account?" and "my funds aren't transferring to my bank" (about 8 cases). Transfers described as "declined" or "failed" go to payments. The line depends on wording and is not fully clean. One "trying to buy crypto, not going through" message also went here.
- **Source of funds** includes "where did this money come from?" (compare the fraud wording above).
- **Also here:** accounts for children or minors, name, address and phone-number changes, and general questions such as "what security protects my money?"

## Where the labels depart from the written policy

1. Getting a first PIN goes to cards; only changing or problem PINs go to fraud.
2. A fee that was charged is pricing even when it is disputed. Only unexplained statement charges go to disputes.
3. Exchange-cost complaints and questions about rates or fees for cash withdrawals abroad lean towards disputes.
4. Any transfer refused as "not allowed" or "not possible" goes to account_and_compliance, not only beneficiary cases.
5. Top-ups through Apple Pay or Google Pay go to cards. Asking which cards can top up goes to pricing, but Visa versus Mastercard goes to cards.
6. Unrecognised transactions go to fraud even when the customer asks for a refund or a dispute.
