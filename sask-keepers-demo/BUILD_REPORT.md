# Keepers demo — BUILD_REPORT

Built in `~/GitHub/sask-public` only (github.com/saskllc-blip/public).
The private Keepers checkout was not used at runtime and was not edited.

**PR (left open for Buddy's verified merge):** https://github.com/saskllc-blip/public/pull/2

## What shipped

Self-contained Streamlit package `sask-keepers-demo/`:

| Surface | Behavior |
| --- | --- |
| Banner | Persistent: “Demo — fictional library, no real photos.” |
| Dashboard | 800 items, 3.303 GB, reclaimable 1.926 GB, unknown location 312; rule cards R1/R2/R3 |
| Review Groups | Burst sets side-by-side, Keeper badge, score chips; in-session quarantine only |
| Prompt Builder | Sample `screenshots not from Maui` → screenshot + negated place chips; unknown-location safety applied; 58 matches (no unknown-GPS rows) |
| Library Map | Search over filename / labels / place |
| Places | Counts by fictional travel place + Unknown location bucket (312 / 39%) |

**Tiles:** eleven PIL gradient tiles generated per label family at build time (`assets/tiles/`). Lighter than 800 image files; no stock photos; no network fetches.

**Runtime isolation:** `app.py` / `library.py` / `prompt.py` / `theme.py` / `generate_data.py` do not import the private `keepers` package. `requirements.txt` is streamlit + pillow only.

## Data (synthetic, seeded)

- Generator: `python generate_data.py` (`SEED = 20261026`)
- Catalog: `data/library.json` — `generated: fictional-only`, 800 items, 48 groups, 312 unknown-location (39%)
- Places: Maui, Kyoto, Swiss Alps, Lisbon, Banff, Reykjavik, Santorini, Queenstown, Marrakech, Patagonia — all fictional travel labels, no real library rows

## Verify

```
cd ~/GitHub/sask-public/sask-keepers-demo
python3 -m pytest tests/test_demo.py -q
..........                                                               [100%]
10 passed in 0.82s
```

Local run (free port **8517** — :8501 was already in use by another process; not touched):

```
.venv/bin/streamlit run app.py --server.port 8517 --server.address 127.0.0.1 --server.headless true
```

Browser smoke (http://127.0.0.1:8517): Dashboard, Review Groups, Prompt Builder, Library Map, and Places each rendered without exceptions. Screenshots:

- `docs/screenshots/01-dashboard.png`
- `docs/screenshots/02-review-groups.png`
- `docs/screenshots/03-prompt-builder.png`

## Deploy / accounts

None. Streamlit Cloud hookup is prepared (`sask-keepers-demo/app.py` as the main file on `main`; no secrets) and is a separate step. GitHub Pages card is a follow-up. No new accounts.

## Git output

```
$ git checkout -b feature/keepers-demo
Switched to a new branch 'feature/keepers-demo'

$ git commit
[feature/keepers-demo f884f3a] Add a synthetic Keepers Streamlit demo to the public showcase.
 26 files changed, 21826 insertions(+)

$ git log -1 --format='%H %s'
f884f3a474672b9be9ba1c5c11c2d9b6deaea4f7 Add a synthetic Keepers Streamlit demo to the public showcase.

$ git push -u origin feature/keepers-demo
To https://github.com/saskllc-blip/public.git
 * [new branch]      feature/keepers-demo -> feature/keepers-demo
branch 'feature/keepers-demo' set up to track 'origin/feature/keepers-demo'.

$ gh pr create --base main --title "Add Keepers synthetic Streamlit demo"
https://github.com/saskllc-blip/public/pull/2

$ gh pr view 2 --json url,number,baseRefName,headRefName,title,state
{"baseRefName":"main","headRefName":"feature/keepers-demo","number":2,"state":"OPEN","title":"Add Keepers synthetic Streamlit demo","url":"https://github.com/saskllc-blip/public/pull/2"}
```

Merge is Buddy’s under Kiran’s 2026-10-26 delegation — this PR is left open.

---
© 2026 SASK LLC — SW Services · fictional library only
