"""
Logger — persists tool calls, agent traces, and eval results to JSON.
All data is read by the Admin Dashboard for live visualisation.
"""

import json, os, sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ── Helpers ───────────────────────────────────────────────────────────────────
def _load(path: str) -> List[Dict]:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save(path: str, data: List[Dict]) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Tool logs ─────────────────────────────────────────────────────────────────
def log_tool_call(tool_name, input_data, output_data, success,
                  error=None, duration_ms=0.0, patient_id=None):
    logs = _load(config.TOOL_LOGS_FILE)
    logs.append({
        "timestamp":   datetime.now().isoformat(),
        "tool_name":   tool_name,
        "input":       str(input_data)[:500],
        "output":      str(output_data)[:500],
        "success":     success,
        "error":       error,
        "duration_ms": round(duration_ms, 2),
        "patient_id":  patient_id,
    })
    _save(config.TOOL_LOGS_FILE, logs)

def get_tool_logs(limit=100):       return _load(config.TOOL_LOGS_FILE)[-limit:]
def clear_tool_logs():              _save(config.TOOL_LOGS_FILE, [])


# ── Agent traces ──────────────────────────────────────────────────────────────
def log_agent_trace(session_id, user_input, plan, steps, final_response, patient_id=None):
    traces = _load(config.AGENT_TRACES_FILE)
    traces.append({
        "timestamp":      datetime.now().isoformat(),
        "session_id":     session_id,
        "patient_id":     patient_id,
        "user_input":     user_input,
        "plan":           plan,
        "steps":          steps,
        "final_response": final_response[:1000],
    })
    _save(config.AGENT_TRACES_FILE, traces)

def get_agent_traces(limit=50):     return _load(config.AGENT_TRACES_FILE)[-limit:]
def clear_agent_traces():           _save(config.AGENT_TRACES_FILE, [])


# ── Eval logs ─────────────────────────────────────────────────────────────────
# schema_version history:
#   (absent) -- pre-provenance. No scorer/model/rubric fields exist at all.
#     That absence is the deliberate signal that provenance is unknown for
#     these entries. Never backfill a guess into one (e.g. stamping
#     scorer="heuristic_token_f1" because that's probably what it was --
#     "probably" is exactly the failure this schema fixes).
#   2 -- added scorer/model/rubric_version/reason/fallback_reason, but named
#     the model field "model". Four entries exist in this exact shape,
#     written while diagnosing this file's own bugs. Short-lived on purpose:
#     found within the same session by checking the persisted log against
#     run_evaluation()'s in-memory result schema, which already called the
#     same value "judge_model".
#   3 -- same fields, "model" renamed to "judge_model" to match the in-memory
#     schema exactly. A reader must check the actual schema_version value,
#     not just its presence, to know which key name to expect: `>= 3` for
#     judge_model, `== 2` for the old model name, absent for unknown.
EVAL_LOG_SCHEMA_VERSION = 3

def log_eval_result(question, expected, generated, score, grade, module,
                     scorer=None, judge_model=None, rubric_version=None,
                     reason=None, fallback_reason=None):
    # Field name matches run_evaluation()'s in-memory result dict
    # ("judge_model", set in evaluation/evaluator.py) exactly -- a persisted
    # record and the live view it was logged from must use the same key for
    # the same value, or a consumer checking one schema silently misses the
    # field under the other name. Found by checking the live log against the
    # in-memory schema rather than assuming they matched.
    evals = _load(config.EVAL_LOGS_FILE)
    evals.append({
        "schema_version": EVAL_LOG_SCHEMA_VERSION,
        "timestamp":      datetime.now().isoformat(),
        "module":         module,
        "question":       question,
        "expected":       expected[:400],
        "generated":      generated[:400],
        "score":          score,
        "grade":          grade,
        "scorer":         scorer,
        "judge_model":    judge_model,
        "rubric_version": rubric_version,
        "reason":         reason,
        "fallback_reason": fallback_reason,
    })
    _save(config.EVAL_LOGS_FILE, evals)

def get_eval_logs(limit=100):       return _load(config.EVAL_LOGS_FILE)[-limit:]
def clear_eval_logs():              _save(config.EVAL_LOGS_FILE, [])


# ── Aggregated metrics for dashboard ─────────────────────────────────────────
def get_metrics_summary() -> Dict[str, Any]:
    tool_logs   = get_tool_logs(1000)
    eval_logs   = get_eval_logs(1000)
    agent_traces= get_agent_traces(1000)

    success  = [t for t in tool_logs if t["success"]]
    fail     = [t for t in tool_logs if not t["success"]]
    counts: Dict[str, int] = {}
    for t in tool_logs:
        counts[t["tool_name"]] = counts.get(t["tool_name"], 0) + 1

    avg_dur = (sum(t["duration_ms"] for t in tool_logs) / len(tool_logs)
               if tool_logs else 0)

    scores = [e["score"] for e in eval_logs if "score" in e]
    avg_score = sum(scores) / len(scores) if scores else 0

    mod_scores: Dict[str, list] = {}
    for e in eval_logs:
        mod_scores.setdefault(e.get("module","?"), []).append(e.get("score", 0))
    mod_avg = {m: sum(v)/len(v) for m, v in mod_scores.items()}

    return {
        "total_tool_calls":      len(tool_logs),
        "successful_tool_calls": len(success),
        "failed_tool_calls":     len(fail),
        "tool_success_rate":     len(success)/len(tool_logs)*100 if tool_logs else 0,
        "tool_call_counts":      counts,
        "avg_tool_duration_ms":  round(avg_dur, 2),
        "total_agent_sessions":  len(agent_traces),
        "total_eval_runs":       len(eval_logs),
        "avg_eval_score":        round(avg_score, 3),
        "module_avg_scores":     mod_avg,
    }
