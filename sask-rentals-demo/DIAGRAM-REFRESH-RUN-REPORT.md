# Rentals OS — architecture diagram refresh run report

- **Date:** 2026-10-30
- **Branch:** `claude/trusting-fermat-o2o3s7`, cut from `main` at `ef6f075`
- **Scope:** docs only. No application code, data files, or tests were changed.

## Step 0: what the old diagram claimed vs what the code does

I read `app.py`, `service.py`, `seed.py`, `models.py`, `data/generate_data.py`, `data/rentals.json`, the tests, and the old `docs/architecture.drawio` and PNG on `main`.

| # | Old diagram (`architecture.drawio` on main) | Code on main |
|---|---|---|
| 1 | No generator and no JSON file. `seed.build_seed(today)` was labelled "relative fictional dates", as if it built records inline. | `data/generate_data.py` (offline, `SEED = 20261025`, `AS_OF = 2026-10-20`) writes the committed `data/rentals.json`. `seed.load_dataset()` (cached) reads it, and `build_seed(today)` shifts every date by `today − as_of`. |
| 2 | `models.py` listed "Property Tenant Lease Payment Mortgage". | It also has **`Expense`**. `Property` gained city/country/specs/purchase, `Lease` gained `deposit`, and `Payment` gained `amount_paid`. |
| 3 | Data lane had five stores: session, "properties list — Aurora + Cedar + adds", "tenants + leases — Avery / Morgan seed", payments, and mortgages. | Six lists on `DemoPortfolio`: properties 30 (4 vacant), tenants 54, leases 54 (26 active), payments 972, expenses 559, mortgages 21. |
| 4 | No sidebar filters. | Sidebar has Country / City / Search filters, which call `DemoPortfolio.filtered(...)`. Every page renders that scoped view. |
| 5 | Service box: "kpis, add, collect, mortgage". | It also has `country_summary`, `occupancy_history`, `occupancy_from_leases`, and `filtered`. |
| 6 | Dashboard: "occupancy, roll, overdue, vacant". | Dashboard has 8 KPIs (adds portfolio value, property count, collected, pending) plus a by-country table. |
| 7 | Properties: "table + Add property form". | Properties also shows specs, a 12-month occupancy column, and a maintenance & expenses table. |
| 8 | Payments: "Mark collected button". | Payments also shows collected / pending / overdue metrics, the outstanding list (including partials), and full payment history. |
| 9 | Tenants & Leases: renewal flag only. Mortgages: debt, payment, LTV. | Tenants & Leases adds a deposit column. Mortgages adds rate, country, and maturity. |
| 10 | External box "Fictional addresses only — Example Way / Fiction Ave". | Real cities and neighbourhoods; invented streets, people, and records. |
| 11 | External box "Python stdlib only — dataclasses, datetime, uuid". | The app also uses `json`, `pathlib`, and `functools`. The generator also uses `random` and `unicodedata`. |
| 12 | No tests shown. | `tests/test_dataset.py` and `tests/test_app.py` (28 tests), added with the data-depth build. |
| 13 | Render defects in the old PNG: "import streamlit", "rebuild" and "frozen dataclasses" connectors cut through boxes; edge labels overlapped the tenants cylinder; lane titles were crossed by connectors; the title cell was wider than the page. | Fixed by re-routing every edge with explicit waypoints (see below). |

I also found stale text in `docs/architecture.md`: "five lists", "deterministic daily seed", "Example Way / Avery Example", "no in-tree test pack today", "Dashboard surfaces Overdue only", "Surface collected/pending KPIs" (already done), the "Richer seed → extend build_seed()" guidance, and an incomplete stdlib list.

## What changed

**`docs/architecture.drawio`** — rewritten by hand-authoring the Draw IO XML.

- The style was kept: the same lane colours, box/cylinder/edge style strings, title/subtitle cells, the `rounded=1;arcSize=10` boxes, and dashed red "constraint" boxes.
- Lanes are now Entry / UI / Service / Data-State / **Seed data path (new)** / External. The page is 1560×1420.
- **Entry lane:** Visitor → Streamlit Cloud → `app.py` → Reset to demo data.
- **UI lane:** the five radio pages plus **Sidebar filters**. They hang off a single trunk from `app.py`.
- **Service lane:** `service.DemoPortfolio` with its full method list. Each page edge is labelled with the methods it calls. `update/delete_property` (unwired) and `PortfolioError` are kept.
- **Data-State lane:** `session.portfolio`, plus a group of six record-list cylinders with seed counts.
- **Seed data path lane:** `data/generate_data.py` → `data/rentals.json` → `seed.build_seed(today)` → `models.py` (Property · Tenant · Lease · Payment · Expense · Mortgage) → the six lists. `DemoPortfolio.__init__` calls `build_seed()` on first load and Reset.
- **External lane:** Streamlit, No DB/API/auth, 100% fictional records, the updated stdlib list, and pytest (dev only).
- Small style differences, all made so no connector crosses text:
  - Lane titles have per-lane left insets.
  - The "import streamlit" label is a free text cell.
  - The UI-lane note "(sidebar radio — not tabs)" moved onto the trunk label.
  - Cylinders gained `spacingTop=10` so their labels sit below the top ellipse.

**`docs/images/architecture.png`** — re-exported (see the next section).

**`README.md`** — the Architecture section now has a short summary that matches the diagram, lane by lane. The embed path is unchanged.

**`docs/architecture.md`** — the stale lines listed above were corrected to match the code.

**`DIAGRAM-REFRESH-RUN-REPORT.md`** — this report (new).

## How the PNG was produced

- **Method:** the `.drawio` XML was rendered with **mxGraph 4.2.2**, the engine draw.io is built on, from npm. It ran in the session's pre-installed headless Chromium via Playwright, at device scale 2.5×, giving 3900×3550 px.
- **Source:** the XML was generated by a small Python script in the session scratchpad, which is not committed. It has fixed coordinates and explicit waypoints for every bent edge.
- **Not a draw.io export.** No Draw IO skill or desktop app was available, and I did not use diagrams.net.
- **Render-only tweak** (not applied to the source): `shape=cylinder3` was drawn as mxGraph's core `cylinder`. `cylinder3` is a draw.io stencil that core mxGraph does not ship. This is the same approach the Stripe session used. In draw.io itself, cylinders will render with the proper `cylinder3` outline.
- **Visual check: done.** I inspected the full image plus close-up crops of the seed lane and data lane over three iterations. The final render has no overlapping elements, no clipped labels, and no connectors crossing boxes or lane titles. Every edge ends on its intended box.
- Fixes made along the way:
  - The "import streamlit" label was clipped at the page edge.
  - A connector crossed the Data-State lane title.
  - Lane titles were crossed by vertical edges.
  - The `rentals.json` label overlapped the cylinder's top.

## Test result (smoke check)

`python3 -m pytest tests -q` (from `sask-rentals-demo/`; Python 3.13.17, Streamlit 1.66.1, pytest 9.2.0):

```
28 passed in 3.22s
```

## Code changes I'd suggest (not made)

None are needed for this task. One observation only: the Properties-page Add form doesn't let the user enter city or country. Properties added this way therefore show under "—" in the by-country table and in the filters. This is by design (the model's fields have defaults), not a bug.

## Cloud-credit burn (for the Infra ledger)

- **Session ID:** `session_01P8L2FsHKgBrKg6M146ceTf` (https://claude.ai/code/session_01P8L2FsHKgBrKg6M146ceTf)
- **Environment:** `env_017tnPQJcqXHc2LxjYzofA48`, kind `anthropic_cloud`, origin `web_claude_ai`
- **Billing class visible from inside the session** (session metadata): rate-limit type `ccr_promotional`, `isUsingOverage: false`, status `allowed`
- **Dollar figure:** none is visible from inside the session, so none is recorded here.
