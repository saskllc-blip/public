> **Showcase note:** This is Kiran Keshava's capstone for the Purdue University Applied Generative AI Specialization — *Agentic Healthcare Assistant for Medical Task Automation*. All patient data is synthetic course data. Running it live requires an `OPENAI_API_KEY` (for example via Streamlit secrets).

# MediAssist — AI-Powered Healthcare Assistant

A multi-agent healthcare assistant demo (appointment booking, EHR lookup,
medical web search, RAG over a patient knowledge base, **medical record vault
with OCR**) built with LangChain, FAISS, and Streamlit — paired with a
domain-agnostic LLM-as-judge evaluation harness for scoring what any of those
agents actually produce.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

No API key required. Without `OPENAI_API_KEY` set, the app runs in **Mock
Mode**: every feature works end to end against rule-based responses instead
of a live model. Copy `.env.example` to `.env` and set a real key to switch
to LLM Mode.

## Run the eval-harness tests

```bash
pytest
```

14 tests, well under a second, and — this is deliberate, not a limitation —
**the suite cannot reach the network or bill an API key even if one is
exported in your shell.** `tests/conftest.py` clears `OPENAI_API_KEY` before
every test runs, session-wide. A portfolio artifact whose test suite could
silently charge a stranger who clones it and runs `pytest` is not
demonstrating good judgement; a suite that structurally cannot is.

## The design decision worth reading: score provenance

The evaluation harness (`evaluation/evaluator.py`) scores QA-style
question/reference/generated triples two ways: a token-overlap heuristic
(always available) and an LLM judge scored against a versioned, swappable
rubric (`evaluation/evaluator.py::DEFAULT_RUBRIC`, `load_rubric()`).

Every result states:
- **which scorer** actually produced it (`heuristic_token_f1` or `llm_judge`)
- **which model**, if a judge was used
- **which rubric version** it was scored against
- **why it degraded**, if the judge path failed and it fell back to the
  heuristic

That last point exists because an early version of this file did not have
it: the judge path could fail silently — a bad API key, a dependency version
bump breaking an import, a malformed response — and return a heuristic
number that looked identical to a real judge verdict. A score you cannot
attribute to a scorer, a model, and a rubric version is worse than no score
at all, because it looks trustworthy while being wrong. Provenance is
recorded both in the live result you see after a run (`run_evaluation()`)
and in the persisted history (`logs/eval_logs.json`, via
`utils/logger.py::log_eval_result()`) — a run's provenance living only on
screen and not in its own log was a real bug here, fixed by making the two
share one schema (see `EVAL_LOG_SCHEMA_VERSION` in `utils/logger.py`).

The eval harness itself is domain-agnostic: `evaluation/evaluator.py`'s
bundled medical QA pairs (`SAMPLE_QA_PAIRS`) are a sample dataset, not a
ceiling. `load_cases()` loads any domain's question/reference/generated
triples from JSON or CSV, and `load_rubric()` loads any rubric — swap both
and nothing else in the module needs to change.

## Architecture

```
├── app.py                    ← Home screen, navigation
├── pages/
│   ├── 1_Patient_View.py     ← Medical history, AI chat, appointments, vault
│   ├── 2_Doctor_View.py
│   ├── 3_Admin_Dashboard.py  ← Eval results, run history, metrics
│   └── 4_Memory_Logs.py
├── agents/
│   ├── healthcare_agent.py   ← Main orchestrator
│   ├── planner.py            ← Intent classifier
│   └── memory_manager.py     ← Two-tier memory
├── tools/
│   ├── appointment_tool.py
│   ├── ehr_tool.py
│   ├── medical_search_tool.py
│   ├── medical_vault_tool.py ← 🆕 File upload, OCR extraction, vault management
│   └── rag_tool.py           ← FAISS RAG
├── evaluation/
│   └── evaluator.py          ← QA evaluation, LLM-as-judge, provenance
├── utils/
│   └── logger.py             ← Persisted logging (tool calls, traces, evals)
├── tests/
│   ├── conftest.py           ← Structural no-network-by-default fixture
│   ├── test_evaluator.py
│   └── test_medical_vault.py ← 🆕 Medical vault tests
├── data/                     ← Sample patient/doctor/appointment records
│                                bundled for local demo use
├── uploads/                  ← 🆕 Medical record files (gitignored)
├── docs/
│   └── MEDICAL_VAULT.md      ← 🆕 Vault documentation
└── logs/                     ← Auto-created at runtime
```

Built as a Purdue Applied Generative AI Specialisation capstone project.
