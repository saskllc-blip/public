# Rentals OS architecture

This document describes the system as it exists in this folder. Where an older README note disagrees with a module, **the code wins**.

Draw IO source: [`architecture.drawio`](architecture.drawio). Export: [`images/architecture.png`](images/architecture.png).

## Purpose and scope

A session-isolated Streamlit console for a fictional rental portfolio: occupancy and rent-roll KPIs, properties, tenants and leases, rent payments, and mortgage roll-ups.

Scope of this folder:

- Sidebar **radio** navigation (not tabs): Dashboard, Properties, Tenants & Leases, Payments, Mortgages.
- Frozen dataclasses + a deterministic daily seed + one in-memory service.
- No database, external service, analytics, authentication, or paid API.

Out of scope: real properties, Plaid/bank links, accounting export, user accounts.

Live hosted demo: https://public-es3d2bknt56jnfpclfltnu.streamlit.app/

## Component inventory

| Module | Responsibility |
|--------|----------------|
| `app.py` | Entry point. `st.set_page_config`, creates `st.session_state.portfolio = DemoPortfolio()` once, fictional-data banner, sidebar radio + **Reset to demo data**, page bodies (metrics, dataframes, Add property form, Mark collected, mortgage table). |
| `service.py` `DemoPortfolio` | In-memory operations: `add_property`, `update_property`, `delete_property`, `collect_payment`, `kpis()`, `mortgage_summary()`, `_property_index`. Raises `PortfolioError` for UI-safe validation. |
| `seed.py` `build_seed(today)` | Loads the committed synthetic dataset `data/rentals.json` (30 properties in 10 cities / 9 countries, 54 leases, 972 payments, 559 expenses, 21 mortgages) and shifts every date by `today - as_of`, so overdue rows and **Renewal pending** flags stay true on any day. |
| `data/generate_data.py` | Deterministic generator (seed `20261025`) that writes `data/rentals.json` byte-for-byte. 100% fictional: real cities/neighbourhoods, invented streets, tenants, and records; USD amounts calibrated per locale. |
| `models.py` | Frozen dataclasses: `Property` (+ city, country, neighbourhood, specs, purchase), `Tenant`, `Lease` (+ deposit; `renewal_pending` if active and ≤30 days), `Payment` (+ `amount_paid` for partials; `effective_status` pending→overdue when `due_date < today`), `Expense`, `Mortgage` (`ltv`). |

**Code vs README:** `update_property` and `delete_property` exist on `DemoPortfolio` but are **not wired in the UI**. `kpis()` also computes collected/pending totals; the Dashboard surfaces **Overdue** only (plus occupancy, rent roll, vacant units). There is no per-property performance page.

## Data-flow walkthroughs

### First load / Reset

1. Missing `st.session_state.portfolio` → `DemoPortfolio()` → `build_seed()` → five lists copied onto the service.
2. **Reset to demo data** replaces the session object with a new `DemoPortfolio()` and `st.rerun()`.

### Dashboard KPIs

`portfolio.kpis()`:

- `occupancy_rate` = `(total_units - vacant_units) / total_units * 100`
- `rent_roll` = sum of `monthly_rent` for `status == "active"` leases
- `vacant_units` = sum of `Property.vacant_units`
- `payments` = ledger: paid amounts are `collected`; any unpaid remainder is `pending` until due, then `overdue`
- `portfolio_value` = sum of `Property.estimated_value`; `occupancy_from_leases(today)` re-derives occupancy from lease windows (tests assert it equals `occupancy_rate`)

The sidebar **Country / City / Search** filters build a scoped `DemoPortfolio.filtered(...)` view; every page renders from that view, while actions (add property, mark collected) still go to the full portfolio.

The Dashboard shows occupancy, rent roll, overdue $, vacant units, portfolio value, property count, collected-to-date, pending, and a by-country table.

### Add a property

Properties page form → `add_property(name, address, kind, units)`. Empty name/address or `units < 1` raises `PortfolioError`. New id is `prop-` + 8 hex chars. `vacant_units` is initialized equal to `total_units` (new building is fully vacant). Metrics update on the next Dashboard view.

### Mark a payment collected

Payments page lists every `Payment`. If `status != "collected"`, **Mark collected** → `collect_payment(id, date.today())` which `dataclasses.replace`s that row to `status="collected"` and sets `collected_date`. Overdue total drops on the next render.

### Mortgage roll-up

`mortgage_summary()`: sum of balances, sum of monthly payments, balance-weighted average rate. The table adds per-row LTV via `Mortgage.ltv(property.estimated_value)`.

## Data model and where state lives

`st.session_state.portfolio` holds six Python lists, loaded from the read-only `data/rentals.json`:

| List | Seed rows | Notes |
|------|-----------|--------|
| `properties` | 30 (3 each in Memphis, Greensboro, Toronto, London, Berlin, Sydney, Bangalore, São Paulo, Cape Town, Singapore); 4 vacant | Real neighbourhoods, invented street names; 1 unit each |
| `tenants` | 54, one per lease | Locale-appropriate fictional names; `@example.demo` emails |
| `leases` | 54: 26 active, 28 ended; 24 properties have a prior lease; 4 renew within 30 days | No overlaps; rent rises from prior lease |
| `payments` | 972 (12–24 per lease) | Mostly on time; ~12% late; a few partials; a few current-month overdue |
| `expenses` | 559 | Quarterly management fees, annual inspections, repairs, turnover cleans |
| `mortgages` | 21 | Amortized balances, locale-typical rates |

No disk, no SQLite, no env vars. Refresh or Reset rebuilds from `build_seed()`.

## External services and dependencies

- Streamlit `>=1.28,<2`
- Standard library only (`dataclasses`, `datetime`, `json`, `uuid`)
- Hosted on Streamlit Cloud for the public demo

## Key design decisions and constraints

- **Session isolation.** Every visitor gets their own `DemoPortfolio`. Nothing is shared or persisted.
- **Relative seed dates.** `build_seed(today)` keeps the overdue row and the 30-day renewal flag true on any calendar day.
- **Frozen dataclasses.** Updates go through `replace()` so the UI cannot mutate fields in place by accident.
- **Synthetic names only.** Example Way / Fiction Avenue / Avery Example / Morgan Sample.
- **Thin UI.** `app.py` is one file; business rules stay in `service.py` so the same methods could be unit-tested without Streamlit (there is no in-tree test pack today).

## How to extend it

1. **Wire update/delete:** add forms in the Properties page that call the existing `update_property` / `delete_property` (delete already refuses a property with an active lease).
2. **Surface collected/pending KPIs:** `kpis()["payments"]` already has the totals; add metric widgets.
3. **Richer seed:** extend `build_seed()`; keep names obviously fictional.
4. **Do not** add a real database or tenant PII in this public folder.

Run from this folder: `python3 -m pytest tests -q` (needs `pytest`; 28 tests incl. Streamlit AppTest). Regenerate data with `python3 data/generate_data.py`.
