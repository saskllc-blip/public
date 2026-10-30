# Data-Depth: Rentals — Run Report (2026-10-29)

Scope: `demo-data-depth-scope-2026-10-25.md` (Rentals, final state). App: `sask-rentals-demo/`.
Provenance: **100% synthetic.** Real cities and neighbourhoods; invented street names, tenants, leases, payments, expenses, and mortgages. No real listings, no scraped data, no real people. The app's "fictional data" banner stays and is still true.

## Step 0 — before (read from `main` @ `0553e3f`)

| Item | Count |
|---|---|
| Properties | 2 |
| Tenants | 2 |
| Leases | 2 |
| Payments | 2 |
| Mortgages | 2 |
| Tests in app | **0** (no test folder; `pytest` collected nothing) |

Data path before: `app.py` → `DemoPortfolio()` → `seed.build_seed(today)` (hardcoded Python rows, dates relative to today). No data files.
Dashboard before: occupancy, rent roll, overdue, vacant units — all already computed by `kpis()`, **none hardcoded**. Portfolio value was not shown anywhere.

## After

| Item | Count |
|---|---|
| Properties | **30** (10 cities, 9 countries, 3 per city) |
| Tenants | 54 |
| Leases | 54 — 26 active, 28 ended; 24 properties have a prior lease; 4 flagged *Renewal pending* |
| Payments | 972 — 12–24 per lease; ~12% paid >5 days late; 11 partials; 3 current-month unpaid (overdue) |
| Expenses | 559 — quarterly mgmt fees, annual inspections, repairs, turnover cleans |
| Mortgages | 21 |
| Occupancy at as-of | 86.7% (26/30), identical whether computed from units or from lease windows |

Cities: Memphis, Greensboro (US) · Toronto · London · Berlin · Sydney · Bangalore · São Paulo · Cape Town · Singapore.

## Generator design

- File: `data/generate_data.py` → writes `data/rentals.json`. Run: `python3 data/generate_data.py`.
- **Seed `20261025`**, `as_of` 2026-10-20. Single `random.Random(seed)`; canonical JSON (`sort_keys`, fixed indent) → re-runs are byte-identical. Dataset SHA-256: `1ca10cba67ee8905e8a4f17a4af2fd4a8fb44330034c7e4065fdb2d3a3ddb7b9`.
- Money in **USD, calibrated per city** (value range, rent range, appreciation rate, deposit custom, cost factor, mortgage rates) — e.g. Bangalore rents < $1k, London values > 2× Memphis, Singapore condos > $1M.
- Purchase price back-computed from current value along the city's appreciation path (2012–2022 purchases).
- Leases built backwards from `as_of`: current lease started ≥12 months ago (so ≥12 payments); prior lease ends before the current one starts (0–2 month turnover gap); prior rent 2–8% lower. 4 properties are vacant 1–3 months after their last lease ended. Deposits follow local custom (e.g. Berlin 3×, Bangalore 8×).
- Payments due on the 1st, only inside the lease window and on/before `as_of`; collected dates are also clamped inside the window.
- Loader (`seed.py`) shifts every date by `today − as_of`, preserving the app's existing "relative seed dates" design (overdue rows and renewal flags stay true on any day).

## Schema extensions (minimal; all with defaults so existing code paths keep working)

- `Property`: `city`, `country`, `neighbourhood`, `bedrooms`, `bathrooms`, `sqft`, `year_built`, `purchase_date`, `purchase_price` (current value reuses existing `estimated_value`).
- `Lease`: `deposit`; helper `covers(day)`.
- `Payment`: `amount_paid` (needed for partials); helpers `paid()`, `outstanding()`, `days_late()`.
- New `Expense` dataclass + `expenses` list (maintenance/expense events had no home).
- No field from the brief was dropped.

## Wiring changes

- `kpis()` now reconciles a ledger: paid → collected, unpaid remainder → pending/overdue; adds `portfolio_value`, `property_count`.
- New: `occupancy_from_leases()`, `occupancy_history()` (trailing 12 m per property), `country_summary()`, `filtered(countries, cities, query)`.
- Dashboard: **Portfolio value** (newly surfaced, computed from data), properties, collected-to-date, pending, by-country table.
- Sidebar **Country / City / Search** filters scope every view; actions still hit the full portfolio.
- Scale fix: Payments view used to render a row + button per payment (~970 widgets); now lists only outstanding payments with buttons, plus one history dataframe.
- Properties view: location/spec columns, 12-month occupancy, expenses table. Add-property form unchanged.

## Tests

| | Count |
|---|---|
| Before | 0 |
| After | **28 passed** (`python3 -m pytest tests -q`, ~3 s) |

- `tests/test_dataset.py` (20): determinism (same seed → same hash; committed file == generator output; different seed differs), counts/bands, global spread, locale calibration, referential integrity, payments inside lease windows, realistic payment mix, no overlapping leases, status matches timeline, occupancy derivable and 0–100, ledger reconciles, dashboard numbers from data, date shift, filters, existing operations (add property, mark collected, renewal flag).
- `tests/test_app.py` (8, Streamlit AppTest, full dataset): all 5 views render with no exceptions; dashboard shows 30 properties; country filter → 3 (India), city filter → 6 (London + Berlin); text search scopes every view; Mark collected works.
- Env: Python 3.13, Streamlit 1.66.1, pytest installed locally (not added to `requirements.txt`, which stays deploy-only).

## Files changed

- `data/generate_data.py` (new), `data/rentals.json` (new, ~330 KB)
- `models.py`, `seed.py`, `service.py`, `app.py`
- `tests/test_dataset.py`, `tests/test_app.py` (new)
- `README.md`, `docs/architecture.md`, this report

## Notes

- Stacks on public `main` only; does not touch the unmerged local showcase branches.
- `docs/architecture.drawio` / `.png` still show the old seed description inside the diagram box; text docs are updated. Diagram refresh left for a follow-up.
- Branch: built on the session's designated branch `claude/exciting-pasteur-ffqxr4` (the cloud session only allows pushing there) rather than `data-depth-rentals`.
