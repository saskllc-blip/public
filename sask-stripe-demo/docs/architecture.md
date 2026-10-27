# Stripe demo architecture

This document describes the system as it exists in this folder. Where an older README note disagrees with a module, **the code wins**.

Draw IO source: [`architecture.drawio`](architecture.drawio). Export: [`images/architecture.png`](images/architecture.png).

## Purpose and scope

A self-contained Streamlit store that makes payment-integration work *visible*: a fictional catalog, a simulated Stripe-shaped checkout, and a webhook console for signatures, retries, and idempotency.

The lesson the demo teaches: **the Pay button must not mark the order paid**. Only `WebhookProcessor.deliver()` advances `order.status`.

Scope of this folder:

- Four tabs on one page (`app.py` render functions).
- In-process simulation of Stripe-shaped objects (`pi_*`, `evt_*`, event type names).
- Session-scoped state only.

Out of scope: the `stripe` Python package, HTTP to Stripe, disk files, env vars, TEST-mode keys, webhooks from the public internet.

Live hosted demo: https://public-jqoiup3zm9dmmth2mranix.streamlit.app/ (simulation-only; no secrets).

## Component inventory

| Module | Responsibility |
|--------|----------------|
| `app.py` | Entry point. Page chrome, safety banner, explainers, four tabs, sidebar **Reset demo**. **No business rules** — buttons call `DemoStore` methods. |
| `store.py` `DemoStore` | Session storefront: catalog reference, cart, orders, `place_order`, `submit_checkout`, `deliver_webhook` facade, `reset`. Owns `_last_event_ids` so re-deliver can reuse a stable event id. |
| `catalog.py` | Four frozen fictional products (API Integration Audit $149, Webhook Starter Kit $79, Idempotency Clinic $99, Retry Playbook Pack $59) and `get_product`. |
| `checkout.py` | `normalize_card_digits`, `classify_simulated_card`. `4242424242424242` → `"success"`; `4000000000000002` → `"decline"`; anything else → `CheckoutError`. |
| `webhooks.py` `WebhookProcessor` | Signature boolean, idempotency set, retry queue, `fail_processing` toggle, legal status transitions, event log. |
| `models.py` | `Product`, `CartItem`, `Order`, `WebhookEventLog`. Literals for `OrderStatus` and `EventType`. |

There is **no** `SASK_STRIPE_MODE` and no live Stripe path in this folder.

## Data-flow walkthroughs

### Place an order (still pending)

1. Storefront **Add to cart** → `DemoStore.add_to_cart` (bumps quantity if the SKU is already in the cart).
2. **Place order** → `place_order()`: empty cart raises `StoreError`; else `Order(id=ord_…, status="pending")` is prepended to `orders` and the cart is cleared.
3. `st.session_state["active_order_id"]` is set so Checkout / Webhook tabs default to that order.

### Submit simulated payment (status unchanged)

1. Checkout tab form → `submit_checkout(order_id, card)`.
2. Only `pending` orders are accepted.
3. `classify_simulated_card` records `payment_intent_id = pi_…` and a `checkout_outcome` string.
4. **`order.status` stays `pending`.** The UI success message says so.

### Webhook advances status

`store.deliver_webhook` → `WebhookProcessor.deliver`:

1. Invalid signature → log `rejected_signature`; no status change.
2. Known idempotency key → log `duplicate`; no status change.
3. `fail_processing` toggle on → log `queued_for_retry`; key enters `_retry_queue`.
4. Else apply `_TRANSITIONS`:
   - `payment_intent.succeeded`: `pending` → `paid`, then auto-`fulfilled`.
   - `payment_intent.payment_failed`: `pending` → `failed`.
   - `charge.refunded`: `paid` or `fulfilled` → `refunded`.
5. Illegal pair → `ignored_invalid_transition` (still marked processed so a duplicate is idempotent).

**Re-deliver last** reuses the previous `event_id` for that order so the second click shows `duplicate — ignored`.

## Data model and where state lives

All of it is `st.session_state["demo_store"]` (a `DemoStore` instance):

| Field | Contents |
|-------|----------|
| `catalog` | Tuple of `Product` (module-level `CATALOG`) |
| `cart` | `list[CartItem]` |
| `orders` | `list[Order]` (`pending` / `paid` / `fulfilled` / `failed` / `refunded`) |
| `webhooks.event_log` | `list[WebhookEventLog]` |
| `webhooks._processed_keys` | Idempotency keys already successfully processed |
| `webhooks._retry_queue` | Keys waiting for a retry after the fail toggle |
| `_last_event_ids` | `(order_id, event_type) → event_id` |

**Reset demo** / a new browser session wipes everything. Nothing is written to disk.

## External services and dependencies

- Streamlit `>=1.28,<2` and the Python standard library.
- **No** `stripe` package, **no** env vars read by the app, **no** HTTP client.

Hosted on Streamlit Cloud for the public demo. Local run: `streamlit run app.py` from this folder.

## Key design decisions and constraints

- **Checkout is deliberately incomplete.** Recording a PaymentIntent is not fulfillment. That is the integration lesson.
- **Simulation-only is the only mode.** README notes about future TEST-mode keys are design-only; the public Cloud deploy stays simulation-only.
- **In-process deliver, not HTTP.** UI buttons call `WebhookProcessor.deliver()` on the same `Order` object so a visitor can see signature / idempotency / retry without a tunnel or Stripe CLI.
- **Synthetic cards and SKUs.** `4242…` / `4000…0002` are Stripe *test-card shapes*, not charges.
- **No Arrow tables.** Orders and the event log render as markdown rows so Cloud/local demos do not depend on PyArrow.

## How to extend it

1. **New catalog item:** append a `Product` to `CATALOG` in `catalog.py`.
2. **New event type:** add the name to `EventType` in `models.py` and a row in `_TRANSITIONS`; add a button in `render_webhook_console`.
3. **Do not** add a live Stripe key or the `stripe` SDK in this public folder. Keep simulation-only.
4. There is **no in-tree test suite** here. Sibling coverage (if you have it) lives in KK_AI_PLATFORM `tests/test_sask_stripe_demo.py` and is not vendored.

Run from this folder: `python3 -m pytest . -q` (expect 0 collected unless you add tests).
