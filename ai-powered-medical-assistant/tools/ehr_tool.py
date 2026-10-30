"""
EHR Tool — Electronic Health Record management.
Read, add, and update patient records.
"""
import json, os, sys, time
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import log_tool_call
from tools.visit_history_tool import _load as _load_visit_history, format_visit_timeline


def _load():
    with open(config.PATIENTS_FILE) as f: return json.load(f)
def _save(patients):
    with open(config.PATIENTS_FILE, "w") as f: json.dump(patients, f, indent=2)


def get_patient_by_id(patient_id: str) -> Dict[str, Any]:
    start = time.time()
    try:
        patients = _load()
        p = next((x for x in patients if x["patient_id"] == patient_id), None)
        if not p: raise ValueError(f"Patient {patient_id} not found.")
        result = {"success": True, "patient": p}
        log_tool_call("get_patient_by_id", patient_id, "found", True,
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("get_patient_by_id", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def search_patient_by_name(name: str) -> Dict[str, Any]:
    start = time.time()
    try:
        patients = _load()
        matches = [p for p in patients if name.lower() in p["name"].lower()]
        result = {"success": True, "query": name, "patients_found": len(matches),
                  "patients": [{"patient_id": p["patient_id"], "name": p["name"],
                                "age": p["age"], "gender": p["gender"],
                                "last_visit": p.get("last_visit","N/A")} for p in matches]}
        log_tool_call("search_patient_by_name", name, result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("search_patient_by_name", name, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def get_medical_history(patient_id: str) -> Dict[str, Any]:
    start = time.time()
    try:
        patients = _load()
        p = next((x for x in patients if x["patient_id"] == patient_id), None)
        if not p: raise ValueError(f"Patient {patient_id} not found.")

        history = p.get("medical_history", [])
        text = (f"Patient: {p['name']}, Age: {p['age']}, Gender: {p['gender']}, "
                f"Blood Group: {p['blood_group']}\n\n"
                f"Allergies: {', '.join(p.get('allergies') or ['None'])}\n\n"
                "Current Medications:\n")
        for m in p.get("current_medications", []):
            text += f"  - {m}\n"
        text += "\nMedical History (most recent first):\n"
        for entry in reversed(history):
            text += (f"\n  [{entry['date']}] {entry['diagnosis']}\n"
                     f"  Doctor: {entry['doctor']}\n"
                     f"  Treatment: {entry['treatment']}\n"
                     f"  Notes: {entry['notes']}\n")

        visits = [v for v in _load_visit_history()["visits"] if v["patient_id"] == patient_id]
        if visits:
            text += (f"\nVisit Timeline ({len(visits)} past visits, most recent first):\n"
                     + format_visit_timeline(visits) + "\n")

        result = {"success": True, "patient_id": patient_id,
                  "patient_name": p["name"], "history_text": text,
                  "history_entries": len(history),
                  "visit_count": len(visits),
                  "medications_count": len(p.get("current_medications",[]))}
        log_tool_call("get_medical_history", patient_id, "retrieved", True,
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("get_medical_history", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def add_medical_record(patient_id: str, diagnosis: str, doctor: str,
                       treatment: str, notes: str,
                       date_str: Optional[str] = None) -> Dict[str, Any]:
    start = time.time()
    try:
        patients = _load()
        p = next((x for x in patients if x["patient_id"] == patient_id), None)
        if not p: raise ValueError(f"Patient {patient_id} not found.")

        rec_date = date_str or datetime.now().strftime("%Y-%m-%d")
        record   = {"date": rec_date, "diagnosis": diagnosis, "doctor": doctor,
                    "treatment": treatment, "notes": notes}
        p.setdefault("medical_history", []).append(record)
        p["last_visit"] = rec_date
        _save(patients)

        result = {"success": True,
                  "message": f"Record added for {p['name']}: '{diagnosis}' on {rec_date}.",
                  "record": record}
        log_tool_call("add_medical_record", patient_id, result, True,
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("add_medical_record", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def update_medications(patient_id: str, medications: List[str]) -> Dict[str, Any]:
    start = time.time()
    try:
        patients = _load()
        p = next((x for x in patients if x["patient_id"] == patient_id), None)
        if not p: raise ValueError(f"Patient {patient_id} not found.")
        old = p.get("current_medications", [])
        p["current_medications"] = medications
        _save(patients)
        result = {"success": True, "message": f"Medications updated for {p['name']}.",
                  "old_medications": old, "new_medications": medications}
        log_tool_call("update_medications", patient_id, result, True,
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("update_medications", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def get_all_patients() -> Dict[str, Any]:
    start = time.time()
    try:
        patients = _load()
        summary = [{
            "patient_id":            p["patient_id"],
            "name":                  p["name"],
            "age":                   p["age"],
            "gender":                p["gender"],
            "blood_group":           p["blood_group"],
            "last_visit":            p.get("last_visit","N/A"),
            "conditions":            [h["diagnosis"] for h in p.get("medical_history",[])],
            "upcoming_appointment":  p.get("upcoming_appointment"),
        } for p in patients]
        result = {"success": True, "total": len(summary), "patients": summary}
        log_tool_call("get_all_patients", "all", result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("get_all_patients", "all", str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}
