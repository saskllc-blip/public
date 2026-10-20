"""Simulated Stripe webhook delivery: signatures, idempotency, and retries.

Payment state for orders is advanced only through this module — never from
the checkout button. That is the integration lesson the demo teaches.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

try:
    from .models import EventType, Order, OrderStatus, WebhookEventLog
except ImportError:
    from models import EventType, Order, OrderStatus, WebhookEventLog


# Legal status transitions driven by simulated Stripe events.
_TRANSITIONS: dict[EventType, dict[OrderStatus, OrderStatus]] = {
    "payment_intent.succeeded": {
        "pending": "paid",
        # Demo auto-fulfills after paid when the same event is re-applied
        # only via the paid→fulfilled step inside the processor below.
    },
    "payment_intent.payment_failed": {"pending": "failed"},
    "charge.refunded": {"paid": "refunded", "fulfilled": "refunded"},
}


class WebhookProcessor:
    """In-memory webhook console with idempotency and retry simulation."""

    def __init__(self) -> None:
        self.event_log: list[WebhookEventLog] = []
        # idempotency_key → first successful processing detail
        self._processed_keys: set[str] = set()
        # Keys that failed and are waiting for a retry delivery
        self._retry_queue: set[str] = set()
        # When True, the next process attempt fails and queues for retry.
        self.fail_processing: bool = False

    def deliver(
        self,
        order: Order,
        event_type: EventType,
        *,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        signature_valid: bool = True,
        now: datetime | None = None,
        on_status_change: Callable[[Order, OrderStatus], None] | None = None,
    ) -> WebhookEventLog:
        """Deliver one simulated webhook event against an order.

        Args:
            order: Mutable order record (status may change).
            event_type: Stripe-shaped event name.
            event_id: Stable event id; reused to demonstrate duplicates.
            idempotency_key: Defaults to event_id (Stripe-style).
            signature_valid: Simulated Stripe-Signature check result.
            now: Optional clock for tests.
            on_status_change: Optional callback after a real status change.
        """
        ts = now or datetime.now(timezone.utc)
        eid = event_id or f"evt_{uuid4().hex[:16]}"
        key = idempotency_key or eid
        attempt = 1 + sum(1 for row in self.event_log if row.idempotency_key == key)

        if not signature_valid:
            entry = WebhookEventLog(
                timestamp=ts,
                event_type=event_type,
                event_id=eid,
                idempotency_key=key,
                order_id=order.id,
                signature_status="invalid",
                processing_result="rejected_signature",
                detail="Signature verification failed — event not processed.",
                attempt=attempt,
            )
            self.event_log.append(entry)
            return entry

        if key in self._processed_keys:
            entry = WebhookEventLog(
                timestamp=ts,
                event_type=event_type,
                event_id=eid,
                idempotency_key=key,
                order_id=order.id,
                signature_status="verified",
                processing_result="duplicate",
                detail=(
                    f"duplicate — ignored, idempotency key {key}"
                ),
                attempt=attempt,
            )
            self.event_log.append(entry)
            return entry

        if self.fail_processing:
            self._retry_queue.add(key)
            entry = WebhookEventLog(
                timestamp=ts,
                event_type=event_type,
                event_id=eid,
                idempotency_key=key,
                order_id=order.id,
                signature_status="verified",
                processing_result="queued_for_retry",
                detail=(
                    "Processing failed (demo toggle) — event queued for retry. "
                    f"idempotency key {key}"
                ),
                attempt=attempt,
            )
            self.event_log.append(entry)
            return entry

        new_status = self._apply_transition(order, event_type)
        if new_status is None:
            entry = WebhookEventLog(
                timestamp=ts,
                event_type=event_type,
                event_id=eid,
                idempotency_key=key,
                order_id=order.id,
                signature_status="verified",
                processing_result="ignored_invalid_transition",
                detail=(
                    f"No transition for event {event_type} from status "
                    f"{order.status}."
                ),
                attempt=attempt,
            )
            self.event_log.append(entry)
            # Still mark processed so a duplicate of a no-op is idempotent.
            self._processed_keys.add(key)
            self._retry_queue.discard(key)
            return entry

        previous = order.status
        order.status = new_status
        order.updated_at = ts
        # Auto-fulfill after paid on successful payment_intent.
        if event_type == "payment_intent.succeeded" and order.status == "paid":
            order.status = "fulfilled"
            order.updated_at = ts
        if on_status_change is not None:
            on_status_change(order, previous)

        self._processed_keys.add(key)
        self._retry_queue.discard(key)
        entry = WebhookEventLog(
            timestamp=ts,
            event_type=event_type,
            event_id=eid,
            idempotency_key=key,
            order_id=order.id,
            signature_status="verified",
            processing_result="processed",
            detail=(
                f"Order {order.id}: {previous} → {order.status} "
                f"(event {event_type})"
            ),
            attempt=attempt,
        )
        self.event_log.append(entry)
        return entry

    def _apply_transition(
        self, order: Order, event_type: EventType
    ) -> OrderStatus | None:
        """Return the next status, or None if the transition is invalid."""
        mapping = _TRANSITIONS.get(event_type, {})
        return mapping.get(order.status)

    @property
    def retry_queue_keys(self) -> frozenset[str]:
        """Idempotency keys currently waiting for a successful retry."""
        return frozenset(self._retry_queue)
