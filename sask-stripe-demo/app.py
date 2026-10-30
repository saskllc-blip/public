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

import history
from checkout import SIMULATED_LABEL, CheckoutError
from store import DemoStore, StoreError

DEMO_BANNER = (
    "Demo store — simulated payments only. No real charges, no real payment data."
)
BRAND = "SASK LLC — SW Services"
HISTORY_NOTE = (
    "Synthetic history — fictional customers on example.com / example.org, "
    "fictional products, simulated Stripe-shaped events. No real people, "
    "businesses, or payments."
)
PAGE_SIZE = 25


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


def _history() -> history.Dataset:
    """Read-only synthetic 90-day dataset (loaded once per process)."""
    return history.load_dataset()


def _page_controls(total: int, key: str) -> int:
    """Page picker for long lists; returns the 1-based page number."""
    pages = max(1, -(-total // PAGE_SIZE))
    page = st.number_input(
        f"Page (of {pages})", min_value=1, max_value=pages, value=1, step=1, key=key
    )
    st.caption(f"{total} matching rows · {PAGE_SIZE} per page")
    return int(page)


def _event_row(event: dict, customers: dict[str, dict]) -> str:
    customer = customers.get(event["customer_id"], {})
    return (
        f"`{event['created_at']}` · **{event['type']}** · order `{event['order_id']}` · "
        f"{customer.get('name', '—')} · event_id `{event['id']}`"
    )


def render_order_story(ds: history.Dataset, order_id: str) -> None:
    """One order's full lifecycle: attempts, refund, dispute, webhook events."""
    story = history.order_story(ds, order_id)
    order, customer = story["order"], story["customer"]
    st.markdown(
        f"**{order['id']}** · status `{order['status']}` · "
        f"{history.usd(order['total_cents'])} · channel `{order['channel']}`  \n"
        f"customer: {customer['name']} <{customer['email']}> · "
        f"payment_intent `{order['payment_intent_id']}`"
    )
    st.markdown(
        "  \n".join(
            f"{i['quantity']}× {i['name']} — {history.usd(i['unit_price_cents'] * i['quantity'])}"
            for i in order["items"]
        )
    )
    for attempt in story["attempts"]:
        reason = attempt["decline_code"] or attempt["failure_code"] or "—"
        st.markdown(
            f"attempt {attempt['attempt_number']} · `{attempt['created_at']}` · "
            f"**{attempt['status']}** · {attempt['card_brand']} ••{attempt['card_last4']} · "
            f"reason `{reason}` · charge `{attempt['id']}`"
        )
    for refund in story["refunds"]:
        st.markdown(
            f"refund `{refund['id']}` · {history.usd(refund['amount_cents'])} · "
            f"reason `{refund['reason']}` · `{refund['created_at']}`"
        )
    for dispute in story["disputes"]:
        st.markdown(
            f"dispute `{dispute['id']}` · {history.usd(dispute['amount_cents'])} · "
            f"reason `{dispute['reason']}` · status `{dispute['status']}` · "
            f"opened `{dispute['created_at']}` · closed `{dispute['closed_at'] or 'open'}`"
        )
    st.markdown("**Webhook timeline**")
    for event in story["events"]:
        with st.expander(f"{event['created_at']} · {event['type']}"):
            st.json(event["payload"], expanded=False)


def render_dashboard() -> None:
    """Gross / refunds / disputes / net and charts, computed from the dataset."""
    ds = _history()
    manifest = ds.manifest
    st.subheader("Dashboard — last 90 days")
    st.caption(
        f"{HISTORY_NOTE} Window {manifest['window_start'][:10]} → "
        f"{manifest['anchor'][:10]} · seed {manifest['seed']}."
    )
    m = history.summary_metrics(ds)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross volume", history.usd(m["gross_cents"]))
    c2.metric("Refunds", history.usd(m["refunded_cents"]))
    c3.metric("Disputes", history.usd(m["disputed_cents"]))
    c4.metric("Net volume", history.usd(m["net_cents"]))
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Orders", m["orders"])
    c6.metric("Payment attempts", m["payment_attempts"])
    c7.metric("Success rate", f"{m['success_rate']:.1%}")
    c8.metric("Webhook events", m["webhook_events"])
    st.caption(
        f"{m['refunds']} refunded orders · {m['disputes']} disputes "
        f"({history.usd(m['dispute_withdrawn_cents'])} still withdrawn). "
        "Net = gross − refunds − disputed funds still withdrawn (lost or open); "
        "won disputes are reinstated."
    )

    import pandas as pd  # streamlit dependency; only needed for charts

    daily = pd.DataFrame(history.daily_series(ds)).set_index("date")
    st.markdown("#### Daily gross volume (USD)")
    st.bar_chart((daily["gross_cents"] / 100).rename("gross USD"))
    st.markdown("#### Payment attempts per day")
    st.bar_chart(daily[["succeeded", "failed"]])
    st.markdown("#### Orders by weekday")
    st.bar_chart(pd.DataFrame(history.weekday_profile(ds)).set_index("weekday"))

    left, right = st.columns(2)
    with left:
        st.markdown("#### Products (paid orders)")
        for row in history.product_revenue(ds):
            st.markdown(
                f"**{row['name']}** · {row['units']} units · "
                f"{history.usd(row['gross_cents'])}"
            )
    with right:
        st.markdown("#### Decline reasons")
        for reason, count in history.failure_breakdown(ds):
            st.markdown(f"`{reason}` · {count} attempts")


def render_order_history() -> None:
    """Searchable, paginated synthetic order history with drill-down."""
    ds = _history()
    st.subheader("Order history — last 90 days (synthetic)")
    st.caption(HISTORY_NOTE)
    statuses = sorted({o["status"] for o in ds.orders})
    picked = st.multiselect("Status", statuses, default=[], key="hist_order_status")
    query = st.text_input("Search order / customer / email", key="hist_order_q")
    rows = history.filter_orders(ds, statuses=picked or None, query=query)
    page = _page_controls(len(rows), "hist_order_page")
    customers = ds.customers_by_id
    for order in history.paginate(rows, page, PAGE_SIZE):
        customer = customers[order["customer_id"]]
        flags = []
        if order["refund_id"]:
            flags.append("refunded")
        if order["dispute_id"]:
            flags.append("disputed")
        st.markdown(
            f"**{order['id']}** · `{order['created_at']}` · status `{order['status']}` · "
            f"{history.usd(order['total_cents'])} · {customer['name']}"
            + (f" · {', '.join(flags)}" if flags else "")
        )
    if rows:
        order_id = st.selectbox(
            "Open order", [o["id"] for o in rows], key="hist_order_pick"
        )
        render_order_story(ds, order_id)
    else:
        st.info("No orders match.")


def render_event_history() -> None:
    """Filter / search the generated webhook events (read-only history)."""
    ds = _history()
    st.markdown("#### Event history — last 90 days (synthetic)")
    st.caption(
        "Read-only history generated by data/generate_data.py. The live "
        "console above only acts on orders created in this session."
    )
    types = st.multiselect(
        "Event types", list(history.EVENT_TYPES), default=[], key="hist_evt_types"
    )
    query = st.text_input(
        "Search event id / order / payment_intent / charge / customer / email",
        key="hist_evt_q",
    )
    rows = history.filter_events(ds, types=types or None, query=query)
    page = _page_controls(len(rows), "hist_evt_page")
    customers = ds.customers_by_id
    for event in history.paginate(rows, page, PAGE_SIZE):
        st.markdown(_event_row(event, customers))
        with st.expander("payload"):
            st.json(event["payload"], expanded=False)
    if not rows:
        st.info("No events match.")


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

    tab_store, tab_pay, tab_hook, tab_orders, tab_dash = st.tabs(
        ["Storefront", "Checkout", "Webhook console", "Orders", "Dashboard (90 days)"]
    )
    with tab_store:
        render_storefront(store)
    with tab_pay:
        render_checkout(store)
    with tab_hook:
        render_webhook_console(store)
        st.divider()
        render_event_history()
    with tab_orders:
        render_orders(store)
        st.divider()
        render_order_history()
    with tab_dash:
        render_dashboard()

    st.caption(
        "© 2026 SASK LLC — SW Services · Portfolio demonstration · "
        "simulation-only · free-tier friendly"
    )


if __name__ == "__main__":
    main()
