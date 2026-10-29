"""
AppTest coverage for every page, run against an isolated copy of the seeded
data so a test can book, cancel or upload without touching the real files.

Runs offline: no page load here reaches the agent's web search.
"""
import json
import os
import shutil
import uuid

import pytest
from streamlit.testing.v1 import AppTest

import config
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
    return {"data": data, "uploads": uploads}


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
