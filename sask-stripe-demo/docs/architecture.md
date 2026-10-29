# Stripe demo architecture

This document describes the system as it exists in this folder. Where an older README note disagrees with a module, **the code wins**.

Draw IO source: [`architecture.drawio`](architecture.drawio). Export: [`images/architecture.png`](images/architecture.png).

## Purpose and scope

A self-contained Streamlit store that makes payment-integration work *visible*: a fictional catalog, a simulated Stripe-shaped checkout, and a webhook console for signatures, retries, and idempotency.

The lesson the demo teaches: **the Pay button must not mark the order paid**. Only `WebhookProcessor.deliver()` advances `order.status`.

Scope of this folder:

- Five tabs on one page (`app.py` render functions): Storefront, Checkout, Webhook console, Orders, Dashboard (90 days).
- In-process simulation of Stripe-shaped objects (`pi_*`, `ch_*`, `evt_*`, event type names).
- Session-scoped live state, plus a **read-only** synthetic 90-day history loaded from `data/*.json`.

Out of scope: the `stripe` Python package, HTTP to Stripe, runtime disk writes, env vars, TEST-mode keys, webhooks from the public internet.

Live hosted demo: https://public-jqoiup3zm9dmmth2mranix.streamlit.app/ (simulation-only; no secrets).

## Component inventory

| Module | Responsibility |
|--------|----------------|
| `app.py` | Entry point. Page chrome, safety banner, explainers, five tabs (incl. Dashboard), sidebar **Reset demo**. **No business rules** — buttons call `DemoStore` methods. |
| `store.py` `DemoStore` | Session storefront: catalog reference, cart, orders, `place_order`, `submit_checkout`, `deliver_webhook` facade, `reset`. Owns `_last_event_ids` so re-deliver can reuse a stable event id. |
| `catalog.py` | Loads the twelve fictional products ($15–$499) from `data/products.json` into frozen `Product`s; `get_product`. The original four SKUs keep their ids and prices. |
| `history.py` | Read-only loader (`load_dataset`, cached per process) and pure functions over the synthetic history: `summary_metrics`, `daily_series`, `weekday_profile`, `product_revenue`, `failure_breakdown`, `filter_events`, `filter_orders`, `paginate`, `order_story`. |
| `data/generate_data.py` | Offline, deterministic generator (seed `20261025`, anchor `2026-10-25T23:59:59Z`). Writes `products`, `customers`, `orders`, `payment_attempts`, `refunds`, `disputes`, `webhook_events` JSON plus `manifest.json` (counts + sha256). Not imported by the app. |
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

## Synthetic 90-day history (read-only)

`history.load_dataset()` reads `data/*.json` once per process. The Dashboard tab shows gross / refunds / disputes / net volume, daily gross and attempt charts, a weekday profile, product revenue, and decline reasons — all computed from rows. Net = gross − refunds − disputed funds still withdrawn (lost or open); won disputes are reinstated. The Orders tab adds a searchable, paginated order history with a per-order lifecycle drill-down; the Webhook console tab adds an event-history browser (type filter, free-text search over event / order / PaymentIntent / charge / customer / email, 25 rows per page, payload JSON per event). History is never mutated; the live console only acts on session orders.

| File | Rows | Key fields |
|------|------|------------|
| `products.json` | 12 | `id`, `name`, `price_cents` |
| `customers.json` | 120 | `cus_…`, name, `@example.com/.org` email, `created_at` |
| `orders.json` | 300 | `ord_…`, `customer_id`, `items` (CartItem shape), `total_cents`, `status`, `payment_intent_id`, `channel`, `paid_at`, `refund_id`, `dispute_id` |
| `payment_attempts.json` | 440 | `ch_…`, `order_id`, `attempt_number`, `amount_cents`, `status`, `failure_code`, `decline_code`, card brand/last4 |
| `refunds.json` / `disputes.json` | 15 / 3 | `re_…` / `dp_…`, `charge_id`, amount, reason, status, timestamps |
| `webhook_events.json` | 1,202 | `evt_…`, `type`, `created_at`, parent ids, Stripe-shaped `payload` |

## Data model and where live state lives

Live session state is `st.session_state["demo_store"]` (a `DemoStore` instance):

| Field | Contents |
|-------|----------|
| `catalog` | Tuple of `Product` (module-level `CATALOG`) |
| `cart` | `list[CartItem]` |
| `orders` | `list[Order]` (`pending` / `paid` / `fulfilled` / `failed` / `refunded`) |
| `webhooks.event_log` | `list[WebhookEventLog]` |
| `webhooks._processed_keys` | Idempotency keys already successfully processed |
| `webhooks._retry_queue` | Keys waiting for a retry after the fail toggle |
| `_last_event_ids` | `(order_id, event_type) → event_id` |

**Reset demo** / a new browser session wipes the session store. The synthetic history is read-only and unaffected. Nothing is written to disk at runtime.

## External services and dependencies

- Streamlit `>=1.28,<2` (and pandas, a Streamlit dependency, for the dashboard charts) and the Python standard library.
- **No** `stripe` package, **no** env vars read by the app, **no** HTTP client.

Hosted on Streamlit Cloud for the public demo. Local run: `streamlit run app.py` from this folder.

## Key design decisions and constraints

- **Checkout is deliberately incomplete.** Recording a PaymentIntent is not fulfillment. That is the integration lesson.
- **Simulation-only is the only mode.** README notes about future TEST-mode keys are design-only; the public Cloud deploy stays simulation-only.
- **In-process deliver, not HTTP.** UI buttons call `WebhookProcessor.deliver()` on the same `Order` object so a visitor can see signature / idempotency / retry without a tunnel or Stripe CLI.
- **Synthetic cards and SKUs.** `4242…` / `4000…0002` are Stripe *test-card shapes*, not charges.
- **No Arrow tables.** Orders and the event log render as markdown rows (paginated for the 90-day history). The three dashboard bar charts use Streamlit's built-in `st.bar_chart`.

## How to extend it

1. **New catalog item:** add it to `PRODUCTS` in `data/generate_data.py` and rerun the generator (`catalog.py` reads `data/products.json`).
2. **New event type:** add the name to `EventType` in `models.py` and a row in `_TRANSITIONS`; add a button in `render_webhook_console`.
3. **Do not** add a live Stripe key or the `stripe` SDK in this public folder. Keep simulation-only.
4. Tests live in `tests/`. Run from this folder: `python3 -m pytest tests -q`.
