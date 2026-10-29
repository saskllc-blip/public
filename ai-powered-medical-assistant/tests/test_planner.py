"""Planner routing for the prompts the UI itself offers (Patient View sample
prompts and Memory & Logs scenario presets)."""
import pytest

from agents.planner import classify_intents

EHR_PROMPTS = [
    "Summarize Rajesh Kumar's medical history",                 # Patient View sample
    "What medications is Rajesh Kumar currently on?",            # Patient View sample
    "Summarize the complete medical history for patient P001",  # scenario preset
    "What medications is Rajesh Kumar currently taking?",       # scenario preset
]

SEARCH_PROMPTS = [
    "What are the latest treatments for chronic kidney disease?",
    "Tell me about rheumatoid arthritis symptoms and treatment",
    "What is the current research on lupus treatment?",
]


@pytest.mark.parametrize("prompt", EHR_PROMPTS)
def test_patient_record_prompts_route_to_medical_history(prompt):
    intents = classify_intents(prompt)
    assert "get_medical_history" in intents
    assert "search_medical_info" not in intents


@pytest.mark.parametrize("prompt", SEARCH_PROMPTS)
def test_general_medical_questions_still_route_to_search(prompt):
    assert classify_intents(prompt) == ["search_medical_info"]


def test_booking_prompt_unchanged():
    assert classify_intents("Book a nephrologist appointment for my father") == ["book_appointment"]
