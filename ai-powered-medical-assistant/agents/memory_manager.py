"""
Memory Manager — two-tier memory:
  Short-term : sliding conversation window (configurable size)
  Long-term  : patient context retrieved from FAISS / RAG
"""
import os, sys
from collections import deque
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class MemoryManager:

    def __init__(self, window_size: int = config.MEMORY_WINDOW):
        self.window_size       = window_size
        self._short_term: deque = deque(maxlen=window_size)
        self._patient_context: Dict[str, str] = {}
        self._active_patient: Optional[str]   = None
        self._session_facts:  List[str]        = []

    # ── Short-term ────────────────────────────────────────────────────────────
    def add_turn(self, role: str, content: str):
        self._short_term.append({"role": role, "content": content})

    def get_short_term_history(self) -> List[Dict]:
        return list(self._short_term)

    def format_history_for_prompt(self) -> str:
        if not self._short_term:
            return "No prior conversation."
        return "\n".join(
            f"{'User' if t['role']=='user' else 'Assistant'}: {t['content']}"
            for t in self._short_term)

    def clear_short_term(self):
        self._short_term.clear()

    # ── Patient context ───────────────────────────────────────────────────────
    def set_active_patient(self, pid: str):   self._active_patient = pid
    def get_active_patient(self) -> Optional[str]: return self._active_patient

    def store_patient_context(self, pid: str, ctx: str):
        self._patient_context[pid] = ctx

    def get_patient_context(self, pid: Optional[str] = None) -> str:
        key = pid or self._active_patient
        return self._patient_context.get(key, "No patient context available.")

    # ── Session facts ─────────────────────────────────────────────────────────
    def add_fact(self, fact: str):
        if fact not in self._session_facts:
            self._session_facts.append(fact)

    def get_facts(self) -> List[str]: return list(self._session_facts)

    def format_facts_for_prompt(self) -> str:
        return "\n".join(f"- {f}" for f in self._session_facts) if self._session_facts else ""

    # ── Full context prompt ───────────────────────────────────────────────────
    def build_context_prompt(self, pid: Optional[str] = None) -> str:
        sections = []
        ctx = self.get_patient_context(pid)
        if ctx != "No patient context available.":
            sections.append(f"=== Patient Medical Context ===\n{ctx}")
        facts = self.format_facts_for_prompt()
        if facts:
            sections.append(f"=== Session Facts ===\n{facts}")
        hist = self.format_history_for_prompt()
        if hist != "No prior conversation.":
            sections.append(f"=== Recent Conversation ===\n{hist}")
        return "\n\n".join(sections)

    # ── Snapshot for UI ───────────────────────────────────────────────────────
    def get_memory_snapshot(self) -> Dict[str, Any]:
        return {
            "active_patient_id":       self._active_patient,
            "short_term_turns":        len(self._short_term),
            "short_term_history":      list(self._short_term),
            "patient_contexts_loaded": list(self._patient_context.keys()),
            "session_facts":           self._session_facts,
        }
