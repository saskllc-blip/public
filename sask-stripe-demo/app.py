"""SASK LLC — SW Services: Stripe payments + webhooks demo store.

Standalone entrypoint: from this folder run ``streamlit run app.py``.
No real payments, no real Stripe keys, no monorepo package imports required.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure this product folder is importable when launched via streamlit run app.py
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    import streamlit as st
except ImportError as exc:  # pragma: no cover - launch-time guard
    raise SystemExit(
        "streamlit is required. Install with: pip install -r requirements.txt"
    ) from exc

from checkout import SIMULATED_LABEL, CheckoutError
from store import DemoStore, StoreError

DEMO_BANNER = (
    "Demo store — simulated payments only. No real charges, no real payment data."
)
BRAND = "SASK LLC — SW Services"


def _store() -> DemoStore:
    """Return the session-scoped demo store, creating it once per session."""
    if "demo_store" not in st.session_state:
        st.session_state.demo_store = DemoStore()
    return st.session_state.demo_store


def render_banner() -> None:
    """Visible safety banner required by acceptance criteria."""
    st.warning(DEMO_BANNER)


def render_explainers() -> None:
    """Short plain-English copy for a non-technical buyer."""
    with st.expander("Why this demo matters (plain English)", expanded=True):
        st.markdown(
            """
**Why webhooks exist**  
When a customer pays, your website does not get the final answer instantly.
The payment provider (here: simulated Stripe) sends a follow-up message —
a *webhook* — saying the payment succeeded, failed, or was refunded.
Your systems should update the order from that message, not from the
"Pay" button alone.

**What signature verification does**  
Every webhook can include a signature. Checking it proves the message
really came from the payment provider, not a stranger pretending to be them.

**Why idempotency matters**  
Providers sometimes send the same event twice (network retries). Without an
idempotency key, you might ship twice or refund twice. Delivering the same
event again in this console must show *duplicate — ignored*.
            """.strip()
        )


def render_storefront(store: DemoStore) -> None:
    """Fictional catalog + cart."""
    st.subheader("Storefront")
    cols = st.columns(2)
    for index, product in enumerate(store.catalog):
        col = cols[index % 2]
        with col:
            st.markdown(f"**{product.name}** — {product.price_display}")
            st.caption(product.description)
            if st.button(f"Add to cart", key=f"add_{product.id}"):
                store.add_to_cart(product.id)
                st.rerun()

    st.markdown("#### Cart")
    if not store.cart:
        st.info("Cart is empty.")
    else:
        for item in store.cart:
            st.write(
                f"{item.quantity}× {item.name} — "
                f"${item.line_total_cents / 100:.2f}"
            )
        st.write(f"**Cart total:** ${store.cart_total_cents / 100:.2f}")
        if st.button("Place order (creates pending order)"):
            try:
                order = store.place_order()
                st.session_state["active_order_id"] = order.id
                st.success(f"Order {order.id} created — status **pending**.")
                st.rerun()
            except StoreError as exc:
                st.error(str(exc))


def render_checkout(store: DemoStore) -> None:
    """Simulated Stripe-shaped card form. Does not change payment status."""
    st.subheader("Simulated checkout")
    st.caption(SIMULATED_LABEL)
    if not store.orders:
        st.info("Place an order from the storefront first.")
        return

    order_ids = [o.id for o in store.orders]
    default = st.session_state.get("active_order_id", order_ids[0])
    if default not in order_ids:
        default = order_ids[0]
    order_id = st.selectbox(
        "Order",
        order_ids,
        index=order_ids.index(default),
    )
    order = store.get_order(order_id)
    st.write(f"Status: **{order.status}** · Total: {order.total_display}")
    if order.payment_intent_id:
        st.code(
            f"payment_intent: {order.payment_intent_id}\n"
            f"checkout_outcome: {order.checkout_outcome}"
        )

    with st.form("checkout_form"):
        card = st.text_input(
            "Card number (demo)",
            value="4242 4242 4242 4242",
            help="4242… success · 4000…0002 decline — simulated, no real charge",
        )
        submitted = st.form_submit_button("Submit simulated payment")
        if submitted:
            try:
                updated = store.submit_checkout(order_id, card)
                st.session_state["active_order_id"] = order_id
                st.success(
                    "Checkout recorded. Order status is still "
                    f"**{updated.status}** — deliver a webhook to change it. "
                    f"({SIMULATED_LABEL})"
                )
            except (CheckoutError, StoreError) as exc:
                st.error(str(exc))

    st.caption(
        "Lesson: the Pay button must not mark the order paid. "
        "Only the webhook console below advances payment state."
    )


def render_orders(store: DemoStore) -> None:
    """Visible order records and status."""
    st.subheader("Orders")
    if not store.orders:
        st.info("No orders yet.")
        return
    # Prefer markdown rows — some environments break Arrow/NumPy table widgets.
    for order in store.orders:
        st.markdown(
            f"**{order.id}** · status `{order.status}` · {order.total_display}  \n"
            f"payment_intent: `{order.payment_intent_id or '—'}`  \n"
            f"checkout: {order.checkout_outcome or '—'}"
        )
        st.divider()


def render_webhook_console(store: DemoStore) -> None:
    """Buttons to deliver simulated events + event log."""
    st.subheader("Webhook console")
    if not store.orders:
        st.info("Create an order before delivering webhooks.")
        return

    order_ids = [o.id for o in store.orders]
    default = st.session_state.get("active_order_id", order_ids[0])
    if default not in order_ids:
        default = order_ids[0]
    order_id = st.selectbox(
        "Target order",
        order_ids,
        index=order_ids.index(default),
        key="webhook_order",
    )
    order = store.get_order(order_id)
    st.write(f"Current status: **{order.status}**")

    store.webhooks.fail_processing = st.toggle(
        "Fail processing (retry demo)",
        value=store.webhooks.fail_processing,
        help=(
            "When on, the next delivery is queued for retry. "
            "Turn off and deliver the same event again to succeed."
        ),
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("payment_intent.succeeded"):
            entry = store.deliver_webhook(order_id, "payment_intent.succeeded")
            st.session_state["last_webhook_msg"] = entry.detail
            st.rerun()
    with c2:
        if st.button("payment_intent.payment_failed"):
            entry = store.deliver_webhook(order_id, "payment_intent.payment_failed")
            st.session_state["last_webhook_msg"] = entry.detail
            st.rerun()
    with c3:
        if st.button("charge.refunded"):
            entry = store.deliver_webhook(order_id, "charge.refunded")
            st.session_state["last_webhook_msg"] = entry.detail
            st.rerun()
    with c4:
        if st.button("Re-deliver last (idempotency)"):
            # Reuse last event id for succeeded if present, else whatever last was.
            last = next(
                (
                    row
                    for row in reversed(store.webhooks.event_log)
                    if row.order_id == order_id
                ),
                None,
            )
            if last is None:
                st.warning("No prior event for this order — deliver one first.")
            else:
                entry = store.deliver_webhook(
                    order_id,
                    last.event_type,
                    event_id=last.event_id,
                )
                st.session_state["last_webhook_msg"] = entry.detail
                st.rerun()

    if st.button("Deliver with bad signature"):
        entry = store.deliver_webhook(
            order_id,
            "payment_intent.succeeded",
            signature_valid=False,
        )
        st.session_state["last_webhook_msg"] = entry.detail
        st.rerun()

    if "last_webhook_msg" in st.session_state:
        st.info(st.session_state["last_webhook_msg"])

    st.markdown("#### Event log")
    if not store.webhooks.event_log:
        st.caption("No webhook events yet.")
    else:
        # Plain markdown rows — no Arrow table widgets for Cloud/local demos.
        for row in reversed(store.webhooks.event_log):
            st.markdown(
                f"`{row.timestamp.isoformat()}` · **{row.event_type}** · "
                f"sig `{row.signature_status}` · result `{row.processing_result}` "
                f"(attempt {row.attempt})  \n"
                f"{row.detail} · event_id `{row.event_id}`"
            )
            st.divider()


def main() -> None:
    """Streamlit page composition."""
    st.set_page_config(
        page_title=f"{BRAND} · Stripe demo",
        page_icon=None,
        layout="wide",
    )
    st.title(BRAND)
    st.markdown("### Stripe payments + webhooks demo store")
    render_banner()
    render_explainers()

    store = _store()
    if st.sidebar.button("Reset demo"):
        store.reset()
        st.session_state.pop("active_order_id", None)
        st.session_state.pop("last_webhook_msg", None)
        st.rerun()

    tab_store, tab_pay, tab_hook, tab_orders = st.tabs(
        ["Storefront", "Checkout", "Webhook console", "Orders"]
    )
    with tab_store:
        render_storefront(store)
    with tab_pay:
        render_checkout(store)
    with tab_hook:
        render_webhook_console(store)
    with tab_orders:
        render_orders(store)

    st.caption(
        "© 2026 SASK LLC — SW Services · Portfolio demonstration · "
        "simulation-only · free-tier friendly"
    )


if __name__ == "__main__":
    main()
