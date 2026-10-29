# MediAssist Bug-Fix Pass — Run Report (2026-10-29)

- **Scope:** `ai-powered-medical-assistant/` on public `main` (multipage build). The five-tab `views/` build was not touched or used.
- **Baseline:** `main` @ `0553e3f`, taken **before** `data-depth-mediassist` landed. The two sessions ran in parallel, so the seed data here is the old data.
- **Branch:** `claude/intelligent-bell-rnhiut` (assigned by the cloud session). One commit per fix.
- **Nothing shipped:** no merge, no deploy, no Streamlit redeploy, no API key, no external sends. All data is synthetic: the seed JSON, plus vault records the tests generate.

## Results

| | Before (main) | After (branch) |
|---|---|---|
| pytest | **29 passed** (needed `langchain-openai` installed by hand; the first run showed 2 import failures) | **62 passed** (29 existing + 33 new) |
| AppTest, plain page loads (5 pages) | 0 exceptions | 0 exceptions |
| AppTest, full flow sweep (~95 interactions) | **1 crash** (vault duplicate key) | **0 exceptions** |
| Tool-log rows written into the real `logs/` per pytest run | 35 | 0 |

- Suite run on two dependency sets:
  - langchain 0.3.30 / streamlit 1.66.1 / pandas 3.1.0
  - a fresh install of the latest versions: langchain 1.4.7 / streamlit 1.66.1 / pandas 3.1.0
- Both green: 62/62.

## Known historical defects — checked on main

| # | Defect | On main? | Evidence |
|---|---|---|---|
| a | pandas `Styler.applymap` removal | **Fixed** (`0d5a3cd`) | No `applymap` anywhere; Doctor View and Admin use `.style.map`; both render under pandas 3.1 |
| b | `log_tool_call` extra-kwargs TypeError | **Fixed** (`97c71b2`) | `**extra` is accepted; the vault tests pass extra kwargs and pass |
| c | Vault duplicate-widget-key crash in Patient View | **Not fixed. Still crashed on main** | See D1 |

## Defect log

Severities: **crash**, **wrong data**, **cosmetic**, **hygiene** (repo/test safety).

### Fixed

| ID | Sev | Page / flow | Repro → expected vs actual | Fix | Test (fails before, passes after) |
|---|---|---|---|---|---|
| D1 | crash | Patient View → Medical Vault | Patient has ≥1 vault record → page should render. Actually: `StreamlitDuplicateElementKey: ... key='text_<record_id>'`. Each record renders in "All" **and** its own type tab with the same `text_`/`dl_`/`del_` keys | Widget keys now include the filter-tab index | `test_apptest_pages.py::test_patient_view_survives_vault_records_in_every_tab` |
| D2 | wrong data (live mode broken) | RAG index, Rebuild FAISS, live LLM answer | `pip install -r requirements.txt` pulls langchain 1.x, which has no `langchain.schema` / `langchain.text_splitter`. Rebuild → `No module named 'langchain.schema'` (reproduced on main). Patient context silently empty. In OpenAI mode the chat answer becomes `[LLM Error: No module named 'langchain.schema']` | Import from `langchain_core.*` / `langchain_text_splitters` (valid in 0.2+ and 1.x) | `test_langchain_compat.py` (3 tests; legacy modules hidden) |
| D3 | wrong data | Memory & Logs → Agent Traces, Scenario Tester memory panel | Run any agent query → traces should show plan, steps and response. Actually: "Total Plan Steps 0", "Avg Steps 0.0", empty lists, blank preview, empty Short-term turns. The page read keys the logger never writes (`plan_steps`/`execution_steps`/`response`/`short_term`) | Reader now uses `plan`/`steps`/`final_response`/`short_term_history`. Stored schema unchanged | `test_memory_logs_trace_shows_plan_steps_and_response`, `test_scenario_tester_shows_short_term_memory` |
| D4 | wrong data | Memory & Logs → Scenario Tester | Pick any Quick Scenario → the Query box should fill. Actually it stays empty, and Run says "Enter a query first." A keyed `text_area` ignores changes to `value=` | `on_change` writes the preset into the widget's session-state slot | `test_scenario_preset_fills_query` |
| D5 | wrong data | Patient View → AI Assistant samples; Memory & Logs presets | "Summarize <patient>'s medical history" and "What medications is <patient> currently on?" should read the EHR. Actually: routed to web search (offline reply: "no relevant data was found") | Two narrow planner patterns. General medical questions still go to search | `test_planner.py` (8 tests) |
| D6 | cosmetic | Patient View: Book, Cancel, Save Record, Vault Upload/Delete, sidebar Agent Plan | Each action should confirm. Actually `st.success()` is followed by `st.rerun()`, so nothing is ever shown. The sidebar plan vanishes the same way | One-shot session-state message under the title. Last agent run kept in session state and drawn in the sidebar | `test_booking_and_cancel_confirmations_survive_rerun`, `test_add_record_confirmation_survives_rerun`, `test_vault_delete_confirmation_survives_rerun`, `test_agent_plan_stays_in_sidebar_after_rerun` |
| D7 | cosmetic | Patient View → Appointments | Specialization list showed "Cardiologist" twice | Duplicate removed | `test_specialization_options_are_unique` |
| D8 | cosmetic | EHR history text, RAG docs | P004 has `allergies: []` → expected "Allergies: None", got a blank "Allergies:" | `get('allergies') or ['None']` | `test_ehr_text.py` (2 tests) |
| D9 | hygiene | Test suite | `pytest` appended about 35 synthetic rows to the real `logs/tool_logs.json`, which the dashboards display. Only eval logs were isolated | `conftest.py` also redirects the tool log and agent traces per test | `test_log_isolation.py` |
| D10 | hygiene | Repo | There was no `.gitignore`. Runtime `uploads/` (vault files), `logs/`, `data/medical_records.json`, `.env` and `__pycache__` were one `git add -A` away from this **public** repo | App-level `.gitignore` | `test_gitignore.py` (5 tests) |

### Reported, not fixed

| ID | Sev | Issue | Why not fixed here | Suggested approach |
|---|---|---|---|---|
| R1 | wrong data (**high impact for the demo**) | Every seeded doctor slot is dated 2026-05-09 to 05-15, all before today (2026-10-29). On main, "Search Doctors" finds nothing for any specialty, booking can't be reached, and every Doctor View Availability tab says "No future slots configured." | This is seed data, and `data-depth-mediassist` is rewriting the data files in parallel. Editing the same JSON here would conflict and might undo that work | Data-depth should seed future slots, or have the app generate slots relative to `date.today()`. Re-run `tests/test_apptest_pages.py` after it lands. The tests already move slot dates forward in their tmp copy |
| R2 | wrong data | Seeded appointments A001 (D001 2026-05-10 09:00) and A002 (D003 2026-05-09 14:00) are `Confirmed`, but their slots are `booked: false`. Doctor View shows them as available, and a second patient could book the same slot | Seed data, same reason as R1 | Data-depth: set `booked: true` on slots held by Confirmed appointments. Optionally add a seed-consistency test |
| R3 | cosmetic / future crash | Streamlit 1.66 prints "`use_container_width` will be removed after 2025-12-31" about 15 times per page. It still works today | Moving to `width=` needs Streamlit ≥ ~1.46, but `requirements.txt` allows ≥1.32. Changing the floor is a dependency decision | Raise the floor to `streamlit>=1.46`, then replace with `width="stretch"`. Do this before Streamlit actually removes the parameter |
| R4 | low | `book_appointment()` accepts a past-dated slot if it exists | The UI only offers future slots, so users can't reach this | Reject `date_str < today` inside `book_appointment` |
| R5 | environment note | Medical search uses Wikipedia/DuckDuckGo over the network. With no internet, search intents fail cleanly ("no relevant data"). The README's "Mock Mode — full UI works" only means no **API key** is needed; internet still is | Not a code defect | Clarify the README wording, or add an offline canned-answer fallback (that's a product call) |

### Questions for Kiran (design, not bugs — behaviour left unchanged)

1. **Chat across patient switch:** in Patient View, chat history and agent memory carry over when you pick another patient, so patient A's conversation shows under patient B. Should chat be per-patient, or cleared on switch?
2. **Vault search shows only a count:** "Found N matching records" appears, but the matches aren't listed (the record list below ignores the search). Should search filter the list?
3. **Specialist mapping:** "lung", "asthma" and "pulmonolog" map to Neurologist, and there is no Pulmonologist in the data. "Endocrinologist" is in the dropdown with no doctor behind it. Intended, or should data-depth add those specialties?
4. **Scenario "Check medications" with Patient Context = None:** the query names Rajesh Kumar, but the agent doesn't pull the name out of the query text, so it answers "No patient identified." Should the agent resolve names from the query?

## AppTest evidence

- **Plain loads.** `AppTest.from_file(...).run()` on each page:

  ```
  app.py                      exceptions=0
  pages/1_Patient_View.py     exceptions=0
  pages/2_Doctor_View.py      exceptions=0
  pages/3_Admin_Dashboard.py  exceptions=0
  pages/4_Memory_Logs.py      exceptions=0
  ```

  The `st.error` badges on Patient View are allergy chips, which is intended.

- **Flow sweep** (scratch copy of the app, latest deps), run twice:
  - with the seed dates as they are;
  - with slot dates moved +184 days, so booking can be exercised.
- **Interactions covered:**
  - **Patient View:** every patient; every specialty search; Book with a 3,000-character reason; Cancel; all 4 sample prompts; chat input (including empty); Clear Chat; Add Record (empty and valid, with a 500-character diagnosis); vault with one record of each type; vault search; vault delete.
  - **Doctor View:** every doctor; Load Full History for every patient.
  - **Memory & Logs:** traces; decompose (default and empty); every preset scenario with a patient context; Reset.
  - **Admin:** eval for every module, plus eval with the live agent; Live Tool Test (4 tools × 3 inputs, including empty and invalid); Clear Tool Logs; Clear Eval Logs; Rebuild FAISS; reload of every page.
- **Before (main):** `TOTAL EXCEPTIONS: 1`, which was D1, the vault duplicate key. Sample evidence:
  - Memory & Logs metrics: `Total Plan Steps 0`, `Avg Steps/Session 0.0`
  - Every scenario preset: `query=''`, warning "Enter a query first."
  - After Book: `success: []`
- **After (branch):** `TOTAL EXCEPTIONS: 0` in both runs. Sample evidence:
  - Memory & Logs metrics: `Total Plan Steps 5`, `Avg Steps/Session 2.0`
  - Presets fill the Query box
  - After Book: `success: ['Appointment booked! Rajesh Kumar with Dr. Sunanda Rao (Cardiologist) on 2026-11-09 …']`
  - Rebuild FAISS: "Vector store rebuilt with 11 chunks." (on langchain 1.4.7; on main this errored)
- **Expected error text in the sweep:**
  - `HTTPConnectionPool(host='en.wikipedia.org' …)` from the Live Tool Test: there is no internet in the sandbox (R5), and it's handled.
  - "Patient  not found." for empty input: correct validation.

## Files changed

- `pages/1_Patient_View.py`: D1, D6, D7
- `pages/4_Memory_Logs.py`: D3, D4
- `agents/planner.py`: D5
- `agents/healthcare_agent.py`, `tools/rag_tool.py`: D2 (`rag_tool.py` also D8)
- `tools/ehr_tool.py`: D8
- `tests/conftest.py`: D9
- `.gitignore`: D10
- New tests:
  - `tests/test_apptest_pages.py`
  - `tests/test_langchain_compat.py`
  - `tests/test_planner.py`
  - `tests/test_ehr_text.py`
  - `tests/test_log_isolation.py`
  - `tests/test_gitignore.py`
- **Architecture:** no change to structure or data flow, so no diagram update.

## Cloud-credit burn (for the Infra ledger)

- **Route:** one Claude Code cloud session against `saskllc-blip/public`, started 2026-10-29 22:02 UTC.
- **Duration:** about 25 minutes of wall-clock time for the work in this report.
- **What used compute:** two throwaway virtualenvs and repeated AppTest sweeps. No other paid services were used: no OpenAI calls, and the test suite structurally blocks network access and keys.
- **Dollar figure:** **not visible from inside the session.** The session metadata only reports `rateLimitType: ccr_promotional`, resetting 2026-11-05 00:00 UTC. Infra should read the actual credit drawn for this session from the claude.ai usage page. I haven't estimated it here, to avoid putting a made-up number in the ledger.
