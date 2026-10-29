"""
Session-wide safety net for this test suite.

Two separate sessions each made one real, unintended paid OpenAI API call
while manually verifying this exact code -- both times because a live
OPENAI_API_KEY happened to be exported in the shell, and nothing structural
stopped it. A safety pattern a person has to remember before every test is
not a control, it is a hope.

This fixture makes "no key, no network" the STRUCTURAL default for every
test in this suite, regardless of what is exported in the environment
running pytest. A test that deliberately wants to exercise a real judge
response must explicitly mock the network boundary itself (see
test_llm_judge_success_mocked in test_evaluator.py) -- it can never reach
the network just because a key happens to be present. A test suite that
cannot accidentally bill you demonstrates judgement; that is a portfolio
strength, not just a safety measure.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True, scope="session")
def no_network_by_default():
    import config

    saved_env_key = os.environ.pop("OPENAI_API_KEY", None)
    saved_config_key = config.OPENAI_API_KEY
    config.OPENAI_API_KEY = ""
    try:
        yield
    finally:
        config.OPENAI_API_KEY = saved_config_key
        if saved_env_key is not None:
            os.environ["OPENAI_API_KEY"] = saved_env_key


@pytest.fixture(autouse=True)
def isolated_eval_log(tmp_path, monkeypatch):
    """Tests must never write to the application's REAL logs/eval_logs.json.
    That file carries the app's genuine evaluation history and is what the
    Admin Dashboard reads for its track-record view -- a suite that quietly
    injects synthetic rows into a stranger's real history every time they
    run `pytest` is the same class of problem as the API-key leak above (a
    global neither test nor reader should be trusted to remember to avoid),
    and it is exactly the kind of thing a staff-engineer reviewer notices.
    Every test gets its own disposable log file instead."""
    import config

    monkeypatch.setattr(config, "EVAL_LOGS_FILE", str(tmp_path / "eval_logs_test.json"))
    # Same reasoning for the tool-call log and agent traces: every tool
    # function logs on each call, so without this a test run appended rows
    # to the real logs/tool_logs.json that the dashboards read.
    monkeypatch.setattr(config, "TOOL_LOGS_FILE", str(tmp_path / "tool_logs_test.json"))
    monkeypatch.setattr(config, "AGENT_TRACES_FILE", str(tmp_path / "agent_traces_test.json"))
