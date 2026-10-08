"""Regroup a flat 77-intent choice classifier into a two_level one, keeping its descriptions."""

import json
import sys

GROUPS = {
    "card_ordering_and_setup": ("Getting, ordering, delivering, activating, linking or choosing a card (physical, virtual, disposable, spare), Apple/Google Pay, which cards and currencies are supported.", [
        "activate_my_card", "card_arrival", "card_delivery_estimate", "card_about_to_expire", "get_physical_card",
        "order_physical_card", "getting_spare_card", "getting_virtual_card", "get_disposable_virtual_card",
        "disposable_card_limits", "card_linking", "visa_or_mastercard", "apple_pay_or_google_pay",
        "supported_cards_and_currencies"]),
    "card_payments_and_card_problems": ("Using a card to pay: card not working, declined, pending, reverted or unrecognised card payments, card payment fees or exchange rates, a card swallowed by an ATM.", [
        "card_not_working", "contactless_not_working", "virtual_card_not_working", "card_acceptance",
        "declined_card_payment", "pending_card_payment", "reverted_card_payment?", "card_payment_not_recognised",
        "card_payment_fee_charged", "card_payment_wrong_exchange_rate", "card_swallowed"]),
    "cash_and_atm": ("Withdrawing cash at an ATM: ATM support, withdrawal fees, declined, pending or unrecognised withdrawals, wrong amount or exchange rate.", [
        "atm_support", "cash_withdrawal_charge", "cash_withdrawal_not_recognised", "declined_cash_withdrawal",
        "pending_cash_withdrawal", "wrong_amount_of_cash_received", "wrong_exchange_rate_for_cash_withdrawal"]),
    "transfers": ("Bank transfers in or out: sending, receiving, cancelling, pending, failed or declined transfers, timing, fees, beneficiaries, balance not updated after a transfer.", [
        "cancel_transfer", "declined_transfer", "failed_transfer", "pending_transfer", "transfer_into_account",
        "transfer_not_received_by_recipient", "transfer_timing", "transfer_fee_charged", "receiving_money",
        "beneficiary_not_allowed", "balance_not_updated_after_bank_transfer"]),
    "top_ups": ("Adding money to the account (topping up) by card, bank transfer, cash or cheque: pending, failed, reverted top-ups, limits, auto top-up, top-up fees and verification.", [
        "automatic_top_up", "pending_top_up", "top_up_failed", "top_up_limits", "top_up_reverted",
        "topping_up_by_card", "top_up_by_cash_or_cheque", "top_up_by_bank_transfer_charge", "top_up_by_card_charge",
        "verify_top_up", "balance_not_updated_after_cheque_or_cash_deposit"]),
    "charges_refunds_and_fx": ("Refunds, duplicate or extra charges, unrecognised direct debits, exchange rates and currency exchange in general.", [
        "request_refund", "Refund_not_showing_up", "transaction_charged_twice", "extra_charge_on_statement",
        "direct_debit_payment_not_recognised", "exchange_rate", "exchange_charge", "exchange_via_app",
        "fiat_currency_support"]),
    "security_and_account": ("Lost, stolen or compromised card or phone, PIN and passcode, identity verification, source of funds, age, personal details, supported countries, closing the account.", [
        "compromised_card", "lost_or_stolen_card", "lost_or_stolen_phone", "change_pin", "pin_blocked",
        "passcode_forgotten", "verify_my_identity", "unable_to_verify_identity", "why_verify_identity",
        "verify_source_of_funds", "age_limit", "edit_personal_details", "terminate_account", "country_support"]),
}


def main(src: str, dest: str) -> None:
    flat = json.load(open(src))
    crit = flat["criteria"]
    listed = [i for _, (_, intents) in GROUPS.items() for i in intents]
    assert sorted(listed) == sorted(crit), (set(crit) ^ set(listed))
    instructions = flat["instructions"]
    two = {
        "version": 1,
        "name": flat["name"] + "_two_level",
        "type": "two_level",
        "state_template": flat["state_template"],
        "router": {
            "instructions": "Which area of banking is this customer message to a digital bank's support chat about?",
            "criteria": {g: desc for g, (desc, _) in GROUPS.items()},
        },
        "groups": {
            g: {"instructions": instructions, "criteria": {i: crit[i] for i in intents}}
            for g, (_, intents) in GROUPS.items()
        },
    }
    json.dump(two, open(dest, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
