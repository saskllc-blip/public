"""
Streamlit AppTest runs of every view with the full visit history loaded.
Patient View and Doctor View are walked through EVERY patient / doctor,
since duplicate-widget-key crashes only show up on the record that repeats.
"""
import json
import os

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest

import config

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 120


@pytest.fixture(autouse=True)
def isolated_runtime_logs(tmp_path, monkeypatch):
    """Views log every tool call; keep the app's real logs untouched."""
    monkeypatch.setattr(config, "TOOL_LOGS_FILE", str(tmp_path / "tool_logs.json"))
    monkeypatch.setattr(config, "AGENT_TRACES_FILE", str(tmp_path / "agent_traces.json"))


def _app(script):
    return AppTest.from_file(os.path.join(APP_DIR, script), default_timeout=TIMEOUT)


def _visits():
    with open(config.VISIT_HISTORY_FILE) as f:
        return json.load(f)["visits"]


def _assert_clean(at, where):
    assert not at.exception, f"{where}: {[e.message for e in at.exception]}"


@pytest.mark.parametrize("script", ["app.py", "pages/3_Admin_Dashboard.py",
                                    "pages/4_Memory_Logs.py"])
def test_other_views_render_without_exceptions(script):
    _assert_clean(_app(script).run(), script)


def test_patient_view_renders_full_history_for_every_patient():
    visits = _visits()
    at = _app("pages/1_Patient_View.py").run()
    _assert_clean(at, "Patient View initial")
    for label in at.selectbox[0].options:
        at.selectbox[0].set_value(label).run()
        _assert_clean(at, f"Patient View {label}")
        pid = label.split("ID: ")[1].rstrip(")")
        expected = sum(1 for v in visits if v["patient_id"] == pid)
        visit_tables = [df for df in at.dataframe if "Complaint" in df.value.columns]
        assert len(visit_tables) == 1
        assert len(visit_tables[0].value) == expected
        assert any(f"{expected} past visits" in m.value for m in at.markdown)


def test_doctor_view_renders_visit_history_for_every_doctor():
    visits = _visits()
    at = _app("pages/2_Doctor_View.py").run()
    _assert_clean(at, "Doctor View initial")
    for label in at.selectbox[0].options:
        at.selectbox[0].set_value(label).run()
        _assert_clean(at, f"Doctor View {label}")
        name = label.split(" — ")[0]
        expected = sum(1 for v in visits if v["doctor_name"] == name)
        tables = [df for df in at.dataframe if "Diagnosis" in df.value.columns]
        if expected:
            assert len(tables) == 1 and len(tables[0].value) == expected
        else:
            assert not tables


def test_doctor_view_full_history_lookup_includes_visit_timeline():
    at = _app("pages/2_Doctor_View.py").run()
    for label in at.selectbox[1].options:
        at.selectbox[1].set_value(label).run()
        at.button[0].click().run()
        _assert_clean(at, f"Doctor View lookup {label}")
        assert any("Visit Timeline" in c.value for c in at.code)
