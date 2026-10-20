"""Simulated Stripe-shaped card checkout — no real charges or keys.

Success pattern mirrors Stripe test card 4242…4242.
Decline pattern mirrors Stripe test card 4000…0002.
"""
from __future__ import annotations

import re

# Digits-only forms of the well-known Stripe test patterns.
SUCCESS_CARD_DIGITS = "4242424242424242"
DECLINE_CARD_DIGITS = "4000000000000002"

SIMULATED_LABEL = "simulated — no real charge"


class CheckoutError(ValueError):
    """User-safe validation message for the simulated card form."""


def normalize_card_digits(card_number: str) -> str:
    """Strip spaces and dashes; keep digits only."""
    return re.sub(r"\D", "", card_number or "")


def classify_simulated_card(card_number: str) -> str:
    """Classify a card number into success, decline, or raise CheckoutError.

    Returns:
        ``"success"`` for the 4242… pattern, ``"decline"`` for 4000…0002.
    """
    digits = normalize_card_digits(card_number)
    if digits == SUCCESS_CARD_DIGITS:
        return "success"
    if digits == DECLINE_CARD_DIGITS:
        return "decline"
    raise CheckoutError(
        "Unrecognized demo card. Use 4242 4242 4242 4242 for success, or "
        "4000 0000 0000 0002 for a decline. "
        f"({SIMULATED_LABEL})"
    )
