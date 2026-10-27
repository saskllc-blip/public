# Diagram landing run report — 2026-10-27

Repo: `/Users/kirankeshava/GitHub/sask-public` (GitHub `saskllc-blip/public`).
Branch: `arch-diagrams-main`, authored fresh against `origin/main` (not cherry-picked).

## Step 1 — origin/main

- Fetched `origin`. Reset `arch-diagrams-main` with `git reset --hard origin/main`.
- `origin/main` tip at start: `aff4b88` (`aff4b88f8579eb32e60378be3cca09d76ef67b25`) — *Merge pull request #2 from saskllc-blip/feature/keepers-demo*. Same tip as the cherry-pick stop report; main had not moved again.
- Parked stack still **not** on main: `6f96e89`, `8f81dff`, `efaff7b` are not ancestors of `origin/main`.

## Step 2 — accuracy gate

Compared each source commit’s `docs/architecture.md` structural claims (entry points, page/view structure, data flow) to the app code on `origin/main`.

| Target | Verdict | Evidence |
|--------|---------|----------|
| Stripe (`79e7505`, `sask-stripe-demo/`) | **INCLUDE** | Main `app.py` is four tabs (`Storefront`, `Checkout`, `Webhook console`, `Orders`) plus sidebar Reset; `DemoStore` lives in `st.session_state`; `catalog.py` has the four named SKUs; `checkout.py` maps `4242…` / `4000…0002`; `WebhookProcessor.deliver` owns status via `_TRANSITIONS`. Matches the doc. |
| Rentals (`51446d8`, `sask-rentals-demo/`) | **INCLUDE** | Main `app.py` uses sidebar radio `Dashboard` / `Properties` / `Tenants & Leases` / `Payments` / `Mortgages`; `DemoPortfolio` + `build_seed()` match Aurora/Cedar, Avery/Morgan, and the KPI / Mark collected / mortgage LTV flows. `update_property` / `delete_property` exist in `service.py` and are not wired in the UI, as the doc says. |
| LinkedIn (`70c82ea`, `sask-linkedin-demo/`) | **INCLUDE** | Main `app.py` is four tabs + header/footer; trending tab imports `fixtures.posts`; chatbot path is validators → FAQ retrieval → local `generate_chatbot_response` (no HTTP). Matches the fixtures-only / no-official-Cloud-demo stance. |
| MediAssist (`51dfcf2`, `ai-powered-medical-assistant/`) | **EXCLUDE** (expected) | Source doc claims five tabs in `views/*.py` and “no Streamlit multipage sidebar.” Main still runs multipage `app.py` + `pages/1_Patient_View.py` … `pages/4_Memory_Logs.py`. No `views/` on `origin/main`. |
| Root overview (`efaff7b`, `docs/architecture.md` + drawio/png) | **EXCLUDE** | Root Draw IO cell `ma` labels MediAssist as “5 tabs,” which is the parked tabs build, not main. The overview also links at MediAssist architecture files that are not landing. |

## Files landed

Verbatim from source commits (blob hashes match):

- `sask-stripe-demo/docs/architecture.drawio`
- `sask-stripe-demo/docs/architecture.md`
- `sask-stripe-demo/docs/images/architecture.png`
- `sask-rentals-demo/docs/architecture.drawio`
- `sask-rentals-demo/docs/architecture.md`
- `sask-rentals-demo/docs/images/architecture.png`
- `sask-linkedin-demo/docs/architecture.drawio`
- `sask-linkedin-demo/docs/architecture.md`
- `sask-linkedin-demo/docs/images/architecture.png`

README Architecture sections (PNG embed + link to `docs/architecture.md` only):

- `sask-stripe-demo/README.md` — replaced the stale `docs/products/sask_stripe_demo/…` pointer with the new section (still one `## Architecture` heading).
- `sask-rentals-demo/README.md` — added the section.
- `sask-linkedin-demo/README.md` — added the section.

Not landed: any MediAssist path, root `docs/architecture.*`, `docs/images/architecture.png`, `ARCH-DIAGRAM-RUN-REPORT-2026-10-26.md`, parked branches.

## Diff stat (`origin/main..HEAD` after commit)

Recorded after the landing commit(s) on `arch-diagrams-main`. Expected fence: included apps’ `docs/**`, their README architecture sections, and this report. No `.py`, no `views/`, no `docs/index.html`, no MediAssist files.

```
DIAGRAM-LANDING-RUN-REPORT-2026-10-27.md
sask-linkedin-demo/README.md
sask-linkedin-demo/docs/architecture.drawio
sask-linkedin-demo/docs/architecture.md
sask-linkedin-demo/docs/images/architecture.png
sask-rentals-demo/README.md
sask-rentals-demo/docs/architecture.drawio
sask-rentals-demo/docs/architecture.md
sask-rentals-demo/docs/images/architecture.png
sask-stripe-demo/README.md
sask-stripe-demo/docs/architecture.drawio
sask-stripe-demo/docs/architecture.md
sask-stripe-demo/docs/images/architecture.png
```

## Tests

MediAssist suite not run (app excluded).

| App | In-tree tests on main |
|-----|------------------------|
| Stripe | no tests ran, 0 collected (`python3 -m pytest . -q` / `--collect-only -q` in `sask-stripe-demo`) |
| Rentals | no tests ran, 0 collected (`python3 -m pytest . -q` / `--collect-only -q` in `sask-rentals-demo`) |
| LinkedIn | no tests ran, 0 collected (`python3 -m pytest . -q` / `--collect-only -q` in `sask-linkedin-demo`) |

## PR and merge

This file is committed on `arch-diagrams-main` before the PR opens, per the brief. Fill-in after merge:

- PR number / URL: *(opened after this commit)*
- Merge SHA: *(merge commit after this commit)*
- Post-merge: `git fetch origin`; `git log origin/main --oneline -3` shows the merge; `git show origin/main:sask-stripe-demo/docs/architecture.drawio` starts with Draw IO XML; `docs/index.html` unchanged by this PR; no MediAssist diagram files on main.

## Parked branches (untouched)

| Branch | SHA |
|--------|-----|
| `showcase-docs` | `efaff7b` |
| `mediassist-ui-tabs-seed` | `8f81dff` |
| `mediassist-live-demo-guards` | `6f96e89` |

No merges, rebases, deletions, or pushes to those branches. Only push: `arch-diagrams-main`. Only merge: this PR.
