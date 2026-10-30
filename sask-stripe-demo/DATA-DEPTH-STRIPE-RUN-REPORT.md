# Data-depth run report — Stripe demo (~90 days of payment history)

- Date: 2026-10-29 (UTC)
- Repo / app: `saskllc-blip/public` → `sask-stripe-demo/`
- Branch: `claude/happy-keller-xrri4n` (assigned by the cloud session), cut from `main` at `0553e3f` (PR #3 merge)
- Stacks on public `main` only. Does **not** touch the unmerged local showcase branches.
- Scope source: `demo-data-depth-scope-2026-10-25.md` §2 (the brief; the file itself is not in this repo)

## Provenance

100% synthetic. Invented first/last-name combinations, emails only on `example.com` / `example.org`, fictional SW-services products, Stripe *test-card shapes* (last4 such as 4242 / 0002 / 9995), random-hex Stripe-shaped ids from a fixed seed, `livemode: false` on every event. No real people, businesses, cards, or scraped data. The existing disclaimers ("Demo store — simulated payments only…") are unchanged and still true. A matching note is on every new history view.

## Step 0 — what was there before (main @ `0553e3f`)

- Entry point `app.py`: four tabs (Storefront, Checkout, Webhook console, Orders) plus sidebar Reset. State is a session-scoped `DemoStore`.
- Data layer: **no data files, no persisted dataset, no loader.** The catalog was hardcoded in `catalog.py`. Everything else was created live in the session.
- Metrics, charts, dashboard: **none existed.** No displayed money totals at all, so nothing was hardcoded. The Webhook console only showed the live session's event log, with no filters or search.
- Tests: **no in-tree suite.** `pytest . --collect-only` → `no tests collected` (this matches the diagram run).

| Entity | Count before |
|---|---|
| Products | 4 (hardcoded) |
| Customers | 0 (no customer concept) |
| Orders | 0 at start (session only) |
| Payment attempts | 0 (only one `checkout_outcome` per session order) |
| Webhook events | 0 at start (session log only) |

## Dataset after

| File | Rows | Band in tests |
|---|---|---|
| `products.json` | 12 ($15.00 – $499.00) | 10–14 |
| `customers.json` | 120 | 108–132 |
| `orders.json` | 300 (254 fulfilled, 15 refunded, 31 failed) | 270–330 |
| `payment_attempts.json` | 440 (269 succeeded, 171 failed) | 405–495 |
| `refunds.json` | 15 (5.0% of orders, full refunds) | 4–6% |
| `disputes.json` | 3 (1.0%: won / lost / needs_response) | 0.5–1.5% |
| `webhook_events.json` | 1,202 | 1,080–1,320 |

Event mix: `payment_intent.created` 300, `charge.succeeded` 269, `payment_intent.succeeded` 269, `checkout.session.completed` 173, `payment_intent.payment_failed` 171, `charge.refunded` 15, `charge.dispute.created` 3, `charge.dispute.closed` 2.

Money (computed from rows, shown on the Dashboard):
- Gross: $47,627.00
- Refunds: $3,073.00
- Disputes opened: $116.00 ($87.00 still withdrawn)
- Net: $44,467.00
- Payment success rate: 61.1%

Decline reasons: `card_declined` 113 (`generic_decline` and `insufficient_funds`), `expired_card` 20, `incorrect_cvc` 20, `processing_error` 18. Failed attempts are retried to success on many orders.

## Generator design

- `data/generate_data.py`: stdlib only, a single `random.Random(SEED)`, no set-iteration or wall-clock dependence.
  - **Seed `20261025`**
  - **Anchor `2026-10-25T23:59:59Z`**
  - **Window `2026-07-28` → `2026-10-25` (90 days)**
- Volume curve: exactly 300 orders are allocated across days. Each day's weight is `(1 + 0.6·day/89) × (0.55 on weekends) × noise(0.85–1.15)`, with largest-remainder rounding. Order times skew toward business hours. Customer frequency is heavy-tailed (Pareto weights), so there are repeat buyers.
- Amounts: line items use catalog prices. `order.total = Σ unit_price × qty`, and every attempt amount equals its order total.
- Lifecycle per order:
  1. `payment_intent.created`
  2. Attempts: the first fails with p=0.42 and retries fail with p=0.35. After a failure, a retry follows with p=0.85, up to 4 attempts, 2 min–8 h apart. Each failure emits `payment_intent.payment_failed`.
  3. On success: `charge.succeeded` → `payment_intent.succeeded` → `checkout.session.completed` (checkout channel, ~65%), 1 s apart.
  4. Refunds land 1 h–21 days after payment (`charge.refunded`).
  5. Disputes open 3–20 days after payment and close 6–18 days later, with `.created` and `.closed` events. The open one has no close event.
  6. Nothing goes past the anchor.
- Payloads follow the real event shapes (`event` envelope with `api_version`, `created` unix, `data.object` = payment_intent / charge / checkout.session / dispute, with `metadata.order_id`).
- Output: one JSON record per line (sorted keys, diff-friendly), plus `manifest.json` with counts, seed, anchor, per-file sha256 and the dataset sha256.
- **Dataset sha256: `f81ada96291f4e19fd8dc0617bf07c3fe71eae3d9de1e13d6022c4a15adfda18`**
- Re-run: `python3 data/generate_data.py`. It is byte-identical and idempotent; a test checks this against the committed files.

## Schema extensions (documented, minimal)

- There was no persisted schema before. The new collections reuse existing shapes where they exist: order `items` use the `CartItem` fields, order `status` stays within the existing `OrderStatus` literal (`fulfilled` / `failed` / `refunded`), and event type names match the console's.
- Fields added to orders: `customer_id`, `total_cents`, `currency`, `channel`, `paid_at`, `refund_id`, `dispute_id`.
- New collections: customers, payment_attempts, refunds, disputes, and webhook events with `payload`.
- `models.py` is unchanged. Disputes are represented by `dispute_id` and the dispute record, not a new order status.
- New event types: `payment_intent.created`, `charge.succeeded`, `checkout.session.completed`, `charge.dispute.created`, `charge.dispute.closed`. These exist in **history only**. The live console's `EventType` and transitions are unchanged.
- Refunds are full refunds only. Partial refunds were not required and are not modelled.

## Wiring (in scope; reported)

- `catalog.py` now loads `data/products.json`, so the storefront shows all 12 products. The original 4 SKUs keep the same ids and prices, and storefront prices equal the history's prices.
- New `history.py`: a read-only loader (cached per process) plus pure metric, filter and search functions. Every displayed number is computed here.
- `app.py`:
  - New 5th tab **Dashboard (90 days)**: metrics; daily gross, daily attempts and weekday bar charts; product revenue; decline reasons.
  - **Event history** section under the Webhook console: type multiselect, free-text search, 25 rows per page, payload JSON per event.
  - **Order history** section under Orders: status filter, search, pagination, and a per-order lifecycle drill-down.
  - Long lists are paginated so the views stay fast with the bigger dataset.
- No existing behaviour was removed. The live cart, checkout, webhook console, idempotency, retry and Reset flows are untouched. The history is read-only and separate from the session store.
- The no-Arrow-tables rule still holds; the three charts use `st.bar_chart`.

## Tests

| | Before | After |
|---|---|---|
| In-tree tests (`pytest tests -q`) | 0 collected (no suite) | **330 passed**, 0 failed |

The new suite is the app's first. It has 31 test functions; one of them is parametrized over all 300 orders, so 30 + 300 = 330 cases. It covers:

- `test_generator.py`: same seed → identical files and hash; a different seed changes the data; committed files match the generator byte for byte; re-running into a dir is idempotent; manifest seed, anchor and hashes; counts in bands.
- `test_dataset.py`:
  - Provenance: example domains, unique ids.
  - Referential integrity: attempt→order, order→customer and products, event→order and charge, refund/dispute→succeeded charge.
  - Window bounds; customer created before their first order; no event before its parent; attempts contiguous and chronological, and only the last can succeed.
  - **Per-order lifecycle story (300 cases):** strict chronological event order, exact event set per outcome, refund and dispute events and timestamps, no refund+dispute overlap.
  - Realistic status mix and the weekday + growth curve.
  - **Money reconciliation:** dashboard gross / refunds / disputes / net equal the dataset sums and the event-payload sums; chart series sum to the totals.
  - Search and filter helpers.
- `test_app.py` (Streamlit AppTest, full dataset loaded):
  - All 5 tabs render with no exceptions, and all 12 products show.
  - Dashboard metric values equal the computed values; 3 charts render.
  - Event-history type filter, search and paging work, and order-history search and drill-down work.
  - The existing live store flow still works (add to cart → place order → checkout → webhook → fulfilled → duplicate ignored).

## AppTest and browser smoke

- AppTest: pass (above). Streamlit 1.66.1, Python 3.13.
- Real browser: `streamlit run app.py` plus headless Chromium. Dashboard and Webhook console screenshots show 0 `stException` elements; the charts render with the visible growth trend and weekday dips.

## Architecture diagram

- `docs/architecture.drawio` was updated by **hand-authored Draw IO XML edits**; no Draw IO skill or desktop app was available in the session.
  - Added `render_dashboard`, `history.py`, `data/*.json`, and `data/generate_data.py` (offline), with their edges.
  - Relabelled `app.py` (5 tabs), `catalog.py` (12 products from products.json), the data lane, and the "No runtime disk writes" box.
  - Re-routed the new edges so they don't cut through boxes, and made the external lane taller.
- PNG re-exported to `docs/images/architecture.png` by rendering the `.drawio` XML with **mxGraph 4.2.2** (the engine draw.io is built on) in headless Chromium at 2.5×.
  - diagrams.net is not reachable through the session's proxy, so this is not a draw.io-desktop export.
  - Two render-only tweaks, not applied to the source: `shape=cylinder3` was drawn as mxGraph's core `cylinder`, and the cell id `keys` was renamed in the render copy because of an mxGraph codec quirk.
  - Not Mermaid.
- README architecture section and `docs/architecture.md` were refreshed for the new data layer.
- Pre-existing layout overlaps (DemoStore / catalog boxes, some crossing labels) were left as they were.

## Files changed

```
sask-stripe-demo/DATA-DEPTH-STRIPE-RUN-REPORT.md   (new)
sask-stripe-demo/data/generate_data.py             (new)
sask-stripe-demo/data/{products,customers,orders,payment_attempts,refunds,disputes,webhook_events,manifest}.json (new)
sask-stripe-demo/history.py                        (new)
sask-stripe-demo/tests/{conftest,test_generator,test_dataset,test_app}.py (new)
sask-stripe-demo/app.py
sask-stripe-demo/catalog.py
sask-stripe-demo/README.md
sask-stripe-demo/docs/architecture.md
sask-stripe-demo/docs/architecture.drawio
sask-stripe-demo/docs/images/architecture.png
```

## Cloud-credit burn (for the Infra ledger)

- Session: `session_01P8L2FtRZJNkAaT9NDNUmi1`, environment `env_017tnPQJcqXHc2LxjYzofA48`, created 2026-10-29T22:02:40Z, origin claude.ai web.
- Billing class reported by the session: `rate_limit_type = ccr_promotional`, `isUsingOverage = false`, status `allowed`. That is the Claude Code cloud-session credit, with no overage.
- **No dollar or credit figure is visible from inside the session.** Infra should read the exact burn for this session id from the account's usage page. Nothing in this report is an estimate dressed up as a figure.

## Not done / follow-ups

- PR opened into `main`; **not merged** (merge after Dashboard verification).
- Screenshots in `screenshots/` predate this change and don't show the Dashboard tab. Re-capture is a separate task.
