# Rentals OS — SASK SW Services Demo

A session-isolated Streamlit portfolio demo built by **SASK SW Services**
(SASK LLC, Saratoga, CA). It shows the dashboard we build for rental-property
operators: portfolio KPIs, properties, tenants and leases, rent payments, and
mortgage summaries in one place.

Every record is conspicuously fictional. The app uses no database, external
service, analytics, authentication, or paid API — state lives in the session
and resets on demand.

## Features

- Live occupancy, rent-roll, collection, and vacancy KPIs
- Property creation with metrics updating immediately
- Lease-renewal flags, payment collection, and mortgage LTV views
- 30 fictional properties across 10 cities in 9 countries (USD, locale-calibrated), with lease, payment, and expense history
- Country / city / text filters that scope every view
- One-click reset to deterministic fictional seed data (`data/generate_data.py`, fixed seed)

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

This folder is published in the SASK public showcase repository
(github.com/saskllc-blip/public). On Streamlit Community Cloud, create an app
from that repository, branch `main`, with main file path
`sask-rentals-demo/app.py`. No secrets are required.

## Architecture

![Architecture](docs/images/architecture.png)

- **Entry:** `app.py` on Streamlit Cloud, sidebar radio over five pages
  (Dashboard, Properties, Tenants & Leases, Payments, Mortgages), plus Country / City /
  Search filters and **Reset to demo data**.
- **Service:** one `DemoPortfolio` per session (`st.session_state.portfolio`) for KPIs,
  country summary, occupancy history, filtered views, mortgage roll-up, add property, and
  mark collected.
- **Data / state:** six in-memory lists of frozen records: properties, tenants, leases,
  payments, expenses, and mortgages.
- **Seed data path:** `data/generate_data.py` (offline, seed `20261025`) writes the committed
  `data/rentals.json`. At startup, `seed.build_seed(today)` loads it, shifts every date by
  `today − as_of`, and builds the `models.py` dataclasses: `Property`, `Tenant`, `Lease`,
  `Payment`, `Expense`, `Mortgage`.
- **External:** Streamlit and the Python standard library only. There is no database, API,
  auth, or secrets, and every record is fictional.

See [docs/architecture.md](docs/architecture.md).

---
© 2026 SASK LLC — SW Services · Public portfolio demonstration.
AI tools for speed, human review and automated testing for reliability.
