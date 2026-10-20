"""
Appointment Tool — simulates a Doctor Schedule API.
Supports: listing available slots, booking, and cancellation.
"""
import json, os, sys, time, uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import log_tool_call


def _load(path):
    with open(path) as f: return json.load(f)
def _save(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)


def get_available_slots(specialization: str) -> Dict[str, Any]:
    """Return doctors matching the specialization with their free upcoming slots."""
    start = time.time()
    try:
        doctors = _load(config.DOCTORS_FILE)
        today = date.today().isoformat()
        matched = []
        for doc in doctors:
            if specialization.lower() in doc["specialization"].lower():
                free = [s for s in doc.get("available_slots", [])
                        if not s["booked"] and s["date"] >= today]
                if free:
                    matched.append({
                        "doctor_id":        doc["doctor_id"],
                        "name":             doc["name"],
                        "specialization":   doc["specialization"],
                        "hospital":         doc["hospital"],
                        "rating":           doc["rating"],
                        "experience_years": doc["experience_years"],
                        "consultation_fee": doc["consultation_fee"],
                        "available_slots":  free[:6],
                    })
        result = {"success": True, "specialization_searched": specialization,
                  "doctors_found": len(matched), "doctors": matched}
        log_tool_call("get_available_slots", specialization, result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("get_available_slots", specialization, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def book_appointment(patient_id: str, doctor_id: str,
                     date_str: str, time_str: str, reason: str) -> Dict[str, Any]:
    """Book a specific slot for a patient."""
    start = time.time()
    try:
        doctors      = _load(config.DOCTORS_FILE)
        appointments = _load(config.APPOINTMENTS_FILE)
        patients     = _load(config.PATIENTS_FILE)

        doc     = next((d for d in doctors  if d["doctor_id"]  == doctor_id),  None)
        patient = next((p for p in patients if p["patient_id"] == patient_id), None)
        if not doc:     raise ValueError(f"Doctor {doctor_id} not found.")
        if not patient: raise ValueError(f"Patient {patient_id} not found.")

        slot_found = False
        for slot in doc.get("available_slots", []):
            if slot["date"] == date_str and slot["time"] == time_str:
                if slot["booked"]: raise ValueError(f"Slot {date_str} {time_str} is already booked.")
                slot["booked"] = True
                slot_found = True
                break
        if not slot_found:
            raise ValueError(f"Slot {date_str} {time_str} not found for {doc['name']}.")

        appt_id = f"A{str(uuid.uuid4())[:6].upper()}"
        new_appt = {
            "appointment_id": appt_id, "patient_id": patient_id,
            "patient_name": patient["name"], "doctor_id": doctor_id,
            "doctor_name": doc["name"], "specialization": doc["specialization"],
            "date": date_str, "time": time_str, "status": "Confirmed",
            "reason": reason, "booked_at": datetime.now().isoformat(), "notes": "",
        }
        appointments.append(new_appt)

        for p in patients:
            if p["patient_id"] == patient_id:
                p["upcoming_appointment"] = {
                    "appointment_id": appt_id, "doctor": doc["name"],
                    "date": date_str, "time": time_str}
                break

        _save(config.DOCTORS_FILE, doctors)
        _save(config.APPOINTMENTS_FILE, appointments)
        _save(config.PATIENTS_FILE, patients)

        result = {"success": True, "appointment_id": appt_id,
                  "message": (f"✅ Appointment booked! {patient['name']} with "
                              f"{doc['name']} ({doc['specialization']}) on "
                              f"{date_str} at {time_str}. Hospital: {doc['hospital']}. "
                              f"Fee: ₹{doc['consultation_fee']}."),
                  "appointment": new_appt}
        log_tool_call("book_appointment",
                      {"patient_id": patient_id, "doctor_id": doctor_id, "date": date_str},
                      result, True, duration_ms=(time.time()-start)*1000,
                      patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("book_appointment",
                      {"patient_id": patient_id, "doctor_id": doctor_id},
                      str(e), False, error=str(e),
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return {"success": False, "error": str(e)}


def cancel_appointment(appointment_id: str) -> Dict[str, Any]:
    """Cancel an existing appointment and free the slot."""
    start = time.time()
    try:
        appointments = _load(config.APPOINTMENTS_FILE)
        doctors      = _load(config.DOCTORS_FILE)
        patients     = _load(config.PATIENTS_FILE)

        appt = next((a for a in appointments if a["appointment_id"] == appointment_id), None)
        if not appt: raise ValueError(f"Appointment {appointment_id} not found.")
        if appt["status"] == "Cancelled": raise ValueError("Already cancelled.")

        for doc in doctors:
            if doc["doctor_id"] == appt["doctor_id"]:
                for slot in doc.get("available_slots", []):
                    if slot["date"] == appt["date"] and slot["time"] == appt["time"]:
                        slot["booked"] = False
                        break

        appt["status"] = "Cancelled"
        for p in patients:
            if p["patient_id"] == appt["patient_id"]:
                ua = p.get("upcoming_appointment")
                if ua and ua.get("appointment_id") == appointment_id:
                    p["upcoming_appointment"] = None

        _save(config.DOCTORS_FILE, doctors)
        _save(config.APPOINTMENTS_FILE, appointments)
        _save(config.PATIENTS_FILE, patients)

        result = {"success": True, "message": f"Appointment {appointment_id} cancelled."}
        log_tool_call("cancel_appointment", appointment_id, result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("cancel_appointment", appointment_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def get_appointments_by_patient(patient_id: str) -> Dict[str, Any]:
    start = time.time()
    try:
        appts = [a for a in _load(config.APPOINTMENTS_FILE) if a["patient_id"] == patient_id]
        result = {"success": True, "patient_id": patient_id,
                  "appointments": appts, "total": len(appts)}
        log_tool_call("get_appointments_by_patient", patient_id, result, True,
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("get_appointments_by_patient", patient_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def get_appointments_by_doctor(doctor_id: str) -> Dict[str, Any]:
    start = time.time()
    try:
        appts = [a for a in _load(config.APPOINTMENTS_FILE) if a["doctor_id"] == doctor_id]
        result = {"success": True, "doctor_id": doctor_id, "appointments": appts}
        log_tool_call("get_appointments_by_doctor", doctor_id, result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("get_appointments_by_doctor", doctor_id, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}
