"""Session-scoped demo store: cart, orders, checkout, and webhook console.

Checkout never advances order payment status — only WebhookProcessor does.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

try:
    from .catalog import CATALOG, get_product
    from .checkout import SIMULATED_LABEL, CheckoutError, classify_simulated_card
    from .models import CartItem, EventType, Order, Product, WebhookEventLog
    from .webhooks import WebhookProcessor
except ImportError:
    from catalog import CATALOG, get_product
    from checkout import SIMULATED_LABEL, CheckoutError, classify_simulated_card
    from models import CartItem, EventType, Order, Product, WebhookEventLog
    from webhooks import WebhookProcessor


class StoreError(ValueError):
    """User-safe storefront validation message."""


class DemoStore:
    """In-memory storefront + webhook lab for the portfolio demo."""

    def __init__(self) -> None:
        self.catalog: tuple[Product, ...] = CATALOG
        self.cart: list[CartItem] = []
        self.orders: list[Order] = []
        self.webhooks = WebhookProcessor()
        # Last event_id per (order_id, event_type) so "deliver again" demos
        # idempotency with a stable key.
        self._last_event_ids: dict[tuple[str, str], str] = {}

    # --- cart ---------------------------------------------------------------

    def add_to_cart(self, product_id: str, quantity: int = 1) -> CartItem:
        """Add a catalog product to the cart (or bump quantity)."""
        if quantity < 1:
            raise StoreError("Quantity must be at least 1.")
        product = get_product(product_id)
        if product is None:
            raise StoreError("Unknown product.")
        for item in self.cart:
            if item.product_id == product_id:
                item.quantity += quantity
                return item
        item = CartItem(
            product_id=product.id,
            name=product.name,
            unit_price_cents=product.price_cents,
            quantity=quantity,
        )
        self.cart.append(item)
        return item

    def clear_cart(self) -> None:
        """Empty the cart."""
        self.cart.clear()

    @property
    def cart_total_cents(self) -> int:
        """Sum of cart line totals."""
        return sum(item.line_total_cents for item in self.cart)

    # --- orders / checkout --------------------------------------------------

    def place_order(self) -> Order:
        """Create a pending order from the cart and clear the cart."""
        if not self.cart:
            raise StoreError("Cart is empty — add a product first.")
        order = Order(
            id=f"ord_{uuid4().hex[:10]}",
            items=deepcopy(self.cart),
            status="pending",
        )
        self.orders.insert(0, order)
        self.clear_cart()
        return order

    def get_order(self, order_id: str) -> Order:
        """Return an order by id or raise StoreError."""
        for order in self.orders:
            if order.id == order_id:
                return order
        raise StoreError("Order not found.")

    def submit_checkout(self, order_id: str, card_number: str) -> Order:
        """Simulate Stripe checkout for an order.

        Records a PaymentIntent id and checkout outcome, but does **not**
        change ``order.status``. Status changes only via webhook delivery.
        """
        order = self.get_order(order_id)
        if order.status != "pending":
            raise StoreError(
                f"Order is already {order.status}; start a new order to checkout again."
            )
        outcome = classify_simulated_card(card_number)
        order.payment_intent_id = f"pi_{uuid4().hex[:14]}"
        if outcome == "success":
            order.checkout_outcome = (
                f"card_accepted_simulated ({SIMULATED_LABEL}) — "
                "waiting for payment_intent.succeeded webhook"
            )
        else:
            order.checkout_outcome = (
                f"card_declined_simulated ({SIMULATED_LABEL}) — "
                "deliver payment_intent.payment_failed to update status"
            )
        order.updated_at = datetime.now(timezone.utc)
        return order

    # --- webhooks -----------------------------------------------------------

    def deliver_webhook(
        self,
        order_id: str,
        event_type: EventType,
        *,
        reuse_last_event_id: bool = False,
        signature_valid: bool = True,
        event_id: str | None = None,
    ) -> WebhookEventLog:
        """Deliver a simulated webhook to an order and log the result."""
        order = self.get_order(order_id)
        key = (order_id, event_type)
        if event_id is None and reuse_last_event_id and key in self._last_event_ids:
            event_id = self._last_event_ids[key]
        entry = self.webhooks.deliver(
            order,
            event_type,
            event_id=event_id,
            signature_valid=signature_valid,
        )
        self._last_event_ids[key] = entry.event_id
        return entry

    def reset(self) -> None:
        """Reset cart, orders, and webhook console (demo reset button)."""
        self.cart.clear()
        self.orders.clear()
        self.webhooks = WebhookProcessor()
        self._last_event_ids.clear()


# Re-export for callers that only import store.
__all__ = [
    "CATALOG",
    "CheckoutError",
    "DemoStore",
    "SIMULATED_LABEL",
    "StoreError",
]
