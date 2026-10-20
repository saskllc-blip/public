"""
Planner — classifies user intent and decomposes queries into ordered sub-goals.
"""
import re, os, sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


INTENT_PATTERNS = {
    "book_appointment": [
        r"\b(book|schedule|appoint|reserve|set up|arrange)\b.*\b(appointment|slot|visit|consult)\b",
        r"\b(want|need|would like)\b.*\b(doctor|specialist|physician|see a)\b",
        r"\b(nephrolog|cardiolog|neurolog|oncolog|orthoped|dermatolog|psychiatr|"
        r"pulmonolog|rheumatolog|gynecolog|endocrinolog|gastroenterolog)\b",
    ],
    "get_medical_history": [
        r"\b(history|records|past|previous)\b.*\b(medical|health|diagnosis|treatment)\b",
        r"\b(what (did|does|has)|tell me about)\b.*(patient|he|she|his|her)\b",
        r"\b(retrieve|get|show|fetch|view)\b.*\b(history|records|file|report)\b",
        r"\b(diagnos|condition|illness)\b.*(had|has|suffer|treating)\b",
    ],
    "search_medical_info": [
        r"\b(what is|explain|describe|information about|tell me about|summarize)\b.*"
        r"\b(disease|condition|syndrome|disorder|treatment|medication|drug|therapy)\b",
        r"\b(latest|recent|new|current)\b.*\b(treatment|research|guidelines|methods)\b",
        r"\b(how to treat|how is .* treated|what causes|symptoms of)\b",
    ],
    "add_medical_record": [
        r"\b(add|update|record|enter|log|document)\b.*\b(medical|health|diagnosis|record)\b",
        r"\b(new (diagnosis|condition|medication))\b",
    ],
    "get_patient_info": [
        r"\b(who is|find|search|look up)\b.*\b(patient|person)\b",
        r"\bpatient (id|number|details)\b",
    ],
}

_EXEC_ORDER = ["get_patient_info", "get_medical_history",
               "book_appointment", "add_medical_record", "search_medical_info"]


def classify_intents(user_input: str) -> List[str]:
    text = user_input.lower()
    detected = []
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text) and intent not in detected:
                detected.append(intent)
                break
    return detected or ["search_medical_info"]


def decompose_query(user_input: str) -> List[Tuple[str, str]]:
    intents = classify_intents(user_input)
    sorted_ = sorted(intents,
                     key=lambda i: _EXEC_ORDER.index(i) if i in _EXEC_ORDER else 99)
    return [(i, _desc(i)) for i in sorted_]


def _desc(intent: str) -> str:
    return {
        "get_patient_info":    "Identify and retrieve patient information",
        "get_medical_history": "Retrieve patient medical history and context",
        "book_appointment":    "Discover available slots and book appointment",
        "add_medical_record":  "Add or update patient medical record",
        "search_medical_info": "Search and summarise medical information",
    }.get(intent, intent)


def build_plan_text(sub_goals: List[Tuple[str, str]]) -> str:
    lines = ["Agent Plan:"]
    for i, (intent, desc) in enumerate(sub_goals, 1):
        lines.append(f"  {i}. [{intent}] {desc}")
    return "\n".join(lines)
