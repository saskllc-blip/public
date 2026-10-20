"""
Tests for evaluation/evaluator.py and its interaction with utils/logger.py.

Runs with NO API key and NO network access, structurally (see conftest.py) --
that is not a limitation of this suite, it is the point: a stranger can
clone this repo and run `pytest` with zero setup and no risk of being billed.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

import config
from evaluation import evaluator as ev
from utils.logger import get_eval_logs


# ── 1. No key -> degraded, stated reason, never mislabelled ────────────────────
def test_no_key_llm_judge_degrades_with_stated_reason():
    assert config.OPENAI_API_KEY == ""  # conftest guarantees this; assert it anyway
    score, grade, prov = ev._llm_score("Q?", "reference answer", "generated answer")
    assert prov["scorer"] == "heuristic_token_f1"
    assert prov["fallback_from"] == "llm_judge"
    assert prov["fallback_reason"] == "no OPENAI_API_KEY configured"
    assert prov["model"] is None
    assert prov["rubric_version"] is None


def test_no_key_run_evaluation_reports_degraded_at_run_level():
    r = ev.run_evaluation(module="appointment", agent=None, use_llm_judge=True)
    assert r["requested_scorer"] == "llm_judge"
    assert r["scorers_used"] == ["heuristic_token_f1"]  # never silently "llm_judge"
    assert r["degraded_count"] == r["total_questions"]
    assert r["degraded_reason"] == "no OPENAI_API_KEY configured"
    for result in r["results"]:
        assert result["scorer"] == "heuristic_token_f1"
        assert result["fallback_reason"] == "no OPENAI_API_KEY configured"


# ── 2. A real judge result carries scorer/model/rubric_version (mocked) ────────
def test_llm_judge_success_mocked_carries_full_provenance(monkeypatch):
    """Exercises the SUCCESS path of _llm_score without any network call --
    the OpenAI client class itself is replaced with a stub. This is the only
    place in the suite that "has" a key, and it is fake, and nothing it
    touches can reach the network because ChatOpenAI itself never runs."""
    monkeypatch.setattr(config, "OPENAI_API_KEY", "fake-test-key-not-real")

    fake_response = MagicMock()
    fake_response.content = '{"score": 0.9, "grade": "A", "reason": "matches the reference closely"}'
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response

    with patch("langchain_openai.ChatOpenAI", return_value=fake_llm) as fake_cls:
        score, grade, prov = ev._llm_score("Q?", "reference answer", "generated answer")

    fake_cls.assert_called_once()
    fake_llm.invoke.assert_called_once()
    assert score == 0.9
    assert grade == "A"
    assert prov["scorer"] == "llm_judge"
    assert prov["model"] == config.LLM_MODEL
    assert prov["rubric_version"] == ev.DEFAULT_RUBRIC["version"]
    assert prov["reason"] == "matches the reference closely"
    assert "fallback_reason" not in prov


def test_llm_judge_uses_the_rubric_it_is_given(monkeypatch):
    """A custom rubric actually drives what gets sent to the judge, and its
    version is what gets attributed back -- not silently DEFAULT_RUBRIC."""
    monkeypatch.setattr(config, "OPENAI_API_KEY", "fake-test-key-not-real")
    custom_rubric = {
        "version": "legal-qa-v1",
        "judge_system_prompt": "You are a legal-accuracy evaluator.",
        "criteria": [{"name": "legal_accuracy", "weight": 1.0}],
    }
    fake_response = MagicMock()
    fake_response.content = '{"score": 0.7, "grade": "B", "reason": "mostly correct"}'
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_response

    with patch("langchain_openai.ChatOpenAI", return_value=fake_llm):
        score, grade, prov = ev._llm_score("Q?", "ref", "gen", custom_rubric)

    assert prov["rubric_version"] == "legal-qa-v1"
    sent_system_message = fake_llm.invoke.call_args[0][0][0]
    assert sent_system_message.content == "You are a legal-accuracy evaluator."


# ── 3. An unversioned rubric is rejected ────────────────────────────────────────
def test_load_rubric_rejects_missing_version(tmp_path):
    bad_rubric_path = tmp_path / "bad_rubric.json"
    bad_rubric_path.write_text(json.dumps({
        "judge_system_prompt": "x",
        "criteria": [{"name": "accuracy", "weight": 1.0}],
    }))
    with pytest.raises(ValueError, match="version"):
        ev.load_rubric(str(bad_rubric_path))


def test_load_rubric_defaults_to_default_rubric_when_no_path():
    assert ev.load_rubric(None) is ev.DEFAULT_RUBRIC
    assert ev.load_rubric() is ev.DEFAULT_RUBRIC


# ── 4. A malformed case file fails with a useful message ───────────────────────
def test_load_cases_json_missing_question_field_names_file_and_case(tmp_path):
    bad_cases_path = tmp_path / "bad_cases.json"
    bad_cases_path.write_text(json.dumps({
        "billing": [{"reference": "no question key here"}],
    }))
    with pytest.raises(ValueError) as exc_info:
        ev.load_cases(str(bad_cases_path))
    message = str(exc_info.value)
    assert str(bad_cases_path) in message
    assert "billing" in message
    assert "question" in message


def test_load_cases_csv_missing_question_names_row_number(tmp_path):
    bad_csv_path = tmp_path / "bad_cases.csv"
    bad_csv_path.write_text("module,reference\nbilling,no question column\n")
    with pytest.raises(ValueError) as exc_info:
        ev.load_cases(str(bad_csv_path))
    message = str(exc_info.value)
    assert str(bad_csv_path) in message
    assert "question" in message


def test_load_cases_unsupported_extension_names_the_extension(tmp_path):
    bad_path = tmp_path / "cases.txt"
    bad_path.write_text("not a real case file")
    with pytest.raises(ValueError, match=r"\.txt"):
        ev.load_cases(str(bad_path))


def test_load_cases_json_generalizes_off_the_medical_domain(tmp_path):
    """Regression test for the generalization itself: a domain that has
    never appeared in SAMPLE_QA_PAIRS runs end to end using only its own
    case file, no medical-specific code path touched."""
    cases_path = tmp_path / "legal_cases.json"
    cases_path.write_text(json.dumps({
        "contracts": [
            {"question": "What is consideration?",
             "reference": "Something of value exchanged between parties.",
             "generated": "Consideration is value exchanged that makes a contract enforceable."},
        ],
    }))
    cases = ev.load_cases(str(cases_path))
    result = ev.run_evaluation(module="all", agent=None, use_llm_judge=False, cases=cases)
    assert result["total_questions"] == 1
    assert result["results"][0]["module"] == "contracts"
    assert result["results"][0]["generated"] == (
        "Consideration is value exchanged that makes a contract enforceable.")


# ── 5. Persisted log round-trips provenance (regression test) ──────────────────
def test_persisted_log_round_trips_full_provenance():
    """This is the regression test for the bug found while verifying step 1:
    log_eval_result() originally accepted no provenance at all, and then --
    after that was fixed -- persisted it under a field name ("model") that
    did not match run_evaluation()'s in-memory schema ("judge_model"). Both
    failure modes would make this test fail."""
    logs_before = len(get_eval_logs(10_000))
    result = ev.run_evaluation(module="appointment", agent=None, use_llm_judge=False)
    logs_after = get_eval_logs(10_000)
    assert len(logs_after) == logs_before + result["total_questions"]

    new_entries = logs_after[-result["total_questions"]:]
    for entry, in_memory_result in zip(new_entries, result["results"]):
        assert entry["schema_version"] >= 3
        assert entry["scorer"] == in_memory_result["scorer"]
        assert entry["judge_model"] == in_memory_result["judge_model"]
        assert entry["rubric_version"] == in_memory_result["rubric_version"]
        assert entry["question"] == in_memory_result["question"]
        assert entry["score"] == in_memory_result["score"]


def test_persisted_log_degraded_entry_is_unmistakable():
    result = ev.run_evaluation(module="appointment", agent=None, use_llm_judge=True)
    new_entries = get_eval_logs(10_000)[-result["total_questions"]:]
    for entry in new_entries:
        assert entry["scorer"] == "heuristic_token_f1"
        assert entry["fallback_reason"] == "no OPENAI_API_KEY configured"
        assert entry["judge_model"] is None


# ── Backward compatibility (locks in behaviour that already existed) ───────────
def test_default_sample_set_still_works_with_no_new_args():
    r = ev.run_evaluation(module="all", agent=None, use_llm_judge=False)
    assert r["total_questions"] == 7  # 2 + 2 + 2 + 1 across the 4 bundled modules
    assert r["scorers_used"] == ["heuristic_token_f1"]
    assert r["rubric_version"] is None  # not a judge run, no rubric applied


def test_heuristic_score_grade_matches_grade_function():
    """_heuristic_score used to inline its own copy of _grade()'s A-F
    thresholds. It now calls _grade() directly -- confirm the grade band it
    returns for a given score is exactly what _grade() independently
    computes for that same score, so the two can never drift apart again."""
    cases = [
        ("appointment slot doctor available", "appointment slot doctor available"),  # high overlap
        ("appointment slot doctor available", "completely unrelated words here"),     # low overlap
        ("a b c d e", "a b"),                                                          # partial overlap
    ]
    for reference, generated in cases:
        score, grade, _ = ev._heuristic_score(reference, generated)
        assert grade == ev._grade(score), (
            f"_heuristic_score returned grade {grade!r} for score {score}, "
            f"but _grade({score}) independently computes {ev._grade(score)!r}")
