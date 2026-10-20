"""
Evaluator — LLMOps model evaluation module.

Uses QA-style evaluation:
  1. Token-overlap F1 heuristic (always available, no API key needed)
  2. LLM-as-judge via OpenAI (optional, better accuracy), scored against a
     versioned, swappable rubric (see DEFAULT_RUBRIC / load_rubric()).

Cases are domain-agnostic: SAMPLE_QA_PAIRS below is a bundled medical sample,
not a hardcoded ceiling. Any domain's cases can be supplied at runtime via
load_cases() and passed to run_evaluation(cases=...).

Results are logged to eval_logs.json for dashboard visualisation.
"""
import csv
import json
import os, sys, re
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import log_eval_result, get_eval_logs


# ── Case sets ─────────────────────────────────────────────────────────────────
# Bundled medical QA pairs -- a SAMPLE dataset, not the only domain this
# evaluator understands. load_cases() below loads any domain's cases from an
# external JSON/CSV file in the same {question, reference, generated?} shape.
SAMPLE_QA_PAIRS = {
    "appointment": [
        {"question": "How do I book an appointment with a nephrologist?",
         "reference": ("To book a nephrologist appointment, search for available "
                       "nephrology doctors and select a convenient slot.")},
        {"question": "What slots are available for a cardiologist?",
         "reference": ("I will check the cardiology schedule and present available "
                       "time slots from matching doctors.")},
    ],
    "ehr": [
        {"question": "What is Rajesh Kumar's current medication?",
         "reference": ("Rajesh Kumar is on Metformin 500mg twice daily, "
                       "Amlodipine 5mg once daily, and Lisinopril 10mg once daily.")},
        {"question": "What are Sunita Sharma's known allergies?",
         "reference": ("Sunita Sharma is allergic to Aspirin.")},
    ],
    "search": [
        {"question": "What are the latest treatment methods for chronic kidney disease?",
         "reference": ("CKD treatment includes blood pressure control, diabetes management, "
                       "low-protein diet, ACE inhibitors, and dialysis or transplant for "
                       "advanced stages.")},
        {"question": "What are the symptoms of rheumatoid arthritis?",
         "reference": ("Rheumatoid arthritis causes morning stiffness, joint pain and "
                       "swelling in hands and wrists, fatigue, and fever.")},
    ],
    "rag": [
        {"question": "Summarize Rajesh Kumar's medical history",
         "reference": ("Rajesh Kumar (70M) has Chronic Kidney Disease Stage 3, Type 2 "
                       "Diabetes, and Hypertension. Takes Metformin, Amlodipine, Lisinopril. "
                       "Allergic to Penicillin and Sulfa drugs.")},
    ],
}
EVAL_QA_PAIRS = SAMPLE_QA_PAIRS  # backward-compat alias; existing callers unaffected


def load_cases(path: str) -> Dict[str, List[Dict[str, str]]]:
    """Load evaluation cases for ANY domain from an external file. This is
    the entire generalization step -- nothing else in this module needs to
    change to evaluate a new domain once a case file (and optionally a
    rubric, see load_rubric()) exist for it.

    JSON: either {module: [{question, reference, generated?}, ...]} (same
    shape as SAMPLE_QA_PAIRS) or a flat list of
    {module, question, reference, generated?} records.
    CSV: columns module,question,reference,generated (reference/generated
    may be blank or omitted; a case with no "generated" falls back to the
    mock/agent path in run_evaluation(), same as the bundled sample).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            for mod_name, pairs in data.items():
                for i, row in enumerate(pairs):
                    if "question" not in row:
                        raise ValueError(
                            f"{path}: module {mod_name!r}, case {i} is missing "
                            f"a required \"question\" field: {row!r}")
            return data
        if isinstance(data, list):
            out: Dict[str, List[Dict[str, str]]] = {}
            for i, row in enumerate(data):
                if "question" not in row:
                    raise ValueError(f"{path}: row {i} is missing a required \"question\" field: {row!r}")
                case = {"question": row["question"], "reference": row.get("reference", "")}
                if row.get("generated"):
                    case["generated"] = row["generated"]
                out.setdefault(row.get("module", "default"), []).append(case)
            return out
        raise ValueError(f"{path}: unrecognized JSON case-file shape (expected an object or a list)")
    elif ext == ".csv":
        out: Dict[str, List[Dict[str, str]]] = {}
        with open(path, newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if not row.get("question"):
                    raise ValueError(f"{path}: row {i + 2} (1-indexed, header is row 1) "
                                      f"is missing a required \"question\" value: {row!r}")
                case = {"question": row["question"], "reference": row.get("reference", "") or ""}
                if row.get("generated"):
                    case["generated"] = row["generated"]
                out.setdefault(row.get("module") or "default", []).append(case)
        return out
    raise ValueError(f"{path}: unsupported case file extension {ext!r} (use .json or .csv)")


# ── Rubric ────────────────────────────────────────────────────────────────────
# Restores Kiran's own later iteration of this judge prompt from the one
# surviving artifact of the original app (mlops_runtime.json): explicit
# per-criterion weights and a "reason" field, both absent from the prompt
# this file had before. VERSIONED deliberately: provenance already records
# which scorer and model produced a score (patch 1), but a score is not
# comparable across runs unless the rubric that produced it is recorded too
# -- two "llm_judge" scores against different criteria are not the same
# yardstick. The system prompt itself is kept domain-neutral (unlike the
# original "You are a medical QA evaluator.") since the rubric, not the
# module, should carry domain specifics going forward.
DEFAULT_RUBRIC: Dict[str, Any] = {
    "version": "qa-judge-v1",
    "judge_system_prompt": "You are an objective evaluator. Score strictly against the rubric provided.",
    "criteria": [
        {"name": "factual_accuracy", "weight": 0.4},
        {"name": "relevance", "weight": 0.3},
        {"name": "completeness", "weight": 0.3},
    ],
}


def load_rubric(path: str | None = None) -> Dict[str, Any]:
    """Load a rubric config: {version, judge_system_prompt, criteria}.
    Defaults to DEFAULT_RUBRIC. This is "a rubric defined in a config file,
    not hardcoded" -- swap the file to change what the judge scores against
    without touching this module."""
    if not path:
        return DEFAULT_RUBRIC
    with open(path) as f:
        rubric = json.load(f)
    if "version" not in rubric:
        raise ValueError(f"rubric file {path} has no 'version' field -- rubrics must be versioned")
    return rubric


def _judge_prompt(question: str, reference: str, generated: str, rubric: Dict[str, Any]) -> str:
    criteria_lines = "\n".join(
        f"- {c['name'].replace('_', ' ').title()} ({c['weight']} weight)"
        for c in rubric["criteria"]
    )
    return (f"Question: {question}\nReference: {reference}\n"
            f"Generated: {generated}\n\n"
            f"Score the generated answer (0-1) using this rubric:\n{criteria_lines}\n\n"
            'Respond ONLY with JSON: {"score": 0.85, "grade": "A", "reason": "..."}')


# ── Scoring ───────────────────────────────────────────────────────────────────
def _heuristic_score(reference: str, generated: str) -> Tuple[float, str, Dict[str, Any]]:
    """Token-overlap F1 with key-term bonus. Returns (score, grade,
    provenance) -- provenance always present, scorer/model/rubric_version
    included even here so every caller can treat all scoring paths
    uniformly (see _llm_score for why that matters)."""
    ref_tok = set(reference.lower().split())
    gen_tok = set(generated.lower().split())
    if not gen_tok:
        return 0.0, "F", {"scorer": "heuristic_token_f1", "model": None, "reason": "empty generation", "rubric_version": None}
    overlap   = ref_tok & gen_tok
    precision = len(overlap) / len(gen_tok)
    recall    = len(overlap) / len(ref_tok) if ref_tok else 0
    f1        = 2*precision*recall/(precision+recall) if (precision+recall) else 0.0
    key_terms = {w for w in ref_tok if len(w) > 4}
    bonus     = min(0.2, len(key_terms & gen_tok) / max(len(key_terms),1) * 0.2)
    score     = min(1.0, f1 + bonus)
    # Single source of truth for grade bands -- this used to duplicate
    # _grade()'s thresholds inline, so a threshold change had two places to
    # remember to update. _grade() is defined later in this module but that
    # is fine: Python resolves the name at call time, after the whole module
    # has loaded, not at definition time.
    grade = _grade(score)
    return round(score, 3), grade, {"scorer": "heuristic_token_f1", "model": None, "reason": None, "rubric_version": None}


def _llm_score(question, reference, generated, rubric: Dict[str, Any] | None = None) -> Tuple[float, str, Dict[str, Any]]:
    """LLM-as-judge score, scored against `rubric` (DEFAULT_RUBRIC if none
    given).

    Returns (score, grade, provenance). Provenance ALWAYS states which scorer
    actually produced the number AND which rubric version, so a heuristic
    fallback can never be mistaken for a judge score, and two judge scores
    can never be silently compared across different rubrics. That distinction
    is the whole point of an eval tool: a number you cannot attribute is
    worse than no number at all.
    """
    rubric = rubric or DEFAULT_RUBRIC
    if not config.OPENAI_API_KEY or config.OPENAI_API_KEY == "your_openai_api_key_here":
        score, grade, prov = _heuristic_score(reference, generated)
        prov["fallback_from"] = "llm_judge"
        prov["fallback_reason"] = "no OPENAI_API_KEY configured"
        return score, grade, prov
    try:
        from langchain_openai import ChatOpenAI
        # langchain>=1.0 removed langchain.schema; messages live in langchain_core.
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = ChatOpenAI(model=config.LLM_MODEL, temperature=0,
                         api_key=config.OPENAI_API_KEY)
        prompt = _judge_prompt(question, reference, generated, rubric)
        resp = llm.invoke([SystemMessage(content=rubric["judge_system_prompt"]),
                           HumanMessage(content=prompt)])
        m = re.search(r"\{.*\}", resp.content, re.DOTALL)
        if not m:
            raise ValueError("judge returned no JSON object")
        d = json.loads(m.group())
        return (float(d.get("score", 0)), d.get("grade", "C"),
                {"scorer": "llm_judge", "model": config.LLM_MODEL,
                 "reason": d.get("reason"), "rubric_version": rubric["version"]})
    except Exception as e:
        # Fall back, but NEVER silently: the caller and the UI must be able to
        # see that this number is token overlap, not a judge verdict.
        score, grade, prov = _heuristic_score(reference, generated)
        prov["fallback_from"] = "llm_judge"
        prov["fallback_reason"] = f"{type(e).__name__}: {e}"
        return score, grade, prov


def _mock_answer(question: str, module: str) -> str:
    answers = {
        "appointment": {
            "How do I book an appointment with a nephrologist?":
                "You can book a nephrologist appointment by searching for available slots. I will find the right doctor and available times.",
            "What slots are available for a cardiologist?":
                "Let me check the cardiology schedule. Available slots are listed at 10:00 AM and 2:00 PM.",
        },
        "ehr": {
            "What is Rajesh Kumar's current medication?":
                "Rajesh Kumar takes Metformin for diabetes and blood pressure medication Amlodipine.",
            "What are Sunita Sharma's known allergies?":
                "Sunita Sharma has an allergy to Aspirin according to her records.",
        },
        "search": {
            "What are the latest treatment methods for chronic kidney disease?":
                "CKD treatment involves managing blood pressure, diabetes control, low-protein diet, and dialysis for advanced stages.",
            "What are the symptoms of rheumatoid arthritis?":
                "Rheumatoid arthritis causes joint pain, swelling, morning stiffness, and fatigue in the hands and wrists.",
        },
        "rag": {
            "Summarize Rajesh Kumar's medical history":
                "Rajesh Kumar is a 70-year-old male with CKD, diabetes, and hypertension. He takes multiple medications and is allergic to Penicillin.",
        },
    }
    return answers.get(module, {}).get(question,
           "I don't have enough information to answer that accurately.")


# ── Public API ────────────────────────────────────────────────────────────────
def run_evaluation(module="all", agent=None, use_llm_judge=False,
                    cases: Dict[str, List[Dict[str, str]]] | None = None,
                    rubric: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """cases defaults to the bundled medical SAMPLE_QA_PAIRS -- pass the
    result of load_cases() to evaluate any other domain. rubric defaults to
    DEFAULT_RUBRIC -- pass the result of load_rubric() to score against a
    different, versioned rubric. Existing positional callers (module, agent,
    use_llm_judge) are unaffected."""
    case_set = cases if cases is not None else SAMPLE_QA_PAIRS
    rubric = rubric or DEFAULT_RUBRIC
    modules = list(case_set.keys()) if module == "all" else [module]
    results = []

    for mod in modules:
        if mod not in case_set:
            continue
        for pair in case_set[mod]:
            q, ref = pair["question"], pair.get("reference", "")
            if pair.get("generated"):
                # A case that already carries its own generated answer is
                # evaluated as-is -- no agent or mock stand-in needed. This
                # is what makes a NEW domain's cases usable without also
                # wiring up an agent for it.
                gen = pair["generated"]
            elif agent:
                try:
                    gen = agent.run(q).get("response","")
                except Exception as e:
                    gen = f"Error: {e}"
            else:
                gen = _mock_answer(q, mod)

            score, grade, prov = (_llm_score(q, ref, gen, rubric) if use_llm_judge
                                  else _heuristic_score(ref, gen))
            log_eval_result(q, ref, gen, score, grade, mod,
                             scorer=prov.get("scorer"), judge_model=prov.get("model"),
                             rubric_version=prov.get("rubric_version"),
                             reason=prov.get("reason"),
                             fallback_reason=prov.get("fallback_reason"))
            results.append({"module": mod, "question": q, "reference": ref,
                             "generated": gen, "score": score, "grade": grade,
                             "scorer": prov.get("scorer"),
                             "judge_model": prov.get("model"),
                             "judge_reason": prov.get("reason"),
                             "rubric_version": prov.get("rubric_version"),
                             "fallback_reason": prov.get("fallback_reason")})

    scores = [r["score"] for r in results]
    avg    = sum(scores)/len(scores) if scores else 0

    mod_scores: Dict[str, list] = {}
    for r in results:
        mod_scores.setdefault(r["module"], []).append(r["score"])
    mod_avg = {m: round(sum(v)/len(v),3) for m, v in mod_scores.items()}

    scorers_used = sorted({r.get("scorer") for r in results if r.get("scorer")})
    degraded = [r for r in results if r.get("fallback_reason")]

    return {"success": True, "total_questions": len(results),
            "average_score": round(avg,3),
            "module_averages": mod_avg, "results": results,
            "grade": _grade(avg),
            # Provenance at the run level: if a caller asked for the LLM judge
            # and got token overlap instead, that must be impossible to miss.
            # rubric_version records what WOULD apply to any llm_judge score
            # in this run -- cross-run comparison must check this, not just
            # scorers_used, since two "llm_judge" runs against different
            # rubric versions are not the same yardstick.
            "scorers_used": scorers_used,
            "requested_scorer": "llm_judge" if use_llm_judge else "heuristic_token_f1",
            "rubric_version": rubric["version"] if use_llm_judge else None,
            "degraded_count": len(degraded),
            "degraded_reason": degraded[0]["fallback_reason"] if degraded else None}


def _grade(s: float) -> str:
    return "A" if s>=.75 else "B" if s>=.60 else "C" if s>=.45 else "D" if s>=.30 else "F"


def get_evaluation_summary() -> Dict[str, Any]:
    logs = get_eval_logs(500)
    if not logs:
        return {"total_evals":0,"average_score":0,"grade":"N/A",
                "module_averages":{},"recent_results":[]}
    scores = [e["score"] for e in logs if "score" in e]
    avg    = sum(scores)/len(scores) if scores else 0
    mod: Dict[str,list] = {}
    for e in logs:
        mod.setdefault(e.get("module","?"),[]).append(e.get("score",0))
    return {"total_evals": len(logs), "average_score": round(avg,3),
            "grade": _grade(avg),
            "module_averages": {m: round(sum(v)/len(v),3) for m,v in mod.items()},
            "recent_results": logs[-10:]}
