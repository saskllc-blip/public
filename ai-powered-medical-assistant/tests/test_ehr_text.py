"""Patient summary text for a patient with no recorded allergies (P004 in
the synthetic seed data has allergies: [])."""
from tools.ehr_tool import get_medical_history
from tools.rag_tool import _build_docs


def test_history_text_says_none_for_empty_allergies():
    text = get_medical_history("P004")["history_text"]
    assert "Allergies: None\n" in text


def test_rag_docs_say_none_for_empty_allergies():
    p004 = [d.page_content for d in _build_docs() if d.metadata["patient_id"] == "P004"]
    assert any("Allergies: None\n" in c for c in p004)
