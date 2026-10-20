"""Domain models for the SASK LLC simulated Stripe demo store.

All payment data is fictional. No real Stripe API calls or keys are used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

# Order lifecycle visible in the storefront and webhook console.
OrderStatus = Literal["pending", "paid", "fulfilled", "failed", "refunded"]

# Simulated Stripe-shaped event types the webhook console can deliver.
EventType = Literal[
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "charge.refunded",
]

SignatureStatus = Literal["verified", "invalid", "skipped"]
ProcessingResult = Literal[
    "processed",
    "duplicate",
    "queued_for_retry",
    "rejected_signature",
    "ignored_invalid_transition",
]


@dataclass(frozen=True)
class Product:
    """A fictional catalog item with a display price in USD cents."""

    id: str
    name: str
    description: str
    price_cents: int

    @property
    def price_display(self) -> str:
        """Format cents as a USD string for the UI."""
        return f"${self.price_cents / 100:.2f}"


@dataclass
class CartItem:
    """One line in the session cart."""

    product_id: str
    name: str
    unit_price_cents: int
    quantity: int = 1

    @property
    def line_total_cents(self) -> int:
        """Quantity × unit price in cents."""
        return self.unit_price_cents * self.quantity


@dataclass
class Order:
    """An order record whose status changes only via the webhook processor."""

    id: str
    items: list[CartItem]
    status: OrderStatus = "pending"
    # Simulated PaymentIntent id created at checkout (Stripe shape, not real).
    payment_intent_id: str | None = None
    # Card outcome recorded at checkout; never advances order.status alone.
    checkout_outcome: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_cents(self) -> int:
        """Sum of line totals."""
        return sum(item.line_total_cents for item in self.items)

    @property
    def total_display(self) -> str:
        """Format order total as USD."""
        return f"${self.total_cents / 100:.2f}"


@dataclass
class WebhookEventLog:
    """One row in the webhook event console log."""

    timestamp: datetime
    event_type: EventType
    event_id: str
    idempotency_key: str
    order_id: str
    signature_status: SignatureStatus
    processing_result: ProcessingResult
    detail: str
    attempt: int = 1
