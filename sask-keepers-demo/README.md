# Keepers — SASK SW Services Demo

A self-contained Streamlit showcase of **Keepers by SASK** — a local-first
photo-library cleanup product. This demo runs on a generated *fictional*
library of ~800 items: Dashboard, burst/duplicate Review, Prompt Builder,
Library Map search, and GPS Places.

**Demo — fictional library, no real photos.** No real names, no real
library rows, no stock photography, no network image fetches.

The app does **not** import or depend on the private Keepers repository
at runtime. Quarantine is simulated in the session; nothing is deleted.

## What it shows

- **Dashboard** — library size, reclaimable-GB estimate, counts by rule
  (R1 bursts/duplicates, R2 screenshots except favorites, R3 no-people/scenery).
- **Review Groups** — burst sets side-by-side, nominated Keeper badged,
  per-item quality scores and reason chips.
- **Prompt Builder** — type `screenshots not from Maui` → interpretation
  chips (screenshot + negated place) with the **unknown-location safety
  rule** applied: items without GPS never match a negative place filter.
- **Library Map** — search over filename, labels, and place.
- **Places** — counts by fictional travel place, plus an
  `Unknown location` bucket (~40% of the catalog, by design).

Thumbnails are small PIL gradient tiles generated per label family at
build time (`assets/tiles/`), not photographs. This is the lighter route:
eleven family tiles instead of 800 image files.

## Screenshots

- [Dashboard](docs/screenshots/01-dashboard.png) — library size, reclaimable GB, rule counts
- [Review Groups](docs/screenshots/02-review-groups.png) — burst set, Keeper badge, scores
- [Prompt Builder](docs/screenshots/03-prompt-builder.png) — `screenshots not from Maui` + safety rule

## Run locally

```bash
cd sask-keepers-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_data.py          # optional — committed JSON is already here
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

## Tests

```bash
cd sask-keepers-demo
python3 -m pytest tests/test_demo.py -q
```

## Deploy (not done in this PR)

This folder is published in the SASK public showcase repository
(github.com/saskllc-blip/public). On Streamlit Community Cloud, create an
app from that repository, branch `main`, with main file path
`sask-keepers-demo/app.py`. No secrets are required.

Cloud hookup is a **separate step** — this package is prepared for it
but is not deployed from this PR. No new accounts are created here.

## Regenerating the fictional library

```bash
python generate_data.py
```

Seeded and deterministic (`SEED = 20261026`). Re-running overwrites
`data/library.json` and the label-family tiles.

---
© 2026 SASK LLC — SW Services · Public portfolio demonstration.
AI tools for speed, human review and automated testing for reliability.
