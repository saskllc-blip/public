# Data-Depth Run Report — MediAssist longitudinal visit history

- **Date:** 2026-10-29
- **Route:** Claude Code cloud session against `saskllc-blip/public`
- **Session:** `session_01P8L2FpiMituFPMmfGDrZ81`
- **Branch:** `claude/youthful-thompson-ubmzeg`. The session assigned this branch, so `data-depth-mediassist` was not used.
- **Base:** public `main` at `0553e3f` (merge of PR #3)
- **Scope:** `demo-data-depth-scope-2026-10-25.md` §3
- **Data provenance:** 100% synthetic, fictional data. No real patients, no real records, nothing scraped. The existing synthetic-data disclaimers are unchanged and still true.
- **Stacking:** stacks on public `main` only. It does not touch or import from the unmerged local showcase/parked branches.

## Cloud-credit burn (for Infra's ledger)

| Item | Value |
|---|---|
| Credit pool | Claude Code cloud-session credit (expires 2026-11-04 23:59 PST) |
| Session | `session_01P8L2FpiMituFPMmfGDrZ81` (env `env_017tnPQJcqXHc2LxjYzofA48`) |
| Wall-clock | Started 2026-10-29 22:02 UTC; finished about 22:25 UTC (~25 min) |
| Rate-limit bucket | `ccr_promotional`, `isUsingOverage: false` (from `get_session`) |
| Dollar / credit amount | **Not available in this session.** The session API exposes no cost figure. Infra should read the exact burn for this session ID from the billing / usage dashboard. |
| Other spend | None. No API keys used, no paid APIs, no deploys. The OpenAI judge path stays unreached because tests clear `OPENAI_API_KEY`. |

## Step 0: what `main` actually has (before)

| Store | Count on main |
|---|---|
| `data/patients.json` | **5 patients** (P001–P005), with 9 `medical_history` entries in total |
| `data/doctors.json` | **5 doctors** (D001–D005) |
| `data/appointments.json` | **2 appointments** (A001, A002, both Confirmed) |
| Visit-history store | **none** |
| `data/medical_records.json` (vault) | **absent.** It is created at runtime on first upload. |
| Seed/generator script | **none.** The data files on main are hand-written JSON. |

- **Headcount:** main carries 5 / 5 / 2, not the scope doc's 505 / 105 / 500. The 505/105/500 figure is the parked local build.
- **This build:** it does not re-seed or grow the headcount. It adds history depth only.
- **Entry point:** `app.py` (Home) plus `pages/1_Patient_View.py`, `2_Doctor_View.py`, `3_Admin_Dashboard.py` and `4_Memory_Logs.py`.
- **How views read data:** through `tools/*.py`. Some views also open the JSON files directly.
- **Baseline test suite:** **29 passed** with `langchain-openai` installed.
  - The README said "14 tests"; that line was stale and is now corrected.
  - With only `streamlit`, `plotly` and `pytest` installed, 2 evaluator tests fail at import (`langchain_openai` missing). That is an environment issue, not a code issue.
- **Baseline AppTest:** all 5 views render with **0 exceptions**.

## Dataset after the build, and the scaling used

- **Scaling rule:** the scope doc's ~2,500 visits for 505 patients works out to **4.95 visits per patient**.
  - Main has 5 patients, so the target is about 25 visits.
  - Accepted band: ±20%, i.e. 20–30 visits.
  - Per-patient draw: 3–8 visits, weights `{3:2, 4:4, 5:4, 6:2, 7:1, 8:1}` (mean about 4.93).
- **Recently-added patients:** main has none, so none get the reduced visit count.
- **Lab coverage:** the target of 40% of 5 patients means **2 patients**.

| Metric | Result |
|---|---|
| Total past visits | **27** (band 20–30) |
| Per patient | P001 7 · P002 6 · P003 4 · P004 5 · P005 5. All 5 are in the 3–8 band. |
| Anchor visits (verbatim from `medical_history`) | 9 of 9 |
| Visit types | Follow-up 14 · Initial Consultation 6 · Referral 3 · Specialist Consultation 3 · Acute Visit 1 |
| Visits by doctor | Anil Mehta 9 · Ramesh Gupta 9 · Priya Nair 5 · Kavita Singh 4 · Sunanda Rao 0 |
| Date span | 2021-08-22 → 2024-04-01. Each patient spans ≤ 3 years and ends exactly on their `last_visit`. |
| Medication events | 20 (start / adjust / short_course) |
| Lab result sets | **2** on 2 of 5 patients (40%). Details below. |

**Lab sets:**
- **P001** (diabetic, the patient with the most lab-relevant conditions): HbA1c 7.2%, matching the anchor note "HbA1c: 7.2%".
- **P002:** Hb 9.8 g/dL, matching the anchor note.

**Notes on the dataset:**
- **Dr. Sunanda Rao (Cardiologist) has no visits.** No patient on main has a cardiology condition or anchor, and inventing one would break the "own condition set" rule. Doctor View shows "No past visits recorded." for her.
- **The lab panel is thin (2 sets).** The seeded 1–3 draw landed on 1 set for each lab patient. That is an honest outcome of the proportional scaling at 5 patients.
- **Dataset SHA-256:** `cd1230ebbb4625b8a9b6997f0254b9dd57c2d3b2e3bf049ec10c5d7f63efbf2a`

## Generator design (`scripts/generate_visit_history.py`)

**Determinism:**
- `SEED = 20261029`, with per-patient sub-seeds (`sha256("SEED:pid")`). Adding a patient never reshuffles the existing patients' history.
- The output contains no timestamps. Re-running it rewrites identical bytes.
- `--check` exits 1 if the committed file is stale.

**Anchors:**
- Every `patients.json` `medical_history` entry becomes a visit with the same date, doctor, diagnosis, treatment and notes.
- Generated visits are woven around the anchors. None fall after `last_visit`, and none fall more than 1,095 days before it.

**Condition library:**
- There is one profile per condition on main (HTN, T2DM, CKD, RA, anemia, asthma, hypothyroidism, osteoporosis, migraine).
- A profile holds complaints, advice, an acute-episode template, a lab panel and medication dose ladders.
- An unmapped diagnosis or medication **raises an error rather than being dropped**.

**Continuity rules:**
- **Diagnoses:** always drawn from the patient's own condition set.
- **Acute visits:** these are flare-ups of the patient's own conditions. There are at most 2 per patient, and each comes after that condition is first seen.
- **Medications:** an event stream. Each drug starts at that condition's first treated visit and steps up along the ladder.
  - The final step lands on the last pre-anchor visit. When the anchor note describes an uncontrolled state (e.g. "ESR elevated", "TSH 8.5, adjustment may be needed"), it lands on the anchor itself.
  - Replaying the stream must equal `current_medications` exactly; the generator asserts this.
  - Short courses (prednisolone, metoclopramide) never persist.
- **Control status:** each visit is Newly diagnosed, Uncontrolled (on step-up), Improving, or Controlled, with an occasional seeded flip.
- **Referrals:** when a condition's managing doctor is not the primary doctor, a primary-doctor Referral visit comes 2–6 weeks before that condition's first visit. That next visit is a Specialist Consultation carrying `referred_from_visit_id`.
- **Primary doctor:** the most frequent anchor doctor, with ties broken toward the General Physician.
- **Vitals:** BP is elevated until antihypertensives start and rises on uncontrolled visits. HR rises during acute and anemia episodes and drops on propranolol. BMI drifts down for diabetics. Any BP quoted in an anchor note (130/80) is used exactly.
- **Labs:** sets attach to real visits, using the panel for that visit's condition. Values track the visit's control status, and any number quoted in the anchor note is used verbatim.
- **Statuses:** every past visit has `status: "Completed"`, alongside the appointment book's Confirmed/Cancelled.
- **Timeline:** all history pre-dates each patient's booked appointments.

## Safe store, and why it avoids the vault landmine

**The landmine, located:**
- `pages/1_Patient_View.py` renders vault records once in **each of 5 filter tabs** ("All" plus the per-type tab).
- Each render uses `key=f"text_{record_id}"`, `dl_{record_id}` and `del_{record_id}`.
- Any vault record therefore appears twice (in "All" and in its type tab) with the same keys. That raises `DuplicateWidgetID` and crashes Patient View.
- **Not fixed here.** That fix belongs to the parallel MediAssist bug-fix session, and changing it here would conflict.

**The store this build uses:**
- History lives in a new file, **`data/visit_history.json`** (`config.VISIT_HISTORY_FILE`). It follows main's pattern of one JSON file per entity under `data/`.
- `schema_version`, `disclaimer` and `generator` metadata sit alongside two lists: `visits` (unique `visit_id`) and `lab_results` (unique `lab_id`, each with a `visit_id` foreign key).
- History never touches `medical_records.json` or `medical_vault_tool.py`. A test proves the generator leaves the vault file's existence and bytes unchanged.
- It is read only through the new read-only `tools/visit_history_tool.py`.
- The views render history as **dataframes and a line chart only**, with no per-record widgets and so no widget keys that could collide, however large the history grows.

**Small extension to existing behaviour:**
- `ehr_tool.get_medical_history` now appends a "Visit Timeline" to `history_text` and returns `visit_count`.
- This feeds the agent and Doctor View's "Load Full History".
- Nothing existing was removed.

**Not changed:**
- The FAISS index (`vectorstore/patient_index`) still indexes `patients.json` only.
- Rebuilding it to include visits is a possible follow-up. It was left alone because the index is committed and the RAG path is out of scope.

## Tests

| Suite | Before | After |
|---|---|---|
| `tests/test_evaluator.py` + `tests/test_medical_vault.py` (existing) | 29 passed | 29 passed |
| `tests/test_visit_history.py` (new) | — | 22 passed |
| `tests/test_views_apptest.py` (new) | — | 6 passed |
| **Total** | **29 passed** | **57 passed** (`pytest -q`: `57 passed in 3.50s`) |

**New tests in `tests/test_visit_history.py`:**
- **Determinism and idempotence:**
  - The same seed gives an identical SHA-256.
  - The committed file equals a fresh build, and `--check` returns 0.
  - Rerunning gives byte-identical output.
  - A different seed changes the output.
  - The vault file is untouched.
- **Counts:**
  - The total falls in the scaled band.
  - The majority of patients have 3–8 visits, and every patient has history.
  - Lab coverage is `round(0.40 × N)` patients, each with 1–3 sets.
- **Referential integrity:**
  - Every visit references a real patient and doctor, and names/specializations match.
  - Visit and lab ids are unique.
  - Each lab's visit, patient, date and condition match, and the panel fits the condition.
- **Continuity and timeline:**
  - Each diagnosis is in the patient's condition set.
  - The medication replay equals `current_medications`, and every adjustment's previous dose was active.
  - No medication conflicts with an allergy, including the NSAID class.
  - No visit after `last_visit`, and the last visit equals `last_visit`.
  - Each patient's span is ≤ 3 years, and all history pre-dates that patient's appointments.
  - Anchors are reproduced verbatim.
  - Every referral is followed by the specialist visit, with a back-link.
  - Acute visits are sparse and come after the condition's first visit.
  - Lab markers are worse when Uncontrolled than when Controlled, for all 8 panels.
  - Numbers quoted in anchor notes are honoured.
- **Tool layer:**
  - Visits come back newest first, and the replay equals current meds.
  - The EHR text includes the timeline.
  - A missing store degrades to empty.

## AppTest evidence (hard acceptance gate)

Run with the full history loaded (`data/visit_history.json` committed). Runtime logs were redirected to a temp directory.

```
tests/test_views_apptest.py::test_other_views_render_without_exceptions[app.py] PASSED
tests/test_views_apptest.py::test_other_views_render_without_exceptions[pages/3_Admin_Dashboard.py] PASSED
tests/test_views_apptest.py::test_other_views_render_without_exceptions[pages/4_Memory_Logs.py] PASSED
tests/test_views_apptest.py::test_patient_view_renders_full_history_for_every_patient PASSED
tests/test_views_apptest.py::test_doctor_view_renders_visit_history_for_every_doctor PASSED
tests/test_views_apptest.py::test_doctor_view_full_history_lookup_includes_visit_timeline PASSED
============================== 6 passed in 3.40s ===============================
```

**Patient View:**
- Selects **every one of the 5 patients** and asserts `at.exception` is empty after each rerun.
- Asserts exactly one visit table is rendered, with a row count equal to that patient's visits.

**Doctor View:**
- Selects **every one of the 5 doctors**, asserts zero exceptions, and checks that the visit table row count equals that doctor's visits (no table for Dr. Sunanda Rao).
- Then walks every patient in Patient Lookup, clicks "Load Full History", and asserts zero exceptions and that "Visit Timeline" appears.

**Home, Admin Dashboard and Memory & Logs:** each renders with zero exceptions.

**Environment:** streamlit 1.66.1, Python 3.13.

## Architecture diagram

- **No Draw IO skill was available in this session, and diagrams.net was blocked by the network policy.**
  - `docs/architecture.drawio` was hand-authored as Draw IO XML, in the same style as the Stripe/Rentals/LinkedIn diagrams on main.
  - `docs/images/architecture.png` was rendered by a local script from **the same cell geometry**, via SVG and headless Chromium. It is not a draw.io export, so draw.io's own edge routing may differ slightly when the file is opened there.
  - No Mermaid substitute was used.
- **Contents:** main's actual structure — 4 pages plus Home, `HealthcareAgent` / planner / memory, evaluator, the 7 tools, the JSON data files, the FAISS index, logs and the optional externals. The visit-history additions are marked ★.
- **Not drawn:** the parked five-tab build.
- **README:** the app README gains an Architecture section (PNG embed, link to the source, a visit-history design summary, and an updated directory layout).

## Files changed (vs `main` @ `0553e3f`)

| File | Change |
|---|---|
| `scripts/generate_visit_history.py` | **new:** generator |
| `data/visit_history.json` | **new:** generated dataset |
| `tools/visit_history_tool.py` | **new:** read-only store access and medication replay |
| `config.py` | + `VISIT_HISTORY_FILE` |
| `tools/ehr_tool.py` | history text appends the visit timeline; adds `visit_count` |
| `pages/1_Patient_View.py` | Medical History tab: visit table, vitals trend, medication history, labs |
| `pages/2_Doctor_View.py` | Schedule tab: past-visit metrics and table |
| `tests/test_visit_history.py` | **new** |
| `tests/test_views_apptest.py` | **new** |
| `docs/architecture.drawio`, `docs/images/architecture.png` | **new** |
| `README.md` | Architecture section, test count, layout |
| `DATA-DEPTH-MEDIASSIST-RUN-REPORT.md` | this report |

## Rails check

- Synthetic data only ✔.
- No external sends, payments, API keys or deploy ✔. This build ships nothing; the MediAssist ship stays gated on Kiran's go-ahead.
- No existing app behaviour was deleted ✔. No UI redesign; history was added as sections inside existing tabs.
- PR is opened into `main` and **not merged**. It merges only after Dashboard verification.

## Reproduce

```bash
cd ai-powered-medical-assistant
pip install -r requirements.txt   # or minimally: streamlit plotly pandas pytest langchain-openai
python scripts/generate_visit_history.py --check
pytest -q
```
