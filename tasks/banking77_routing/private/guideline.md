# Support routing policy (private)

Each customer message goes to exactly one of six support teams. The team is
decided by the underlying customer intent; the mapping below lists which
intents belong to which team.

Team scopes:

- **fraud_and_security**: anything where the customer may have lost control of
  their card, phone, PIN or passcode, or does not recognise a transaction.
  Includes PIN changes, blocked PINs and forgotten passcodes (credential
  handling is security's job), and cards swallowed by an ATM (a retained card is
  treated as a possible compromise).
- **disputes_and_refunds**: the customer believes money was taken wrongly or
  should come back: refunds, duplicate charges, extra statement charges, wrong
  cash amounts, reverted payments. A complaint that a *wrong exchange rate was
  applied* to a payment or withdrawal is a dispute, not a pricing question.
- **cards**: getting, activating, delivering, linking and using cards (physical,
  virtual, disposable), Apple/Google Pay, card acceptance, and card payments or
  cash withdrawals that were declined or are pending.
- **payments_and_transfers**: top-ups and bank transfers (sending, receiving,
  pending, failed, cancelled, timing), and balances not updated after a
  transfer or deposit.
- **pricing_and_fx**: questions about fees, charges and exchange rates *in
  general* or fees that were charged, and which currencies or cards are
  supported.
- **account_and_compliance**: identity verification, source of funds, age
  limits, personal details, closing the account. Also: beneficiaries that are
  not allowed (a compliance restriction), verifying a top-up (a card
  verification check run by compliance), and which countries are supported
  (a regulatory question).

The counter-intuitive rules (things a reasonable person would route
differently) are: PIN/passcode issues and swallowed cards go to
fraud_and_security; wrong exchange rates on a transaction go to
disputes_and_refunds; beneficiaries that are not allowed, top-up
verification and country support go to account_and_compliance.
