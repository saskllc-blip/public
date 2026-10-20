"""
Healthcare Agent — main orchestrator.

Pipeline: Planner → Tool Dispatcher → Memory update → LLM synthesis (or mock).

Modes:
  • OpenAI mode  – real LLM calls when OPENAI_API_KEY is set in .env
  • Mock mode    – deterministic structured responses (demo / no API key)
"""
import os, re, sys, time, uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.memory_manager import MemoryManager
from agents.planner import decompose_query, build_plan_text
from tools.appointment_tool import get_available_slots, book_appointment, get_appointments_by_patient
from tools.ehr_tool import get_medical_history, search_patient_by_name, get_patient_by_id, add_medical_record
from tools.medical_search_tool import search_medical_info, search_treatment_options
from tools.rag_tool import retrieve_patient_context
from utils.logger import log_agent_trace

SYSTEM_PROMPT = """You are MediAssist, an AI-powered agentic healthcare assistant.
You help patients and medical staff with appointment booking, medical history retrieval,
patient record management, and medical information searches.
Always be accurate, empathetic, and professional.
Base responses strictly on retrieved data — never fabricate medical information.
"""

# ── LLM helper ────────────────────────────────────────────────────────────────
def _get_llm():
    key = config.OPENAI_API_KEY
    if not key or key == "your_openai_api_key_here":
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=config.LLM_MODEL,
                          temperature=config.LLM_TEMPERATURE,
                          api_key=key)
    except Exception:
        return None


def _llm_call(prompt: str) -> Optional[str]:
    llm = _get_llm()
    if not llm:
        return None
    try:
        from langchain.schema import HumanMessage, SystemMessage
        resp = llm.invoke([SystemMessage(content=SYSTEM_PROMPT),
                           HumanMessage(content=prompt)])
        return resp.content
    except Exception as e:
        return f"[LLM Error: {e}]"


# ── Mock response builder ─────────────────────────────────────────────────────
def _mock_response(tool_results: List[Dict],
                   user_input: str,
                   plan: List[Tuple[str, str]]) -> str:
    parts = [f"### 🏥 MediAssist Response\n*Query: \"{user_input[:100]}\"*\n"]
    for intent, _ in plan:
        tr = next((r for r in tool_results if r.get("intent") == intent), None)
        if not tr:
            continue
        data = tr.get("data", {})

        if intent == "get_medical_history" and data.get("success"):
            parts.append(f"#### 📋 Medical History\n```\n{data.get('history_text','')}\n```")

        elif intent == "book_appointment":
            if data.get("success") and data.get("doctors"):
                parts.append("#### 🩺 Available Doctors & Slots")
                for doc in data["doctors"][:2]:
                    slot_strs = ", ".join(
                        f"{s['date']} {s['time']}"
                        for s in doc["available_slots"][:3])
                    parts.append(
                        f"**{doc['name']}** ({doc['specialization']})  \n"
                        f"🏥 {doc['hospital']} | ⭐ {doc['rating']} | "
                        f"₹{doc['consultation_fee']}  \n"
                        f"📅 Available: {slot_strs}")
            elif data.get("success") and data.get("message"):
                parts.append(f"#### ✅ Booking\n{data['message']}")
            else:
                parts.append(f"#### ⚠️ Booking\n{data.get('error','No slots found.')}")

        elif intent == "search_medical_info" and data.get("success"):
            summary = data.get("summary", "")
            parts.append(
                f"#### 🔍 Medical Information\n"
                f"*Source: {data.get('source','Web')}*\n\n"
                + summary[:900] + ("..." if len(summary) > 900 else ""))

        elif intent == "add_medical_record" and data.get("success"):
            parts.append(f"#### ✅ Record Updated\n{data.get('message','')}")

        elif intent == "get_patient_info" and data.get("success"):
            pts = data.get("patients", [])
            if pts:
                p = pts[0]
                parts.append(
                    f"#### 👤 Patient Found\n"
                    f"**{p['name']}** (ID: `{p['patient_id']}`) | "
                    f"Age: {p['age']} | Last Visit: {p.get('last_visit','N/A')}")

    return "\n\n".join(parts) if len(parts) > 1 else "I processed your request but no relevant data was found."


# ── Main Agent ────────────────────────────────────────────────────────────────
class HealthcareAgent:
    def __init__(self):
        self.memory     = MemoryManager()
        self.session_id = str(uuid.uuid4())[:8]
        self._steps: List[Dict] = []

    def run(self, user_input: str,
            patient_id: Optional[str] = None,
            patient_name: Optional[str] = None) -> Dict[str, Any]:
        """Full agentic pipeline: Plan → Execute → Synthesise → Memory."""
        t0 = time.time()
        self._steps = []

        # Patient context
        if patient_id:
            self.memory.set_active_patient(patient_id)
            ctx = retrieve_patient_context(user_input, patient_id)
            if ctx.get("success"):
                self.memory.store_patient_context(patient_id, ctx["context"])
        pid = patient_id or self.memory.get_active_patient()

        # Plan
        plan      = decompose_query(user_input)
        plan_text = build_plan_text(plan)
        self._step("planning", plan_text, "success")

        # Execute tools
        tool_results = []
        for intent, desc in plan:
            data = self._dispatch(intent, user_input, pid, patient_name)
            tool_results.append({"intent": intent, "desc": desc, "data": data})

        # Facts
        self._extract_facts(tool_results, pid)

        # Synthesise
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            tool_summary = "\n".join(
                f"[{tr['intent']}] {'OK' if tr['data'].get('success') else 'FAIL'}: "
                + str(tr['data'].get('history_text') or tr['data'].get('message')
                       or tr['data'].get('summary') or tr['data'].get('error',''))[:400]
                for tr in tool_results)
            prompt = (f"{self.memory.build_context_prompt(pid)}\n\n"
                      f"Tool Results:\n{tool_summary}\n\n"
                      f"User Query: {user_input}\n\n"
                      "Provide a comprehensive, helpful, empathetic response.")
            response = _llm_call(prompt) or _mock_response(tool_results, user_input, plan)
        else:
            response = _mock_response(tool_results, user_input, plan)

        # Update memory
        self.memory.add_turn("user", user_input)
        self.memory.add_turn("assistant", response[:500])

        ms = (time.time() - t0) * 1000
        log_agent_trace(self.session_id, user_input,
                        [f"{i}: {d}" for i, d in plan],
                        self._steps, response, pid)

        return {"success": True, "session_id": self.session_id,
                "response": response, "plan": plan, "plan_text": plan_text,
                "tool_results": tool_results, "steps": self._steps,
                "duration_ms": round(ms, 2), "patient_id": pid,
                "memory_snapshot": self.memory.get_memory_snapshot()}

    # ── Dispatcher ────────────────────────────────────────────────────────────
    def _dispatch(self, intent, user_input, pid, pname):
        if intent == "get_medical_history":
            if pid:
                r = get_medical_history(pid)
                self._step("tool:get_medical_history", f"PID:{pid}",
                           "success" if r.get("success") else "error")
                return r
            if pname:
                sr = search_patient_by_name(pname)
                if sr.get("success") and sr.get("patients"):
                    r = get_medical_history(sr["patients"][0]["patient_id"])
                    self._step("tool:get_medical_history", f"by name:{pname}", "success")
                    return r
            return {"success": False, "error": "No patient identified."}

        if intent == "book_appointment":
            spec = self._extract_specialist(user_input)
            if not spec:
                self._step("tool:book_appointment", "No specialist found", "error")
                return {"success": False, "error": "Could not identify specialist type."}
            slots = get_available_slots(spec)
            self._step("tool:get_available_slots", f"Searching: {spec}",
                       "success" if slots.get("success") else "error")
            if not slots.get("success") or not slots.get("doctors"):
                return {"success": False, "error": f"No {spec} doctors with free slots."}
            return {"success": True, "action": "slots_found", "specialist": spec,
                    "message": f"Found {len(slots['doctors'])} {spec} doctor(s). Select a slot.",
                    "doctors": slots["doctors"]}

        if intent == "get_patient_info":
            if pid:
                r = get_patient_by_id(pid)
                self._step("tool:get_patient_by_id", pid, "success" if r.get("success") else "error")
                return r
            if pname:
                r = search_patient_by_name(pname)
                self._step("tool:search_patient_by_name", pname, "success" if r.get("success") else "error")
                return r
            return {"success": False, "error": "No patient identifier."}

        if intent == "search_medical_info":
            topic = self._extract_topic(user_input)
            fn = (search_treatment_options if any(w in user_input.lower()
                  for w in ("treatment","latest","method","guideline"))
                  else search_medical_info)
            r = fn(topic)
            self._step("tool:search_medical_info", f"Query:{topic}",
                       "success" if r.get("success") else "error")
            return r

        if intent == "add_medical_record":
            self._step("tool:add_medical_record", "Guided via form", "info")
            return {"success": False,
                    "error": "Use the 'Add Medical Record' form in the Patient View tab."}

        return {"success": False, "error": f"Unknown intent: {intent}"}

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _step(self, tool, detail, status):
        self._steps.append({"timestamp": datetime.now().isoformat(),
                             "tool": tool, "detail": detail, "status": status})

    @staticmethod
    def _extract_specialist(text: str) -> str:
        mapping = {
            "nephrolog": "Nephrologist", "kidney": "Nephrologist",
            "cardiolog": "Cardiologist", "heart": "Cardiologist",
            "neurolog":  "Neurologist",  "brain": "Neurologist",
            "migraine":  "Neurologist",  "pulmonolog": "Neurologist",
            "asthma":    "Neurologist",  "lung": "Neurologist",
            "rheumatolog":"Rheumatologist","arthritis": "Rheumatologist",
            "endocrinolog":"Endocrinologist","thyroid":"Endocrinologist",
            "diabetes":  "General Physician","general": "General Physician",
            "physician": "General Physician","dermatolog":"Dermatologist",
            "skin":      "Dermatologist","oncolog":"Oncologist",
            "cancer":    "Oncologist",   "orthoped":"Orthopedic",
            "psychiatr": "Psychiatrist", "gynecolog":"Gynecologist",
        }
        t = text.lower()
        for kw, spec in mapping.items():
            if kw in t:
                return spec
        return ""

    @staticmethod
    def _extract_topic(text: str) -> str:
        cleaned = re.sub(
            r"\b(tell me about|what is|explain|describe|information about|"
            r"summarize|latest|recent|treatment for|how to treat|symptoms of)\b",
            "", text, flags=re.IGNORECASE).strip()
        return cleaned[:60] or text[:60]

    def _extract_facts(self, tool_results, pid):
        for tr in tool_results:
            d = tr.get("data", {})
            if d.get("success"):
                if tr["intent"] == "get_medical_history" and d.get("patient_name"):
                    self.memory.add_fact(f"Patient: {d['patient_name']} ({pid})")
                elif tr["intent"] == "book_appointment" and d.get("message"):
                    self.memory.add_fact(f"Booking: {d['message'][:80]}")
                elif tr["intent"] == "search_medical_info" and d.get("title"):
                    self.memory.add_fact(f"Searched: {d['title']}")

    def reset(self):
        self.memory.clear_short_term()
        self._steps = []
        self.session_id = str(uuid.uuid4())[:8]
