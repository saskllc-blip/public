"""
AppTest coverage for every page, run against an isolated copy of the seeded
data so a test can book, cancel or upload without touching the real files.

Runs offline: no page load here reaches the agent's web search.
"""
import json
import os
import shutil
import uuid
from datetime import date, timedelta

import pytest
from streamlit.testing.v1 import AppTest

import config
from agents import healthcare_agent
from agents.memory_manager import MemoryManager
from tools import medical_vault_tool, rag_tool
from utils.logger import log_agent_trace

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["app.py", "pages/1_Patient_View.py", "pages/2_Doctor_View.py",
         "pages/3_Admin_Dashboard.py", "pages/4_Memory_Logs.py"]


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    shutil.copytree(config.DATA_DIR, data)
    uploads = tmp_path / "uploads"
    for sub in medical_vault_tool.RECORD_TYPES.values():
        (uploads / sub).mkdir(parents=True)
    for name in ("patients", "doctors", "appointments"):
        monkeypatch.setattr(config, f"{name.upper()}_FILE", str(data / f"{name}.json"))
    monkeypatch.setattr(config, "VECTORSTORE_DIR", str(tmp_path / "vectorstore"))
    monkeypatch.setattr(medical_vault_tool, "UPLOADS_DIR", str(uploads))
    monkeypatch.setattr(medical_vault_tool, "MEDICAL_RECORDS_FILE",
                        str(data / "medical_records.json"))
    monkeypatch.setattr(config, "AGENT_TRACES_FILE", str(tmp_path / "agent_traces.json"))
    monkeypatch.setattr(rag_tool, "_vectorstore", None)
    # Keep embedding models (and any download they would trigger) out of UI tests.
    monkeypatch.setattr(rag_tool, "rebuild_vectorstore", lambda: {"success": True})
    monkeypatch.setattr(healthcare_agent, "retrieve_patient_context",
                        lambda q, pid=None: {"success": False})
    return {"data": data, "uploads": uploads}


def future_slots(env):
    """Seeded slot dates are fixed; move them past today so booking is reachable."""
    path = env["data"] / "doctors.json"
    docs = json.loads(path.read_text())
    start = date.today() + timedelta(days=7)
    for d in docs:
        for i, s in enumerate(d["available_slots"]):
            s["date"] = (start + timedelta(days=i)).isoformat()
    path.write_text(json.dumps(docs))


def run_page(page, **session):
    at = AppTest.from_file(os.path.join(APP_DIR, page), default_timeout=120)
    for k, v in session.items():
        at.session_state[k] = v
    return at.run()


def seed_vault(env, patient_id="P001"):
    records = []
    for rtype, sub in medical_vault_tool.RECORD_TYPES.items():
        rid = str(uuid.uuid4())
        path = env["uploads"] / sub / f"{rid}_synthetic.pdf"
        path.write_bytes(b"%PDF-1.4 synthetic demo record")
        records.append({
            "record_id": rid, "patient_id": patient_id, "record_type": rtype,
            "title": f"Synthetic {rtype}", "description": "synthetic demo",
            "filename": "synthetic.pdf", "file_path": str(path),
            "file_size_bytes": path.stat().st_size, "file_extension": ".pdf",
            "upload_date": "2026-10-01 10:00:00", "record_date": "2026-10-01",
            "doctor_name": "Dr. Demo", "extracted_text": "Hb 13.2 g/dL (synthetic)",
            "extraction_method": "PDF Text Extraction",
        })
    (env["data"] / "medical_records.json").write_text(json.dumps(records))
    return records


@pytest.mark.parametrize("page", PAGES)
def test_every_page_loads_without_exception(app_env, page):
    at = run_page(page)
    assert not at.exception, [e.message for e in at.exception]


def test_patient_view_survives_vault_records_in_every_tab(app_env):
    # Each record shows in "All" and in its type tab; before the fix the
    # second render reused the same widget key and crashed the page.
    seed_vault(app_env)
    at = run_page("pages/1_Patient_View.py")
    assert not at.exception, [e.message for e in at.exception]
    assert len([b for b in at.button if b.label == "🗑️ Delete"]) == 8


def test_memory_logs_trace_shows_plan_steps_and_response(app_env):
    # Same arguments HealthcareAgent.run() passes to the logger.
    log_agent_trace("abc12345", "Summarize history",
                    ["get_medical_history: Retrieve patient medical history and context"],
                    [{"timestamp": "2026-10-29T10:00:00", "tool": "tool:get_medical_history",
                      "detail": "PID:P001", "status": "success"}],
                    "Synthetic response body", "P001")
    at = run_page("pages/4_Memory_Logs.py")
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Total Plan Steps"] == "1"
    assert metrics["Avg Steps/Session"] == "1.0"
    md = [m.value for m in at.markdown]
    assert "- `get_medical_history: Retrieve patient medical history and context`" in md
    assert any("tool:get_medical_history" in m for m in md)
    assert "Synthetic response body" in md


def test_scenario_tester_shows_short_term_memory(app_env):
    mem = MemoryManager()
    mem.add_turn("user", "synthetic question")
    mem.add_turn("assistant", "synthetic answer")
    result = {"session_id": "s1", "plan": [], "steps": [], "tool_results": [],
              "response": "ok", "duration_ms": 1.0,
              "memory_snapshot": mem.get_memory_snapshot()}
    at = run_page("pages/4_Memory_Logs.py", scenario_result=result)
    md = [m.value for m in at.markdown]
    assert "👤 synthetic question" in md
    assert "🤖 synthetic answer" in md


def test_scenario_preset_fills_query(app_env):
    at = run_page("pages/4_Memory_Logs.py")
    preset = next(s for s in at.selectbox if s.label == "Quick Scenario")
    preset.select("🩺 Book cardiology appointment").run()
    query = next(t for t in at.text_area if t.label == "Query")
    assert query.value == "I need to see a cardiologist as soon as possible"
    query.input("my own edit").run()  # a typed edit is kept, not overwritten
    assert next(t for t in at.text_area if t.label == "Query").value == "my own edit"
    assert not at.exception


def test_booking_and_cancel_confirmations_survive_rerun(app_env):
    future_slots(app_env)
    at = run_page("pages/1_Patient_View.py")
    next(s for s in at.selectbox if s.label == "Specialization").select("Cardiologist").run()
    next(b for b in at.button if b.label == "Search Doctors").click().run()
    next(b for b in at.button if b.label == "✅ Book").click().run()
    assert any("Appointment booked!" in s.value for s in at.success)
    next(b for b in at.button if b.label == "Cancel" and b.key.startswith("cx_A") and b.key != "cx_A001").click().run()
    assert any("cancelled" in s.value for s in at.success)
    assert not at.exception


def test_add_record_confirmation_survives_rerun(app_env):
    at = run_page("pages/1_Patient_View.py")
    {t.label: t for t in at.text_input}["Diagnosis *"].input("Synthetic check-up")
    {t.label: t for t in at.text_input}["Doctor Name *"].input("Dr. Demo")
    {t.label: t for t in at.text_area}["Treatment *"].input("Rest")
    next(b for b in at.button if "Save Record" in b.label).click().run()
    assert any(s.value.startswith("Record added for") for s in at.success)


def test_vault_delete_confirmation_survives_rerun(app_env):
    seed_vault(app_env)
    at = run_page("pages/1_Patient_View.py")
    next(b for b in at.button if b.label == "🗑️ Delete").click().run()
    assert any("deleted successfully" in s.value for s in at.success)
    assert not at.exception


def test_agent_plan_stays_in_sidebar_after_rerun(app_env):
    at = run_page("pages/1_Patient_View.py")
    next(b for b in at.button if b.key == "sp_1").click().run()  # booking prompt, no web search
    assert "🧠 Agent Plan" in [h.value for h in at.sidebar.subheader]
    assert "✅ `book_appointment`" in [m.value for m in at.sidebar.markdown]


def test_specialization_options_are_unique(app_env):
    at = run_page("pages/1_Patient_View.py")
    opts = next(s for s in at.selectbox if s.label == "Specialization").options
    assert len(opts) == len(set(opts))
